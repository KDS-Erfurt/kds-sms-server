import logging
from contextlib import asynccontextmanager
from ipaddress import IPv4Address
from pathlib import Path
from typing import TYPE_CHECKING, Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route
from starlette_admin import fields as sa_fields
from starlette_admin.auth import AdminConfig, AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed, FormValidationError
from starlette_admin.actions import row_action, action
from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.exceptions import ActionFailed

from kds_sms_server.statics import ASSETS_PATH
from kds_sms_server.db import Sms, SmsStatus, db
from kds_sms_server.server.server import BaseServer
from kds_sms_server.settings import settings

if TYPE_CHECKING:
    from kds_sms_server.server.ui.config import UiServerConfig

logger = logging.getLogger(__name__)


class UiAuthProvider(AuthProvider):
    ui: "Ui"

    async def login(self,
                    username: str,
                    password: str,
                    remember_me: bool,
                    request: Request,
                    response: Response) -> Response:
        if username not in self.ui.ui_server.config.authentication_accounts:
            if self.ui.ui_server.config.debug:
                raise FormValidationError({"username": "Username not found!"})
            raise LoginFailed("Invalid username or password!")
        if self.ui.ui_server.config.authentication_accounts[username] != password:
            if self.ui.ui_server.config.debug:
                raise FormValidationError({"password": "Password incorrect!"})
            raise LoginFailed("Invalid username or password!")

        # save username in session
        request.session.update({"username": username})
        return response

    async def is_authenticated(self, request) -> bool:
        if request.session.get("username", None) in self.ui.ui_server.config.authentication_accounts:
            return True
        return False

    def get_admin_config(self, request: Request) -> AdminConfig:
        return AdminConfig(
            app_title=f"Hello, {request.session['username'].capitalize()}!",
            logo_url=None,
        )

    def get_admin_user(self, request: Request) -> AdminUser:
        return AdminUser(username=request.session["username"], photo_url=None)

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response


class UiSmsView(ModelView):
    page_size = 100
    page_size_options = [5, 10, 25, 50, 75, 100, -1]
    fields = [sa_fields.IntegerField("id"),
              sa_fields.EnumField("status", choices=[status.value for status in SmsStatus]),
              sa_fields.StringField("received_by"),
              sa_fields.DateTimeField("received_datetime"),
              sa_fields.DateTimeField("processed_datetime"),
              sa_fields.StringField("sent_by"),
              sa_fields.PhoneField("number"),
              sa_fields.TextAreaField("message"),
              sa_fields.TextAreaField("result"),
              sa_fields.TextAreaField("log")]
    exclude_fields_from_list = [Sms.message,
                                Sms.result,
                                Sms.log]
    exclude_fields_from_create = [Sms.status,
                                  Sms.received_by,
                                  Sms.received_datetime,
                                  Sms.processed_datetime,
                                  Sms.sent_by,
                                  Sms.result,
                                  Sms.log]

    row_actions = ["view", "row_reset", "row_abort"]
    actions = ["reset", "abort"]

    def __init__(self, ui: "Ui"):
        if not settings.listener.sms_logging:
            # noinspection PyUnresolvedReferences
            self.exclude_fields_from_detail.append(Sms.message)
        super().__init__(Sms, label="SMS", icon="fa fa-message")
        self.ui = ui

    def can_edit(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False

    async def create(self, request: Request, data: dict[str, Any]) -> Any:
        try:
            data = await self._arrange_data(request, data)
            await self.validate(request, data)

            # get number and message
            number = data["number"]
            message = data["message"]

            client_ip = IPv4Address(request.client.host)
            client_port = request.client.port

            result = self.ui.ui_server.handle_request(caller=None, number=number, message=message, client_ip=client_ip, client_port=client_port)
            if isinstance(result, Exception):
                raise result
            sms = Sms.get(id=result)
            if sms is None:
                raise FileNotFoundError(f"SMS with id={result} not found!")
            return sms
        except Exception as e:
            return self.handle_exception(e)

    @row_action(
        name="row_reset",
        text="Reset SMS",
        confirmation="Do you want to reset this SMS?",
        icon_class="fa-regular fa-repeat",
        submit_btn_text="Yes",
        submit_btn_class="btn-success",
    )
    async def row_reset_action(self, request: Request, pk: str) -> str:
        sms = Sms.get(Sms.id == pk)
        if sms is None:
            raise ActionFailed(f"SMS with id={pk} not found.")
        sms.update(status=SmsStatus.QUEUED,
                   processed_datetime=None,
                   sent_by=None,
                   result=None,
                   log=None)
        return f"SMS with id={pk} reset successfully."

    @action(
        name="reset",
        text="Reset SMS",
        confirmation="Do you want to reset this SMS?",
        icon_class="fa-regular fa-repeat",
        submit_btn_text="Yes",
        submit_btn_class="btn-success",
    )
    async def reset_action(self, request: Request, pks: list[str]) -> str:
        successes = []
        for pk in pks:
            successes.append(await self.row_reset_action(request=request, pk=pk))
        return "\n".join(successes)

    @row_action(
        name="row_abort",
        text="Abort SMS",
        confirmation="Do you want to cancel this SMS?",
        icon_class="fa-regular fa-ban",
        submit_btn_text="Yes",
        submit_btn_class="btn-success",
    )
    async def row_abort_action(self, request: Request, pk: str) -> str:
        sms = Sms.get(Sms.id == pk)
        if sms is None:
            raise ActionFailed(f"SMS with id={pk} not found.")
        if sms.status != SmsStatus.QUEUED:
            raise ActionFailed(f"Cannot abort SMS with id={pk}! SMS is not in queued state.")
        sms.update(status=SmsStatus.ABORTED,
                   processed_datetime=None,
                   sent_by=None,
                   result=None,
                   log=None)
        return f"SMS with id={pk} aborted successfully."

    @action(
        name="abort",
        text="Abort SMS",
        confirmation="Do you want to cancel this SMS?",
        icon_class="fa-regular fa-ban",
        submit_btn_text="Yes",
        submit_btn_class="btn-success",
    )
    async def abort_action(self, request: Request, pks: list[str]) -> str:
        successes = []
        for pk in pks:
            successes.append(await self.row_abort_action(request=request, pk=pk))
        return "\n".join(successes)


class Ui(Admin):
    def __init__(self, ui_server: "UiServer"):
        templates_dir = Path(__file__).parent / "templates"
        if not templates_dir.is_dir():
            raise FileNotFoundError(f"Template directory '{templates_dir}' not found.")
        auth_provider = UiAuthProvider(allow_paths=["/statics/logo.png"])
        auth_provider.ui = self
        super().__init__(engine=db().engine,
                         title=ui_server.title,
                         base_url="/",
                         templates_dir=str(templates_dir),
                         statics_dir=ASSETS_PATH,
                         logo_url="/statics/logo.png",
                         login_logo_url="/statics/logo.png",
                         favicon_url="/statics/favicon.ico",
                         auth_provider=auth_provider,
                         middlewares=[Middleware(SessionMiddleware,
                                                 secret_key=ui_server.config.session_secret_key,
                                                 session_cookie=ui_server.config.session_cookie,
                                                 max_age=ui_server.config.session_max_age)],
                         debug=ui_server.config.debug)
        self.ui_server = ui_server

        # add views
        self.sms_view = UiSmsView(self)
        self.add_view(self.sms_view)

        # replace the root route
        root_route_index = None
        for i, route in enumerate(self.routes):
            if not isinstance(route, Route):
                continue
            if route.path != "/":
                continue
            root_route_index = i
            break
        if root_route_index is None:
            raise RuntimeError("Root route not found.")
        self.routes[root_route_index] = Route(
            path="/",
            endpoint=self.root,
            methods=None,
            name="index",
        )

        # mount to ui_server
        self.mount_to(self.ui_server)

    async def root(self, request: Request):
        return RedirectResponse(url=f"/{self.sms_view.identity}/list")


class UiServer(BaseServer, FastAPI):
    __str_columns__ = ["name",
                       ("debug", "config_debug"),
                       ("host", "config_host"),
                       ("port", "config_port"),
                       ("allowed_networks", "config_allowed_networks"),
                       ("authentication_enabled", "config_authentication_enabled")]

    def __init__(self, name: str, config: "UiServerConfig"):
        BaseServer.__init__(self,
                            name=name,
                            config=config)
        FastAPI.__init__(self,
                         openapi_url=None,
                         docs_url=None,
                         redoc_url=None,
                         lifespan=self._stated_done,
                         debug=self.config.debug)
        self.title = f"{settings.branding_title} - {self.name}"
        self.description = settings.branding_description
        self.version = f"v{settings.branding_version}"
        self.terms_of_service = settings.branding_terms_of_service
        self.contact = {"name": settings.branding_author, "email": settings.branding_author_email}
        self.license_info = {"name": settings.branding_license, "url": settings.branding_license_url}

        # create ui
        logger.info(f"Create ui for {self} ...")
        self._ui = Ui(self)
        logger.debug(f"Create ui for {self} ... done")

        self.init_done()

    @property
    def config(self) -> "UiServerConfig":
        return super().config

    @property
    def config_host(self) -> str:
        return str(self.config.host)

    @property
    def config_port(self) -> int:
        return self.config.port

    @property
    def config_allowed_networks(self) -> list[str]:
        return [str(allowed_network) for allowed_network in self.config.allowed_networks]

    @property
    def config_authentication_enabled(self) -> bool:
        return self.config.authentication_enabled

    @staticmethod
    @asynccontextmanager
    async def _stated_done(ui_server: "UiServer"):
        ui_server.stated_done()
        yield

    def enter(self):
        uvicorn.run(self, host=str(self.config.host), port=self.config.port)

    def exit(self):
        ...

    # noinspection DuplicatedCode
    def handle_request(self, caller: None, **kwargs) -> Any | None:
        # check if client ip is allowed
        allowed = False
        for network in self.config.allowed_networks:
            if kwargs["client_ip"] in network:
                allowed = True
                break
        if not allowed:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=False, sms_id=None, result=f"Client IP address '{kwargs['client_ip']}' is not allowed.")

        logger.debug(f"{self} - Accept message:\nclient='{kwargs['client_ip']}'\nport={kwargs['client_ip']}")

        return super().handle_request(caller=caller, **kwargs)

    def handle_sms_data(self, caller: None, **kwargs) -> tuple[str, str]:
        return kwargs["number"], kwargs["message"]

    def success_handler(self, caller: None, sms_id: int, result: str, **kwargs) -> Any:
        return sms_id

    def error_handler(self, caller: None, sms_id: int | None, result: str, **kwargs) -> Any:
        return RuntimeError(result)
