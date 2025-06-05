import logging
from contextlib import asynccontextmanager
from ipaddress import IPv4Address
from pathlib import Path
from typing import TYPE_CHECKING, Any

import uvicorn
from starlette.applications import Starlette
from starlette_admin.views import CustomView
from starlette_admin.actions import row_action, action
from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.exceptions import StarletteAdminException, ActionFailed

from kds_sms_server import __title__, __description__, __version__, __author__, __author_email__, __license__
from kds_sms_server.assets import ASSETS_PATH
from kds_sms_server.db import Sms, SmsStatus, db
from kds_sms_server.server.server import BaseServer
from starlette.requests import Request

if TYPE_CHECKING:
    from kds_sms_server.server.ui.config import UiServerConfig

logger = logging.getLogger(__name__)


class HomeView(CustomView):
    def __init__(self, ui: "Ui"):
        super().__init__(label="Home", icon="fa fa-house")
        self.ui = ui


class SmsView(ModelView):
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
        super().__init__(engine=db().engine,
                         title="Test",
                         base_url="/",
                         templates_dir=str(templates_dir),
                         debug=ui_server.config.debug)
        self.ui_server = ui_server

        # add views
        self.add_view(HomeView(self))
        self.add_view(SmsView(self))

        self.mount_to(self.ui_server)


class UiServer(BaseServer, Starlette):
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
        Starlette.__init__(self,
                           lifespan=self._stated_done,
                           debug=self.config.debug)

        # create ui and mount admin to server
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

    # async def get_api_credentials_from_token(self, token: str) -> tuple[str, str]:
    #     if not self.config.authentication_enabled:
    #         raise HTTPException(status_code=401, detail="Authentication is disabled.")
    #     if ":" not in token:
    #         raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    #     split_token = token.split(":")
    #     if len(split_token) != 2:
    #         raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    #     api_key, api_secret = split_token
    #     if api_key not in self.config.authentication_accounts:
    #         raise HTTPException(status_code=401, detail="API key not found.")
    #     if api_secret != self.config.authentication_accounts[api_key]:
    #         raise HTTPException(status_code=401, detail="API secret is incorrect.")
    #     return api_key, api_secret

    # noinspection DuplicatedCode
    def handle_request(self, caller: None, **kwargs) -> Any | None:
        # check if client ip is allowed
        allowed = False
        for network in self.config.allowed_networks:
            if kwargs["client_ip"] in network:
                allowed = True
                break
        if not allowed:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=False, sms_id=None, result=f"Client IP address '{kwargs["client_ip"]}' is not allowed.")

        logger.debug(f"{self} - Accept message:\nclient='{kwargs["client_ip"]}'\nport={kwargs["client_ip"]}")

        return super().handle_request(caller=caller, **kwargs)

    def handle_sms_data(self, caller: None, **kwargs) -> tuple[str, str]:
        return kwargs["number"], kwargs["message"]

    def success_handler(self, caller: None, sms_id: int, result: str, **kwargs) -> Any:
        return sms_id

    def error_handler(self, caller: None, sms_id: int | None, result: str, **kwargs) -> Any:
        return RuntimeError(result)
