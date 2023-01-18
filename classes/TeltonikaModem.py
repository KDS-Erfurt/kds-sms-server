import requests as requests
from pythonping import ping

from classes.Logger import LOG
from classes.SMSBaseGateway import SMSBaseGateway
from classes.Settings import Settings


class TeltonikaModem(SMSBaseGateway):
    def __init__(self, modem_config: Settings.ModemConfig):
        super().__init__()
        self.modem_config = modem_config

    def check(self) -> bool:
        result = ping(self.modem_config.ip, self.modem_config.check_timeout, count=self.modem_config.check_retries)

        LOG.debug(f"packets_loss={result.packet_loss}")
        LOG.debug(f"rtt_avg={result.rtt_avg_ms}")
        LOG.debug(f"rtt_max={result.rtt_max_ms}")
        LOG.debug(f"rtt_min={result.rtt_min_ms}")
        LOG.debug(f"packets_sent={result.stats_packets_sent}")
        LOG.debug(f"packets_received={result.stats_packets_returned}")

        if result.success():
            return True
        else:
            return False

    def send_sms(self, number: str, message: str) -> tuple[bool, str]:
        response = requests.get(f"http://{self.modem_config.ip}:{self.modem_config.port}/cgi-bin/sms_send",
                                params={"username": self.modem_config.username,
                                        "password": self.modem_config.password,
                                        "number": number,
                                        "text": message},
                                timeout=self.modem_config.timeout)
        LOG.debug(f"request='{response.url}'")
        text = response.text.replace("\n", "")
        LOG.debug(f"response='{text}'")
        if response.ok:
            return True, text
        else:
            return False, text
