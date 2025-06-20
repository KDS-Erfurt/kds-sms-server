import json
import logging
from typing import Literal, TYPE_CHECKING

from vonage import Vonage, Auth, HttpClientOptions
from vonage_sms import SmsMessage, SmsResponse

from sms_broker.gateways.gateway import BaseGateway

if TYPE_CHECKING:
    from sms_broker.gateways.vonage.config import VonageGatewayConfig

logger = logging.getLogger(__name__)


class VonageGateway(BaseGateway):
    @property
    def config(self) -> "VonageGatewayConfig":
        return super().config

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
        if not self.config.check_balance:
            return True
        balance = vonage.account.get_balance()
        log_msg = f"balance={balance.value}\n" \
                  f"auto_reload={balance.auto_reload}"

        logger.debug(f"Checking account balance for {self}:\n{log_msg}")

        if balance.value >= self._config.check_min_balance:
            logger.debug(f"Balance for {self} is enough.")
            return True
        if self._config.check_auto_balance:
            if balance.auto_reload:
                logger.debug(f"Balance for {self} is not enough. But auto_reload is enabled.")
                return True
            logger.warning(f"Balance for {self} is not enough and auto_reload is disabled.")
        else:
            logger.warning(f"Balance for {self} is not enough.")
        return False

    def _send_sms(self, number: str, message: str) -> tuple[bool, str]:
        vonage = self.get_vonage_instance(mode="send")
        message = SmsMessage(to=number, from_=self._config.from_text, text=message, **{})
        sms_response: SmsResponse = vonage.sms.send(message)

        # check status for all messages
        success = True
        for message in sms_response.messages:
            if message.status != "0":
                success = False
                break

        # convert sms_response to pretty json
        sms_response_dict = []
        for message in sms_response.messages:
            sms_response_dict.append(message.model_dump(mode="json"))
        sms_response_json = json.dumps(sms_response_dict, indent=4)

        return success, sms_response_json
