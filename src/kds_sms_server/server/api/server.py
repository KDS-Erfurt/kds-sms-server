import logging
from contextlib import asynccontextmanager
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
from kds_sms_server.server.server import BaseServer
from starlette.requests import Request

if TYPE_CHECKING:
    from kds_sms_server.server.api.config import ApiServerConfig

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
    error: bool = Field(default=False, title="Error", description="Indicates if the request resulted in an error.")
    sms_id: int | None = Field(default=None, title="SMS ID", description="The ID of the queued SMS.")
    result: str = Field(default=..., title="Message", description="The message of the response.")


class ApiServer(BaseServer, FastAPI):
    def __init__(self, name: str, config: "ApiServerConfig"):
        BaseServer.__init__(self, name=name, config=config)

        FastAPI.__init__(
            self,
            lifespan=self._stated_done,
            debug=self.config.debug,
            title=f"{__title__} - {self.name}",
            summary=f"{__title__} API",
            description=__description__,
            version=__version__,
            terms_of_service="https://www.kds-kg.de/impressum",
            docs_url=None,
            redoc_url=None,
            contact={"name": __author__, "email": __author_email__},
            license_info={"name": __license__, "url": "https://www.gnu.org/licenses/gpl-3.0.html"}
        )

        if self.config.docs_web_path is not None or self.config.redoc_web_path is not None:
            @self.get('/favicon.ico', include_in_schema=False)
            async def favicon() -> FileResponse:
                return FileResponse(ASSETS_PATH / "favicon.ico")

        if self.config.docs_web_path is not None:
            @self.get(self.config.docs_web_path, include_in_schema=False)
            async def swagger():
                return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{__title__} - API Docs", swagger_favicon_url="/favicon.ico")

        if self.config.redoc_web_path is not None:
            @self.get(self.config.redoc_web_path, include_in_schema=False)
            async def redoc():
                return get_redoc_html(openapi_url="/openapi.json", title=f"{__title__} - API Docs", redoc_favicon_url="/favicon.ico")

        async def validate_token(token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="/auth"))]) -> tuple[str, str]:
            return await self.get_api_credentials_from_token(token=token)

        if self.config.authentication_enabled:
            @self.get(path="/info", summary="Get the application info.", tags=["API version 1"])
            async def get_info(_=Depends(validate_token)) -> InfoApiModel:
                return await self.get_info()
        else:
            @self.get(path="/info", summary="Get the application info.", tags=["API version 1"])
            async def get_info() -> InfoApiModel:
                return await self.get_info()

        if self.config.authentication_enabled:
            @self.post(path="/auth", summary="Authenticate against server.", tags=["API version 1"])
            async def post_auth(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
                return await self.post_auth(form_data=form_data)

        if self.config.authentication_enabled:
            @self.post(path="/sms", summary="Sending an SMS.", tags=["API version 1"])
            async def post_sms(request: Request, number: str, message: str, _=Depends(validate_token)) -> ResponseApiModel:
                return await self.post_sms(request=request, number=number, message=message)
        else:
            @self.post(path="/sms", summary="Sending an SMS.", tags=["API version 1"])
            async def post_sms(request: Request, number: str, message: str) -> ResponseApiModel:
                return await self.post_sms(request=request, number=number, message=message)

        self.init_done()

    @property
    def config(self) -> "ApiServerConfig":
        return super().config

    @staticmethod
    @asynccontextmanager
    async def _stated_done(api_server: "ApiServer"):
        api_server.stated_done()
        yield

    def enter(self):
        uvicorn.run(self, host=str(self.config.host), port=self.config.port)

    def exit(self):
        ...

    async def get_api_credentials_from_token(self, token: str) -> tuple[str, str]:
        if not self.config.authentication_enabled:
            raise HTTPException(status_code=401, detail="Authentication is disabled.")
        if ":" not in token:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        split_token = token.split(":")
        if len(split_token) != 2:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        api_key, api_secret = split_token
        if api_key not in self.config.authentication_accounts:
            raise HTTPException(status_code=401, detail="API key not found.")
        if api_secret != self.config.authentication_accounts[api_key]:
            raise HTTPException(status_code=401, detail="API secret is incorrect.")
        return api_key, api_secret

    def handle_request(self, caller: Any, client_ip: IPv4Address, client_port: int, **kwargs) -> Any:
        # check if client ip is allowed
        allowed = False
        for network in self.config.allowed_networks:
            if client_ip in network:
                allowed = True
                break
        if not allowed:
            return self.handle_response(caller=self, log_level=logging.WARNING, success=False, sms_id=None, result=f"Client IP address '{client_ip}' is not allowed.")
        return super().handle_request(caller=caller, client_ip=client_ip, client_port=client_port, **kwargs)

    def handle_sms_data(self, caller: None, **kwargs) -> tuple[str, str]:
        return kwargs["number"], kwargs["message"]

    def success_handler(self, caller: None, sms_id: int, result: str) -> Any:
        if self.config.success_result is not None:
            result = self.config.success_result
        return ResponseApiModel(error=False, sms_id=sms_id, result=result)

    def error_handler(self, caller: None, sms_id: int | None, result: str) -> Any:
        if self.config.error_result is not None:
            result = self.config.error_result
        return ResponseApiModel(error=True, sms_id=sms_id, result=result)

    async def get_info(self) -> InfoApiModel:
        return InfoApiModel()

    async def post_auth(self, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
        if not self.config.authentication_enabled:
            raise HTTPException(status_code=401, detail="Authentication is disabled.")
        if form_data.username not in self.config.authentication_accounts:
            raise HTTPException(status_code=401, detail="API key not found.")
        if form_data.password != self.config.authentication_accounts[form_data.username]:
            raise HTTPException(status_code=401, detail="API secret is incorrect.")
        return {"access_token": f"{form_data.username}:{form_data.password}", "token_type": "bearer"}

    async def post_sms(self, request: Request, number: str, message: str) -> ResponseApiModel:
        try:
            client_ip = IPv4Address(request.client.host)
            client_port = request.client.port
        except Exception as e:
            self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while parsing client IP address.")
            raise RuntimeError("This should never happen.")
        return self.handle_request(caller=None, client_ip=client_ip, client_port=client_port, number=number, message=message)
