import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, PrivateAttr

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SMSServer

logger = logging.getLogger(__name__)


class BaseGateway(ABC):
    def __init__(self, server: "SMSServer", name: str, config: "BaseConfig"):
        self.lock = threading.Lock()
        self._name = name
        self._server = server
        self._config = config

        logger.debug(f"Initializing {self} ...")

        self._state = False
        self._sms_send_count = 0
        self._sms_send_error_count = 0

        logger.debug(f"Initializing {self} done.")

    def __str__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"

    @property
    def name(self) -> str:
        with self.lock:
            return self._name

    @property
    def state(self) -> bool:
        with self.lock:
            return self._state

    @state.setter
    def state(self, value: bool):
        with self.lock:
            self._state = value

    @property
    def sms_send_count(self) -> int:
        with self.lock:
            return self._sms_send_count

    @sms_send_count.setter
    def sms_send_count(self, value: int):
        with self.lock:
            self._sms_send_count = value

    @property
    def sms_send_error_count(self) -> int:
        with self.lock:
            return self._sms_send_error_count

    @sms_send_error_count.setter
    def sms_send_error_count(self, value: int):
        with self.lock:
            self._sms_send_error_count = value

    def check(self) -> bool:
        if not self._config.check:
            logger.warning(f"Gateway check is disabled for {self}. This is not recommended!")
            self.state = True
            return True
        try:
            logger.debug(f"Checking gateway {self} ...")
            if self._check():
                logger.debug(f"Gateway {self} is available.")
                self.state = True
                return True
            logger.warning(f"Gateway {self} is not available.")
        except Exception as e:
            logger.error(f"Gateway {self} check failed.\nException: {e}")
        self.state = False
        return False

    @abstractmethod
    def _check(self) -> bool:
        ...

    def send_sms(self, number: str, message: str) -> bool:
        logger.debug(f"Sending SMS via {self} ...")
        self.sms_send_count += 1
        try:
            if not self.state:
                raise RuntimeError(f"SMS gateway {self} is not available!")
            if self._config.dry_run:
                result, msg = True, f"Dry run mode is enabled. SMS will not be sent via {self}."
            else:
                result, msg = self._send_sms(number, message)
        except Exception as e:
            result, msg = False, f"Failed to send SMS via {self}.\nException: {e}"

        if not result:
            self.sms_send_error_count += 1

        if result:
            logger.debug(f"SMS sent successfully via {self}. \nGateway result: {msg}")
        else:
            logger.error(f"Error while sending SMS via {self}.\nGateway result: {msg}")

        return result

    @abstractmethod
    def _send_sms(self, number: str, message: str) -> tuple[bool, str]:
        ...

    def reset_metrics(self):
        self.sms_send_count = 0
        self.sms_send_error_count = 0


class BaseConfig(BaseModel):
    class Config:
        use_enum_values = True

    _gateway_cls: type[BaseGateway] | None = PrivateAttr(None)
    dry_run: bool = False
    timeout: int = 5
    check: bool = True
    check_timeout: int = 1
    check_retries: int = 3

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        _ = self.gateway_cls

    @property
    def gateway_cls(self) -> type[BaseGateway]:
        if self._gateway_cls is None:
            raise ValueError("Gateway class is not set")
        if not issubclass(self._gateway_cls, BaseGateway):
            raise TypeError(f"Gateway class '{self._gateway_cls.__name__}' is not a subclass of '{BaseGateway.__name__}'")
        return self._gateway_cls
