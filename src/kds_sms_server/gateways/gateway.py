import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Union, Any

from kds_sms_server.base import Base

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SmsServer
    from kds_sms_server.gateways.config import BaseGatewayConfig

logger = logging.getLogger(__name__)


class BaseGateway(Base):
    def __init__(self, server: "SmsServer", name: str, config: "BaseGatewayConfig"):
        Base.__init__(self, server=server, name=name, config=config)

        self._state = False
        self._sms_send_count = 0
        self._sms_send_error_count = 0

        self.init_done()

    @property
    def config(self) -> Union["BaseGatewayConfig", Any]:
        return super().config

    @property
    def state(self) -> bool:
        return self._state

    @state.setter
    def state(self, value: bool):
        self._state = value

    @property
    def sms_send_count(self) -> int:
        return self._sms_send_count

    @sms_send_count.setter
    def sms_send_count(self, value: int):
        self._sms_send_count = value

    @property
    def sms_send_error_count(self) -> int:
        return self._sms_send_error_count

    @sms_send_error_count.setter
    def sms_send_error_count(self, value: int):
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
                result = True
                logger.warning(f"Dry run mode is enabled. SMS will not be sent via {self}.")
            else:
                result, msg = self._send_sms(number, message)
                if result:
                    logger.debug(f"SMS sent successfully via {self}. \nGateway result: {msg}")
                else:
                    logger.error(f"Error while sending SMS via {self}.\nGateway result: {msg}")
        except Exception as e:
            result = False, f"Failed to send SMS via {self}.\nException: {e}"
            logger.error(f"Failed to send SMS via {self}.\nException: {e}")

        if not result:
            self.sms_send_error_count += 1

        return result

    @abstractmethod
    def _send_sms(self, number: str, message: str) -> tuple[bool, str]:
        ...

    def reset_metrics(self):
        self.sms_send_count = 0
        self.sms_send_error_count = 0
