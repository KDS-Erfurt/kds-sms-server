import logging
from typing import TYPE_CHECKING

import requests
from pythonping import ping

from kds_sms_server.gateways.gateway import BaseGateway

if TYPE_CHECKING:
    from kds_sms_server.gateways.teltonika.config import TeltonikaGatewayConfig

logger = logging.getLogger(__name__)


class TeltonikaGateway(BaseGateway):
    @property
    def config(self) -> "TeltonikaGatewayConfig":
        return super().config

    def _check(self) -> bool:
        result = ping(self._config.ip, self._config.check_timeout, count=self._config.check_retries)

        log_msg = f"packets_loss={result.packet_loss}\n" \
                  f"rtt_avg={result.rtt_avg_ms}\n" \
                  f"rtt_max={result.rtt_max_ms}\n" \
                  f"rtt_min={result.rtt_min_ms}\n" \
                  f"packets_sent={result.stats_packets_sent}\n" \
                  f"packets_received={result.stats_packets_returned}"

        logger.debug(f"Check result for {self}:\n{log_msg}")

        if result.success():
            logger.debug(f"Ping for {self} was successful.")
            return True
        else:
            logger.warning(f"Ping for {self} was unsuccessful.")
            return False

    def _send_sms(self, number: str, message: str) -> tuple[bool, str]:
        response = requests.get(f"http://{self._config.ip}:{self._config.port}/cgi-bin/sms_send",
                                params={"username": self._config.username,
                                        "password": self._config.password,
                                        "number": number,
                                        "text": message},
                                timeout=self._config.timeout)
        gateway_result = response.text.replace("\n", "")
        if response.ok:
            return True, gateway_result
        else:
            return False, gateway_result
