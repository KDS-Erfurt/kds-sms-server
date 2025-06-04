import logging
from abc import ABC, abstractmethod
from ipaddress import IPv4Network, IPv4Address
from typing import Any, TYPE_CHECKING, Literal

from pydantic import BaseModel, PrivateAttr

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SmsServer

logger = logging.getLogger(__name__)


class BaseServer(ABC):
    def __init__(self,
                 sms_server: "SmsServer",
                 host: str,
                 port: int,
                 debug: bool,
                 allowed_networks: list[IPv4Network] | None = None,
                 success_message: str = "OK",
                 success_handler: callable = None,
                 error_handler: callable = None):
        self.sms_server = sms_server
        self.host = host
        self.port = port
        self.debug = debug
        if allowed_networks is None:
            allowed_networks = []
        self.allowed_networks = allowed_networks
        self.success_message = success_message
        self.success_handler = success_handler
        if self.success_handler is None:
            self.success_handler = self._handle_response
        self.error_handler = error_handler
        if self.error_handler is not None:
            self.error_handler = self._handle_response

        logger.debug(f"Initializing {self} ...")

    def __str__(self):
        return f"{self.__class__.__name__}(host='{self.host}', port={self.port})"

    def done(self):
        logger.debug(f"Initializing {self} ... done")

    @abstractmethod
    def start(self):
        ...

    def run(self):
        logger.debug(f"{self} started.")
        try:
            self.enter()
        except KeyboardInterrupt:
            logger.debug(f"Stopping {self} ...")
            self.exit()
            logger.debug(f"Stopping {self} ... done")

    @abstractmethod
    def enter(self):
        ...

    @abstractmethod
    def exit(self):
        ...

    def log_and_handle_response(self, caller: Any, message: str, level: Literal["debug", "info", "warning", "error"] = "debug", error: bool | Exception = False) -> None:
        if message.endswith(".") or message.endswith(":"):
            message = message[:-1]
        e = ""
        if error and isinstance(error, Exception):
            e = str(error)
        if error and self.debug:
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
        # check if client ip is allowed
        if not self.check_is_allowed_network(client_ip=client_ip):
            return self.log_and_handle_response(caller=self, message=f"Client IP address '{client_ip}' is not allowed.", level="warning", error=True)

        logger.debug(f"{self} - Accept message:\nclient='{client_ip}'\nport={client_port}")

        logger.debug(f"{self} - Progressing SMS body ...")
        try:
            number, message = self._handle_sms_body(caller=caller, **kwargs)
        except Exception as e:
            logger.error(f"{self} - Error while processing SMS body:\n{e}")
            return None
        logger.debug(f"{self} - Progressing SMS body ... done")

        result, message = self.sms_server.handle_sms(server=caller, number=number, message=message)

        # send a success message
        return self.handle_response(caller=caller, message=message, error=not result)

    @abstractmethod
    def _handle_sms_body(self, caller: Any, **kwargs) -> tuple[str, str]:
        ...

    def handle_response(self, caller: Any, message: str, error: bool = False) -> Any:
        if not error:
            message = self.success_message
        logger.debug(f"{self} - Sending Response.\nmessage='{message}'\nerror={error}\n")
        try:
            if error:
                return self.error_handler(caller=caller, message=message)
            return self.success_handler(caller=caller, message=message)
        except Exception as e:
            logger.error(f"{self} - Error while sending response message.\n{e}")
        return None

    @abstractmethod
    def _handle_response(self, caller: Any, message: str) -> Any:
        ...

    def check_is_allowed_network(self, client_ip: IPv4Address) -> bool:
        # check if client ip is allowed
        for network in self.allowed_networks:
            if client_ip in network:
                return True
        return False


class BaseServerConfig(BaseModel):
    class Config:
        use_enum_values = True

    _server_cls: type[BaseServer] | None = PrivateAttr(None)

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        _ = self.server_cls

    @property
    def server_cls(self) -> type[BaseServer]:
        if self._server_cls is None:
            raise ValueError("Server class is not set")
        if not issubclass(self._server_cls, BaseServer):
            raise TypeError(f"Server class '{self._server_cls.__name__}' is not a subclass of '{BaseServer.__name__}'")
        return self._server_cls
