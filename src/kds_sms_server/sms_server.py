import logging
import threading
import time

from kds_sms_server.console import console
from kds_sms_server.settings import settings
from kds_sms_server.gateways import BaseGateway
from kds_sms_server.server.tcp import TcpServer
from kds_sms_server.server.api import ApiServer

logger = logging.getLogger(__name__)


class SmsServer:
    def __init__(self):
        self.lock = threading.Lock()

        logger.debug(f"Initializing {self} ...")

        # tcp server
        self.tcp_server: TcpServer | None = None
        if settings.tcp_server_enabled:
            self.tcp_server = TcpServer(sms_server=self)

        # api server
        self.api_server: ApiServer | None = None
        if settings.api_server_enabled:
            self.api_server = ApiServer(sms_server=self)

        logger.debug("Initializing gateways ...")
        self._next_sms_gateway_index: int | None = None
        self._gateways: list[BaseGateway] = []
        for gateway_config_name, gateway_config in settings.gateways.items():
            gateway = gateway_config.cls(server=self, name=gateway_config_name, config=gateway_config)
            self._gateways.append(gateway)

        # starting servers
        if self.tcp_server is not None:
            self.tcp_server.start()
        if self.api_server is not None:
            self.api_server.start()
        else:
            self.done()
            try:
                while True:
                    time.sleep(0.001)
            except KeyboardInterrupt:
                ...

    def __str__(self):
        tcp_server = getattr(self, "tcp_server", settings.tcp_server_enabled)
        api_server = getattr(self, "api_server", settings.api_server_enabled)
        return (f"{self.__class__.__name__}("
                f"tcp_server={tcp_server}, "
                f"api_server={api_server})")

    def done(self):
        logger.debug(f"Initializing {self} ... done")
        console.print(f"{self} is ready. Press CTRL+C to quit.")

    @property
    def gateways(self) -> tuple[BaseGateway, ...]:
        with self.lock:
            if self._next_sms_gateway_index is None:
                self._next_sms_gateway_index = 0
            else:
                self._next_sms_gateway_index += 1
            if self._next_sms_gateway_index >= len(self._gateways):
                self._next_sms_gateway_index = 0

            gateways = []
            for gateway in self._gateways[self._next_sms_gateway_index:]:
                gateways.append(gateway)
            if self._next_sms_gateway_index > 0:
                for gateway in self._gateways[:self._next_sms_gateway_index]:
                    gateways.append(gateway)
        return tuple(gateways)

    def handle_sms(self, server: TcpServer | ApiServer, number: str, message: str) -> tuple[bool, str]:
        logger.debug(f"{server} - Processing SMS ...")

        # check number
        if len(number) > settings.sms_number_max_size:
            return False, f"Received number is too long. Max size is '{settings.sms_number_max_size}'.\nnumber_size={len(number)}"
        _number = ""
        for char in number:
            if char not in list(settings.sms_number_allowed_chars):
                return False, f"Received number contains invalid characters. Allowed characters are '{settings.sms_number_allowed_chars}'.\nnumber='{number}'"
            if char in list(settings.sms_number_replace_chars):
                char = ""
            _number += char
        number = _number
        del _number

        # replace zoro number
        if settings.sms_replace_zero_numbers is not None:
            if number.startswith("0"):
                number = settings.sms_replace_zero_numbers + number[1:]

        # check a message
        if len(message) > settings.sms_message_max_size:
            return False, f"Received message is too long. Max size is '{settings.sms_message_max_size}'.\nmessage_size={len(message)}"

        # log sms received successfully
        if settings.sms_logging:
            logger.debug(f"{server} - Processing SMS ... done\nnumber={number}\nmessage='{message}'")
        else:
            logger.debug(f"{server} - Processing SMS ... done\nnumber={number}")

        # send sms to gateways
        for gateway in self.gateways:
            # check if gateway is available
            if not gateway.check():
                continue

            # send it with gateway
            result = gateway.send_sms(number, message)
            if result:
                return True, ""
        return False, f"Error while sending SMS. Not gateways left."
