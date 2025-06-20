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

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sms_broker.statics import ASSETS_PATH
from sms_broker.db import Sms, SmsStatus
from sms_broker.server.server import BaseServer
from starlette.requests import Request

from sms_broker.settings import settings
from wiederverwendbar.fastapi import FastAPI

if TYPE_CHECKING:
    from sms_broker.server.api.config import ApiServerConfig

logger = logging.getLogger(__name__)


class SmsSendApiModel(BaseModel):
    error: bool = Field(default=False, title="Error", description="Indicates if the request resulted in an error.")
    sms_id: int | None = Field(default=None, title="SMS ID", description="The ID of the queued SMS.")
    result: str = Field(default=..., title="Message", description="The message of the response.")


class SmsStatusApiModel(BaseModel):
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
        json_schema_extra = {
            "example": {"detail": "Not authenticated"}
        }


class SmsNotFoundError(BaseModel):
    detail: str

    class Config:
        json_schema_extra = {
            "example": {"detail": "SMS with id=1 not found!"},
        }


class SmsAbortError(BaseModel):
    detail: str

    class Config:
        json_schema_extra = {
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
        FastAPI.__init__(self,
                         lifespan=self._stated_done,
                         debug=self.config.debug,
                         title=f"{settings.branding_title} - {self.name}",
                         description=settings.branding_description,
                         version=f"v{settings.branding_version}",
                         terms_of_service=settings.branding_terms_of_service,
                         favicon=ASSETS_PATH / "favicon.ico",
                         docs_url=self.config.docs_web_path,
                         redoc_url=self.config.redoc_web_path,
                         contact={"name": settings.branding_author, "email": settings.branding_author_email},
                         license_info={"name": settings.branding_license, "url": settings.branding_license_url})

        self.init_done()

    def setup(self) -> None:
        super().setup()

        # async def validate_token() -> tuple[str, str]:
        #     return await self.get_api_credentials_from_token(token=token)

        if self.config.authentication_enabled:
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
                               _=Depends(self.get_api_credentials_from_token)) -> list[
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
                              _=Depends(self.get_api_credentials_from_token)) -> SmsStatusApiModel:
                return await self.get_sms(sms_id=sms_id)

            @self.post(path="/sms",
                       summary="Sending an SMS.",
                       tags=["API version 1"],
                       responses={401: {"model": Unauthorized}})
            async def send_sms(request: Request,
                               number: str,
                               message: str,
                               _=Depends(self.get_api_credentials_from_token)) -> SmsSendApiModel:
                return await self.send_sms(request=request,
                                           number=number,
                                           message=message)

            @self.patch(path="/sms/{sms_id}",
                        summary="Reset an SMS.",
                        tags=["API version 1"],
                        responses={401: {"model": Unauthorized},
                                   404: {"model": SmsNotFoundError}})
            async def reset_sms(sms_id: int,
                                _=Depends(self.get_api_credentials_from_token)) -> SmsStatusApiModel:
                return await self.reset_sms(sms_id=sms_id)

            @self.delete(path="/sms/{sms_id}",
                         summary="Abort an SMS.",
                         tags=["API version 1"],
                         responses={401: {"model": Unauthorized},
                                    403: {"model": SmsAbortError,
                                          "description": "Aborting SMS is not allowed."},
                                    404: {"model": SmsNotFoundError}})
            async def abort_sms(sms_id: int,
                                _=Depends(self.get_api_credentials_from_token)) -> SmsStatusApiModel:
                return await self.abort_sms(sms_id=sms_id)
        else:
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

    async def get_api_credentials_from_token(self, token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="/auth"))]) -> tuple[str, str]:
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
        if self.config.success_result is not None:
            result = self.config.success_result
        return SmsSendApiModel(error=False, sms_id=sms_id, result=result)

    def error_handler(self, caller: None, sms_id: int | None, result: str, **kwargs) -> Any:
        if self.config.error_result is not None:
            result = self.config.error_result
        return SmsSendApiModel(error=True, sms_id=sms_id, result=result)

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
        # get client_ip and client_port
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
