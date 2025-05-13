import logging
from enum import Enum
from typing import Literal

from vonage import Vonage, Auth, HttpClientOptions
from vonage_sms import SmsMessage, SmsResponse

from kds_sms_server import __title__
from kds_sms_server.gateways.base import BaseConfig, BaseGateway

logger = logging.getLogger(__name__)


class VonageGateway(BaseGateway):
    def get_vonage_instance(self, mode: Literal["check", "send"]) -> Vonage:
        # Create an Auth instance
        auth = Auth(api_key=self._config.api_key, api_secret=self._config.api_secret)

        # Create HttpClientOptions instance
        if mode == "check":
            options = HttpClientOptions(timeout=self._config.check_timeout, max_retries=self._config.check_retries)
        elif mode == "send":
            options = HttpClientOptions(timeout=self._config.timeout)
        else:
            raise ValueError("Invalid mode")

        # Create a Vonage instance
        vonage = Vonage(auth=auth, http_client_options=options)

        return vonage

    def _check(self) -> bool:
        vonage = self.get_vonage_instance(mode="check")
        balance = vonage.account.get_balance()
        log_msg = f"balance={balance.value}\n" \
                  f"auto_reload={balance.auto_reload}"

        logger.debug(f"Check result for {self}:\n{log_msg}")

        if balance.value >= self._config.check_min_balance:
            return True
        if self._config.check_auto_balance:
            if balance.auto_reload:
                return True
        return False

    def _send_sms(self, number: str, message: str) -> tuple[bool, str]:
        vonage = self.get_vonage_instance(mode="send")
        message = SmsMessage(to=number, from_=self._config.from_text, text=message, **{})
        response: SmsResponse = vonage.sms.send(message)
        logger.debug(f"response={response}")
        return True, "OK"

class VonageConfig(BaseConfig):
    _gateway_cls = VonageGateway

    class Type(str, Enum):
        VONAGE = "vonage"

    type: Type
    api_key: str
    api_secret: str
    from_text: str = __title__
    check_min_balance: float = 0.0
    check_auto_balance: bool = True
