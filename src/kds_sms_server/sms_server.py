import logging
import sys
import threading
import time

from kds_sms_server.console import console
from kds_sms_server.settings import Settings, settings
from kds_sms_server.server import BaseServer
from kds_sms_server.gateways import BaseGateway

logger = logging.getLogger(__name__)


class SmsServer:
    def __init__(self):
        logger.info(f"Initializing SMS-Server ...")
        self.lock = threading.Lock()
        self._settings = settings

        logger.info("Initializing servers ...")
        self._server: list[BaseServer] = []
        for server_config_name, server_config in self.settings.sms_server.items():
            server = server_config.cls(server=self, name=server_config_name, config=server_config)
            self._server.append(server)
        logger.debug("Initializing servers ... done")

        logger.info("Initializing gateways ...")
        # self._next_sms_gateway_index: int | None = None
        self._gateways: list[BaseGateway] = []
        for gateway_config_name, gateway_config in self.settings.sms_gateways.items():
            gateway = gateway_config.cls(server=self, name=gateway_config_name, config=gateway_config)
            self._gateways.append(gateway)
        logger.debug("Initializing gateways ... done")

        logger.debug(f"Initializing SMS-Server ... done")

    @property
    def settings(self) -> "Settings":
        return self._settings

    @property
    def server(self) -> tuple[BaseServer, ...]:
        return tuple(self._server)

    @property
    def gateways(self) -> tuple[BaseGateway, ...]:
        return tuple(self._gateways)

    # @property
    # def gateways(self) -> tuple[BaseGateway, ...]:
    #     with self.lock:
    #         if self._next_sms_gateway_index is None:
    #             self._next_sms_gateway_index = 0
    #         else:
    #             self._next_sms_gateway_index += 1
    #         if self._next_sms_gateway_index >= len(self._gateways):
    #             self._next_sms_gateway_index = 0
    #
    #         gateways = []
    #         for gateway in self._gateways[self._next_sms_gateway_index:]:
    #             gateways.append(gateway)
    #         if self._next_sms_gateway_index > 0:
    #             for gateway in self._gateways[:self._next_sms_gateway_index]:
    #                 gateways.append(gateway)
    #     return tuple(gateways)

    # def handle_sms(self, server: TcpServer | ApiServer, number: str, message: str) -> tuple[bool, str]:
    #     logger.debug(f"{server} - Processing SMS ...")
    #
    #     # check number
    #     if len(number) > self.settings.sms_number_max_size:
    #         return False, f"Received number is too long. Max size is '{self.settings.sms_number_max_size}'.\nnumber_size={len(number)}"
    #     _number = ""
    #     for char in number:
    #         if char not in list(self.settings.sms_number_allowed_chars):
    #             return False, f"Received number contains invalid characters. Allowed characters are '{self.settings.sms_number_allowed_chars}'.\nnumber='{number}'"
    #         if char in list(self.settings.sms_number_replace_chars):
    #             char = ""
    #         _number += char
    #     number = _number
    #     del _number
    #
    #     # replace zoro number
    #     if self.settings.sms_replace_zero_numbers is not None:
    #         if number.startswith("0"):
    #             number = self.settings.sms_replace_zero_numbers + number[1:]
    #
    #     # check a message
    #     if len(message) > self.settings.sms_message_max_size:
    #         return False, f"Received message is too long. Max size is '{self.settings.sms_message_max_size}'.\nmessage_size={len(message)}"
    #
    #     # log sms received successfully
    #     if self.settings.sms_logging:
    #         logger.debug(f"{server} - Processing SMS ... done\nnumber={number}\nmessage='{message}'")
    #     else:
    #         logger.debug(f"{server} - Processing SMS ... done\nnumber={number}")
    #
    #     # send sms to gateways
    #     for gateway in self.gateways:
    #         # check if gateway is available
    #         if not gateway.check():
    #             continue
    #
    #         # send it with gateway
    #         result = gateway.send_sms(number, message)
    #         if result:
    #             return True, ""
    #     return False, f"Error while sending SMS. Not gateways left."

    def loop(self):
        if len(self.server) == 0:
            logger.error(f"No servers are configured. Please check your settings.")
            sys.exit(1)
        if len(self.gateways) == 0:
            logger.error(f"No gateways are configured. Please check your settings.")
            sys.exit(1)

        logger.info(f"Starting SMS-Server ...")

        # starting servers
        for server in self.server:
            server.start()

        # waiting for servers to start

        while True:
            if not any(not server.is_started for server in self.server):
                break
            logger.debug(f"Waiting for servers to start ...")
            time.sleep(1.0)

        logger.debug(f"Starting SMS-Server ... done")
        console.print(f"SMS-Server is ready. Press CTRL+C to quit.")
        try:
            while True:
                time.sleep(0.001)
        except KeyboardInterrupt:
            logger.debug(f"KeyboardInterrupt received. Stopping SMS-Server ...")
        sys.exit(0)
