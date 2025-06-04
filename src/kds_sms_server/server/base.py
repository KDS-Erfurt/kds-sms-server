import logging
from abc import abstractmethod
from ipaddress import IPv4Address
from threading import Thread
from typing import Any, TYPE_CHECKING, Literal, Union

from pydantic import Field

from kds_sms_server.base import Base, BaseConfig

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SmsServer

logger = logging.getLogger(__name__)


class BaseServer(Base, Thread):
    def __init__(self, server: "SmsServer", name: str, config: "BaseServerConfig"):
        self._is_started = False
        Base.__init__(self, server=server, name=name, config=config)
        Thread.__init__(self, name=name, daemon=True)

    @property
    def is_started(self) -> bool:
        return self._is_started

    @property
    def config(self) -> Union["BaseServerConfig", Any]:
        return super().config

    def run(self):
        logger.info(f"Starting {self} ...")
        try:
            self.enter()
        except KeyboardInterrupt:
            logger.info(f"Stopping {self} ...")
            self.exit()
            logger.debug(f"Stopping {self} ... done")

    @abstractmethod
    def enter(self):
        ...

    def stated_done(self):
        logger.debug(f"Starting {self} ... done.")
        self._is_started = True

    @abstractmethod
    def exit(self):
        ...

    def log_and_handle_response(self, caller: Any, message: str, level: Literal["debug", "info", "warning", "error"] = "debug", error: bool | Exception = False) -> None:
        if message.endswith(".") or message.endswith(":"):
            message = message[:-1]
        e = ""
        if error and isinstance(error, Exception):
            e = str(error)
        if error and self.config.debug:
            response_msg = f"{message}:\n{e}"
        else:
            response_msg = f"{message}."
        if error:
            log_msg = f"{self} - {message}:\n{e}"
        else:
            log_msg = f"{self} - {message}."
        getattr(logger, level)(log_msg)
        self.handle_response(caller=caller, message=response_msg, error=error)

    def handle_request(self, caller: Any, client_ip: IPv4Address, client_port: int, **kwargs) -> Any:
        logger.debug(f"{self} - Accept message:\nclient='{client_ip}'\nport={client_port}")

        logger.debug(f"{self} - Progressing SMS body ...")
        try:
            number, message = self.handle_sms_body(caller=caller, **kwargs)
        except Exception as e:
            logger.error(f"{self} - Error while processing SMS body:\n{e}")
            return None
        logger.debug(f"{self} - Progressing SMS body ... done")

        result, message = self.sms_server.handle_sms(server=caller, number=number, message=message)

        # send a success message
        return self.handle_response(caller=caller, message=message, error=not result)

    @abstractmethod
    def handle_sms_body(self, caller: Any, **kwargs) -> tuple[str, str]:
        ...

    def handle_response(self, caller: Any, message: str, error: bool = False) -> Any:
        logger.debug(f"{self} - Sending Response.\nmessage='{message}'\nerror={error}\n")
        try:
            if error:
                return self.error_handler(caller=caller, message=message)
            return self.success_handler(caller=caller, message=message)
        except Exception as e:
            logger.error(f"{self} - Error while sending response message.\n{e}")
        return None

    @abstractmethod
    def success_handler(self, caller: Any, message: str) -> Any:
        ...

    @abstractmethod
    def error_handler(self, caller: Any, message: str) -> Any:
        ...


class BaseServerConfig(BaseConfig):
    debug: bool = Field(default=False, title="Debug", description="If set to True, server will be started in debug mode.")

    @property
    def cls(self) -> type[BaseServer]:
        cls = super().cls
        if not issubclass(cls, BaseServer):
            raise TypeError(f"Server class '{cls.__name__}' is not a subclass of '{BaseServer.__name__}'")
        return cls
