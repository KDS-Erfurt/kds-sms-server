import logging
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Annotated, Any

import uvicorn
from pydantic import BaseModel, Field

from fastapi import FastAPI, Depends, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from kds_sms_server import __title__, __description__, __version__, __author__, __author_email__, __license__
from kds_sms_server.assets import ASSETS_PATH
from kds_sms_server.server.base import BaseServer
from kds_sms_server.settings import settings
from starlette.requests import Request

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SMSServer

logger = logging.getLogger(__name__)


class InfoApiModel(BaseModel):
    title: str = Field(default="Application Title", title="Application Title", description="The title of the application.")
    description: str = Field(default="Application Description", title="Application Description", description="The description of the application.")
    version: str = Field(default="Application Version", title="Application Version", description="The version of the application.")
    author: str = Field(default="Application Author", title="Application Author", description="The author of the application.")
    author_email: str = Field(default="Application Author Email", title="Application Author Email", description="The author email of the application.")
    license: str = Field(default="Application License", title="Application License", description="The license of the application.")

    def __init__(self, /, **data: Any):
        data["title"] = __title__
        data["description"] = __description__
        data["version"] = "v" + __version__
        data["version_full"] = __version__
        data["version_major"] = __version__.split(".")[0]
        data["version_minor"] = __version__.split(".")[1]
        data["version_bugfix"] = __version__.split(".")[2]
        data["author"] = __author__
        data["author_email"] = __author_email__
        data["license"] = __license__

        super().__init__(**data)


class ResponseApiModel(BaseModel):
    message: str = Field(default=..., title="Message", description="The message of the response.")


class APIServer(BaseServer, FastAPI):
    def __init__(self, sms_server: "SMSServer"):
        self.sms_server = sms_server
        self.host = str(settings.api_server_host)
        self.port = settings.api_server_port

        logger.debug(f"Initializing {self} ...")

        BaseServer.__init__(self,
                            sms_server=sms_server,
                            host=settings.api_server_host,
                            port=settings.api_server_port,
                            debug=settings.debug,
                            allowed_networks=settings.api_server_allowed_networks,
                            success_message=settings.api_server_success_message,
                            success_handler=self._handle_response,
                            error_handler=self._handle_error_response)
        FastAPI.__init__(
            self,
            debug=settings.debug,
            title=__title__,
            summary=f"{__title__} API",
            description=__description__,
            version=__version__,
            terms_of_service="https://www.kds-kg.de/impressum",
            docs_url=None,
            redoc_url=None,
            contact={"name": __author__, "email": __author_email__},
            license_info={"name": __license__, "url": "https://www.gnu.org/licenses/gpl-3.0.html"}
        )

        self._info = InfoApiModel()

        if settings.api_server_docs_web_path is not None or settings.api_server_redoc_web_path is not None:
            @self.get('/favicon.ico', include_in_schema=False)
            async def favicon() -> FileResponse:
                return FileResponse(ASSETS_PATH / "favicon.ico")

        if settings.api_server_docs_web_path is not None:
            @self.get(settings.api_server_docs_web_path, include_in_schema=False)
            async def swagger():
                return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{__title__} - API Docs", swagger_favicon_url="/favicon.ico")

        if settings.api_server_redoc_web_path is not None:
            @self.get(settings.api_server_redoc_web_path, include_in_schema=False)
            async def redoc():
                return get_redoc_html(openapi_url="/openapi.json", title=f"{__title__} - API Docs", redoc_favicon_url="/favicon.ico")

        async def validate_token(token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="/auth"))]) -> tuple[str, str]:
            return await self.get_api_credentials_from_token(token=token)

        if settings.api_server_authentication_enabled:
            @self.get(path="/info", summary="Get the application info.", tags=["API version 1"])
            async def get_info(_=Depends(validate_token)) -> InfoApiModel:
                return await self.get_info()
        else:
            @self.get(path="/info", summary="Get the application info.", tags=["API version 1"])
            async def get_info() -> InfoApiModel:
                return await self.get_info()

        if settings.api_server_authentication_enabled:
            @self.post(path="/auth", summary="Authenticate against server.", tags=["API version 1"])
            async def post_auth(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
                return await self.post_auth(form_data=form_data)

        if settings.api_server_authentication_enabled:
            @self.post(path="/sms", summary="Sending an SMS.", tags=["API version 1"])
            async def post_sms(request: Request, number: str, message: str, _=Depends(validate_token)) -> ResponseApiModel:
                return await self.post_sms(request=request, number=number, message=message)
        else:
            @self.post(path="/sms", summary="Sending an SMS.", tags=["API version 1"])
            async def post_sms(request: Request, number: str, message: str) -> ResponseApiModel:
                return await self.post_sms(request=request, number=number, message=message)

        self.done()

    def start(self):
        try:
            self.run()
        except KeyboardInterrupt:
            logger.info(f"Keyboard Interrupt {self}")

    def run(self):
        uvicorn.run(self,
                    host=self.host,
                    port=self.port)

    @classmethod
    async def get_api_credentials_from_token(cls, token: str) -> tuple[str, str]:
        if not settings.api_server_authentication_enabled:
            raise HTTPException(status_code=401, detail="Authentication is disabled.")
        if ":" not in token:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        split_token = token.split(":")
        if len(split_token) != 2:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        api_key, api_secret = split_token
        if api_key not in settings.api_server_authentication_accounts:
            raise HTTPException(status_code=401, detail="API key not found.")
        if api_secret != settings.api_server_authentication_accounts[api_key]:
            raise HTTPException(status_code=401, detail="API secret is incorrect.")
        return api_key, api_secret

    def _handle_sms_body(self, caller: None, **kwargs) -> tuple[str, str]:
        return kwargs["number"], kwargs["message"]

    def _handle_response(self, caller: None, message: str) -> Any:
        return ResponseApiModel(message=message)

    def _handle_error_response(self, caller: None, message: str) -> None:
        print()

    async def get_info(self) -> InfoApiModel:
        return self._info

    async def post_auth(self, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
        if not settings.api_server_authentication_enabled:
            raise HTTPException(status_code=401, detail="Authentication is disabled.")
        if form_data.username not in settings.api_server_authentication_accounts:
            raise HTTPException(status_code=401, detail="API key not found.")
        if form_data.password != settings.api_server_authentication_accounts[form_data.username]:
            raise HTTPException(status_code=401, detail="API secret is incorrect.")
        return {"access_token": f"{form_data.username}:{form_data.password}", "token_type": "bearer"}

    async def post_sms(self, request: Request, number: str, message: str) -> ResponseApiModel:
        try:
            client_ip = IPv4Address(request.client.host)
            client_port = request.client.port
        except Exception as e:
            self.log_and_handle_response(caller=self, message=f"Error while parsing client IP address.", level="error", error=e)
            raise RuntimeError("This should never happen.")
        return self.handle_request(caller=None, client_ip=client_ip, client_port=client_port, number=number, message=message)
