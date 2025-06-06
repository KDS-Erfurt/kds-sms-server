import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Union, Any

from sms_broker.base import Base

if TYPE_CHECKING:
    from sms_broker.gateways.config import BaseGatewayConfig

logger = logging.getLogger(__name__)


class BaseGateway(Base):
    __str_columns__ = ["name",
                       ("dry_run", "config_dry_run")]

    def __init__(self, name: str, config: "BaseGatewayConfig"):
        Base.__init__(self, name=name, config=config)

        self._state = False

        self.init_done()

    @property
    def config(self) -> Union["BaseGatewayConfig", Any]:
        return super().config

    @property
    def config_dry_run(self) -> bool:
        return self.config.dry_run

    @property
    def state(self) -> bool:
        return self._state

    @state.setter
    def state(self, value: bool):
        self._state = value

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

    def send_sms(self, number: str, message: str) -> tuple[bool, int, str]:
        logger.debug(f"Sending SMS via {self} ...")
        log_level = logging.DEBUG
        success = False
        try:
            if not self.state:
                raise RuntimeError(f"SMS gateway {self} is not available!")
            if self._config.dry_run:
                log_level = logging.WARNING
                success = True
                result = f"Dry run mode is enabled. SMS will not sent via {self}."
            else:
                success, gateway_result = self._send_sms(number, message)
                if success:
                    result = f"SMS sent successfully via {self}. \nGateway result: {gateway_result}"
                else:
                    result = f"Failed to send SMS via {self}. \nGateway result: {gateway_result}"
        except Exception as e:
            result = f"Failed to send SMS via {self}.\nException: {e}"

        if not success:
            log_level = logging.ERROR

        return success, log_level, result

    @abstractmethod
    def _send_sms(self, number: str, message: str) -> tuple[bool, str]:
        ...
