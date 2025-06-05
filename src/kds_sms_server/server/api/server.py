import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from ipaddress import IPv4Address
from json import JSONDecodeError
from typing import TYPE_CHECKING, Annotated, Any

import uvicorn
from pydantic import BaseModel, Field

from fastapi import FastAPI, Depends, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from kds_sms_server import __title__, __description__, __version__, __author__, __author_email__, __license__
from kds_sms_server.assets import ASSETS_PATH
from kds_sms_server.db import Sms, SmsStatus
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


class SmsSendApiModel(BaseModel):
    error: bool = Field(default=False, title="Error", description="Indicates if the request resulted in an error.")
    sms_id: int | None = Field(default=None, title="SMS ID", description="The ID of the queued SMS.")
    result: str = Field(default=..., title="Message", description="The message of the response.")


class SmsStatusApiModel(BaseModel):
    class SmsStatus(str, Enum):
        QUEUED = "queued"
        SENT = "sent"
        ABORTED = "aborted"
        ERROR = "error"

    id: int = Field(default=..., title="ID", description="The ID of the SMS.")
    status: SmsStatus = Field(default=..., title="Status", description="The status of the SMS.")
    received_by: str = Field(default=..., title="Received by", description="The IP address of the server that received the SMS.")
    received_datetime: datetime = Field(default=..., title="Received datetime", description="The datetime when the SMS was received.")
    processed_datetime: datetime | None = Field(default=None, title="Processed datetime", description="The datetime when the SMS was processed.")
    sent_by: str | None = Field(default=None, title="Sent by", description="The IP address of the server that sent the SMS.")
    number: str = Field(default=..., title="Number", description="The phone number of the SMS.")
    message: str = Field(default=..., title="Message", description="The message of the SMS.")
    result: str | None = Field(default=None, title="Result", description="The result of the SMS.")
    log: str | None = Field(default=None, title="Log", description="The log of the SMS.")


class ListOrderBy(str, Enum):
    ID = "id"
    STATUS = "status"
    RECEIVED_BY = "received_by"
    RECEIVED_DATETIME = "received_datetime"
    PROCESSED_DATETIME = "processed_datetime"
    SENT_BY = "sent_by"
    NUMBER = "number"
    MESSAGE = "message"
    RESULT = "result"


class ListOrderDesc(str, Enum):
    ASC = "asc"
    DESC = "desc"


class Unauthorized(BaseModel):
    detail: str

    class Config:
        schema_extra = {
            "example": {"detail": "Not authenticated"}
        }


class SmsNotFoundError(BaseModel):
    detail: str

    class Config:
        schema_extra = {
            "example": {"detail": "SMS with id=1 not found!"},
        }


class SmsAbortError(BaseModel):
    detail: str

    class Config:
        schema_extra = {
            "example": {"detail": "Cannot abort SMS with id=1!"},
        }


class ApiServer(BaseServer, FastAPI):
    __str_columns__ = ["name",
                       ("debug", "config_debug"),
                       ("host", "config_host"),
                       ("port", "config_port"),
                       ("allowed_networks", "config_allowed_networks"),
                       ("authentication_enabled", "config_authentication_enabled")]

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
            @self.get('/favicon.ico',
                      include_in_schema=False)
            async def favicon() -> FileResponse:
                return FileResponse(ASSETS_PATH / "favicon.ico")

        if self.config.docs_web_path is not None:
            @self.get(self.config.docs_web_path,
                      include_in_schema=False)
            async def swagger():
                return get_swagger_ui_html(openapi_url="/openapi.json",
                                           title=f"{__title__} - API Docs",
                                           swagger_favicon_url="/favicon.ico")

        if self.config.redoc_web_path is not None:
            @self.get(self.config.redoc_web_path,
                      include_in_schema=False)
            async def redoc():
                return get_redoc_html(openapi_url="/openapi.json",
                                      title=f"{__title__} - API Docs",
                                      redoc_favicon_url="/favicon.ico")

        async def validate_token(token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="/auth"))]) -> tuple[str, str]:
            return await self.get_api_credentials_from_token(token=token)

        if self.config.authentication_enabled:
            @self.get(path="/info",
                      summary="Get the application info.",
                      tags=["API version 1"],
                      responses={401: {"model": Unauthorized}})
            async def get_info(_=Depends(validate_token)) -> InfoApiModel:
                return await self.get_info()

            @self.post(path="/auth",
                       summary="Authenticate against server.",
                       tags=["API version 1"])
            async def auth(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
                return await self.auth(form_data=form_data)

            @self.get(path="/sms",
                      summary="List SMS.",
                      tags=["API version 1"],
                      responses={401: {"model": Unauthorized}})
            async def list_sms(order_by: ListOrderBy = ListOrderBy.ID,
                               order_desc: ListOrderDesc = ListOrderDesc.ASC,
                               limit: int = 100,
                               page: int = 1,
                               query: str = "{}",
                               _=Depends(validate_token)) -> list[
                SmsStatusApiModel]:
                return await self.list_sms(order_by=order_by,
                                           order_desc=order_desc,
                                           limit=limit,
                                           page=page,
                                           query=query)

            @self.get(path="/sms/{sms_id}",
                      summary="Get SMS.",
                      tags=["API version 1"],
                      responses={401: {"model": Unauthorized},
                                 404: {"model": SmsNotFoundError}})
            async def get_sms(sms_id: int,
                              _=Depends(validate_token)) -> SmsStatusApiModel:
                return await self.get_sms(sms_id=sms_id)

            @self.post(path="/sms",
                       summary="Sending an SMS.",
                       tags=["API version 1"],
                       responses={401: {"model": Unauthorized}})
            async def send_sms(request: Request,
                               number: str,
                               message: str,
                               _=Depends(validate_token)) -> SmsSendApiModel:
                return await self.send_sms(request=request,
                                           number=number,
                                           message=message)

            @self.patch(path="/sms/{sms_id}",
                        summary="Reset an SMS.",
                        tags=["API version 1"],
                        responses={401: {"model": Unauthorized},
                                   404: {"model": SmsNotFoundError}})
            async def reset_sms(sms_id: int,
                                _=Depends(validate_token)) -> SmsStatusApiModel:
                return await self.reset_sms(sms_id=sms_id)

            @self.delete(path="/sms/{sms_id}",
                         summary="Abort an SMS.",
                         tags=["API version 1"],
                         responses={401: {"model": Unauthorized},
                                    403: {"model": SmsAbortError,
                                          "description": "Aborting SMS is not allowed."},
                                    404: {"model": SmsNotFoundError}})
            async def abort_sms(sms_id: int,
                                _=Depends(validate_token)) -> SmsStatusApiModel:
                return await self.abort_sms(sms_id=sms_id)
        else:
            @self.get(path="/info",
                      summary="Get the application info.",
                      tags=["API version 1"],
                      responses={401: {"model": Unauthorized}})
            async def get_info() -> InfoApiModel:
                return await self.get_info()

            @self.get(path="/sms",
                      summary="List SMS.",
                      tags=["API version 1"],
                      responses={401: {"model": Unauthorized}})
            async def list_sms(order_by: ListOrderBy = ListOrderBy.ID,
                               order_desc: ListOrderDesc = ListOrderDesc.ASC,
                               limit: int = 100,
                               page: int = 1,
                               query: str = "{}") -> list[SmsStatusApiModel]:
                return await self.list_sms(order_by=order_by,
                                           order_desc=order_desc,
                                           limit=limit,
                                           page=page,
                                           query=query)

            @self.get(path="/sms/{sms_id}",
                      summary="Get SMS.",
                      tags=["API version 1"],
                      responses={401: {"model": Unauthorized},
                                 404: {"model": SmsNotFoundError}})
            async def get_sms(sms_id: int) -> SmsStatusApiModel:
                return await self.get_sms(sms_id=sms_id)

            @self.post(path="/sms",
                       summary="Sending an SMS.",
                       tags=["API version 1"],
                       responses={401: {"model": Unauthorized}})
            async def send_sms(request: Request,
                               number: str,
                               message: str) -> SmsSendApiModel:
                return await self.send_sms(request=request,
                                           number=number,
                                           message=message)

            @self.patch(path="/sms/{sms_id}",
                        summary="Reset an SMS.",
                        tags=["API version 1"],
                        responses={401: {"model": Unauthorized},
                                   404: {"model": SmsNotFoundError}})
            async def reset_sms(sms_id: int) -> SmsStatusApiModel:
                return await self.reset_sms(sms_id=sms_id)

            @self.delete(path="/sms/{sms_id}",
                         summary="Abort an SMS.",
                         tags=["API version 1"],
                         responses={401: {"model": Unauthorized},
                                    403: {"model": SmsAbortError,
                                          "description": "Aborting SMS is not allowed."},
                                    404: {"model": SmsNotFoundError}})
            async def abort_sms(sms_id: int) -> SmsStatusApiModel:
                return await self.abort_sms(sms_id=sms_id)

        self.init_done()

    @property
    def config(self) -> "ApiServerConfig":
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

    # noinspection DuplicatedCode
    def handle_request(self, caller: Any, **kwargs) -> Any | None:
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

    def success_handler(self, caller: None, sms_id: int, result: str) -> Any:
        if self.config.success_result is not None:
            result = self.config.success_result
        return SmsSendApiModel(error=False, sms_id=sms_id, result=result)

    def error_handler(self, caller: None, sms_id: int | None, result: str) -> Any:
        if self.config.error_result is not None:
            result = self.config.error_result
        return SmsSendApiModel(error=True, sms_id=sms_id, result=result)

    async def get_info(self) -> InfoApiModel:
        return InfoApiModel()

    async def auth(self, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
        if not self.config.authentication_enabled:
            raise HTTPException(status_code=401, detail="Authentication is disabled.")
        if form_data.username not in self.config.authentication_accounts:
            raise HTTPException(status_code=401, detail="API key not found.")
        if form_data.password != self.config.authentication_accounts[form_data.username]:
            raise HTTPException(status_code=401, detail="API secret is incorrect.")
        return {"access_token": f"{form_data.username}:{form_data.password}", "token_type": "bearer"}

    async def list_sms(self,
                       order_by: ListOrderBy = ListOrderBy.ID,
                       order_desc: ListOrderDesc = ListOrderDesc.ASC,
                       limit: int = 100,
                       page: int = 1,
                       query: str = "{}") -> list[SmsStatusApiModel]:
        # try to parse query
        try:
            query_dict = json.loads(query)
        except JSONDecodeError as e:
            msg = f"Error while parsing query!"
            if self.config.debug:
                msg = f"{msg[:-1]}:\n{e}"
            logger.error(msg)
            raise HTTPException(status_code=442, detail=[{"loc": "query", "msg": msg}])

        # list from db
        sms_models: list[SmsStatusApiModel] = []
        for sms_dict in Sms.get_all(order_by=order_by.value, order_desc=order_desc is ListOrderDesc.DESC, rows_per_page=limit, page=page, as_dict=True, **query_dict):
            sms_model = SmsStatusApiModel(**sms_dict)
            sms_models.append(sms_model)
        return sms_models

    async def get_sms(self,
                      sms_id: int) -> SmsStatusApiModel:
        sms_dict = Sms.get(Sms.id == sms_id, as_dict=True)
        if sms_dict is None:
            raise HTTPException(status_code=404, detail=f"SMS with id={sms_id} not found.")
        sms_model = SmsStatusApiModel(**sms_dict)
        return sms_model

    async def send_sms(self,
                       request: Request,
                       number: str,
                       message: str) -> SmsSendApiModel:
        try:
            client_ip = IPv4Address(request.client.host)
            client_port = request.client.port
        except Exception as e:
            self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while parsing client IP address.")
            raise RuntimeError("This should never happen.")
        return self.handle_request(caller=None, number=number, message=message, client_ip=client_ip, client_port=client_port)

    async def reset_sms(self,
                        sms_id: int) -> SmsStatusApiModel:
        sms = Sms.get(Sms.id == sms_id)
        if sms is None:
            raise HTTPException(status_code=404, detail=f"SMS with id={sms_id} not found.")
        sms.update(status=SmsStatus.QUEUED,
                   processed_datetime=None,
                   sent_by=None,
                   result=None,
                   log=None)
        return await self.get_sms(sms_id=sms_id)

    async def abort_sms(self,
                        sms_id: int) -> SmsStatusApiModel:
        sms = Sms.get(Sms.id == sms_id)
        if sms is None:
            raise HTTPException(status_code=404, detail=f"SMS with id={sms_id} not found.")
        if sms.status != SmsStatus.QUEUED:
            raise HTTPException(status_code=403, detail=f"Cannot abort SMS with id={sms_id}! SMS is not in queued state.")
        sms.update(status=SmsStatus.ABORTED,
                   processed_datetime=None,
                   sent_by=None,
                   result=None,
                   log=None)
        return await self.get_sms(sms_id=sms_id)
