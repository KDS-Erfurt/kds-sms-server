import logging

import requests
from pythonping import ping
from enum import Enum

from kds_sms_server.gateways.base import BaseConfig, BaseGateway

logger = logging.getLogger(__name__)


class TeltonikaGateway(BaseGateway):
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
            return True
        else:
            return False

    def _send_sms(self, number: str, message: str) -> tuple[bool, str]:
        response = requests.get(f"http://{self._config.ip}:{self._config.port}/cgi-bin/sms_send",
                                params={"username": self._config.username,
                                        "password": self._config.password,
                                        "number": number,
                                        "text": message},
                                timeout=self._config.timeout)
        text = response.text.replace("\n", "")
        # log_msg = f"request='{response.url}'\n"
        if response.ok:
            return True, text
        else:
            return False, text


class TeltonikaConfig(BaseConfig):
    _gateway_cls = TeltonikaGateway

    class Type(str, Enum):
        TELTONIKA = "teletonika"

    type: Type
    ip: str
    port: int = 80
    username: str = ""
    password: str = ""
