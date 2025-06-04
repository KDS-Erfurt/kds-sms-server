import logging
from enum import Enum
from typing import Literal

from pydantic import Field
from vonage import Vonage, Auth, HttpClientOptions
from vonage_sms import SmsMessage, SmsResponse

from kds_sms_server.gateways.base import BaseGateway, BaseGatewayConfig

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


class VonageGatewayConfig(BaseGatewayConfig):
    _gateway_cls = VonageGateway

    class Type(str, Enum):
        VONAGE = "vonage"

    type: Type = Field(default=..., title="Type", description="Type of the gateway.")
    api_key: str = Field(default="", title="API key", description="API key for authentication.")
    api_secret: str = Field(default="", title="API secret", description="API secret for authentication.")
    from_text: str = Field(default="1234567890123", title="From Text", description="From Text visible for recipient.")
    check_min_balance: float = Field(default=0.0, title="Check min balance", description="Minimum balance required for checking gateway availability.")
    check_auto_balance: bool = Field(default=True, title="Check auto balance",
                                     description="If set to True, min balance will be ignored if the vonage api returns an auto reload flag.")
