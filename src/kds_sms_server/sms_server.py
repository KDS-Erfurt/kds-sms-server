import logging
import socketserver
import sys
from typing import Optional

import chardet

from kds_sms_server.settings import settings
from kds_sms_server.gateways import BaseGateway

logger = logging.getLogger(__name__)


class SMSServerHandler(socketserver.BaseRequestHandler):
    server: Optional["SMSServer"]

    def handle(self):
        # handle incoming SMS
        try:
            client_ip, client_port = self.client_address
            logger.debug(f"Received message. client='{client_ip}:{client_port}'")

            data = self.request.recv(settings.sms_data_max_size).strip()
            logger.debug(f"data={data}")

            # detect encoding
            encoding = settings.sms_in_encoding
            if encoding == "auto":
                encoding = chardet.detect(data)['encoding']

            logger.debug(f"encoding={encoding}")

            # decode message
            data_str = data.decode(encoding)
            logger.debug(f"data_str='{data_str}'")

            # split message
            if "\r\n" not in data_str:
                return self.handel_response(message=f"Received data is not valid.", error=True)

            number, message = data_str.split("\r\n")

            # check number
            if len(number) > settings.sms_number_max_size:
                return self.handel_response(message=f"Received number is too long. \n"
                                                    f"Max size is '{settings.sms_number_max_size}'.\n"
                                                    f"number_size={len(number)}",
                                            error=True)

            # replace zoro number
            if settings.sms_replace_zero_numbers is not None:
                if number.startswith("0"):
                    number = settings.sms_replace_zero_numbers + number[1:]

            # check a message
            if len(message) > settings.sms_message_max_size:
                return self.handel_response(message=f"Received message is too long. \n"
                                                    f"Max size is '{settings.sms_message_max_size}'.\n"
                                                    f"message_size={len(message)}",
                                            error=True)
        except Exception as e:
            return self.handel_response(message=str(e), error=True)

        # sms received successfully
        if settings.sms_logging:
            logger.info(f"Received SMS client='{client_ip}:{client_port}' number={number}, message='{message}'")
        else:
            logger.info(f"Received SMS client='{client_ip}:{client_port}' number={number}")

        # send sms to gateways
        result = False
        for gateway in self.server.gateways:
            # check if gateway is available
            if not gateway.check():
                continue

            result = gateway.send_sms(number, message)

            if result:
                break

        if not result:
            return self.handel_response(message=f"Error while sending SMS. Not gateways left.", error=True)

        # send a success message
        return self.handel_response(message=settings.sms_success_message, error=False)

    def handel_response(self, message: str, error: bool = False):
        logger.debug(f"Sending Response: message='{message}', error={error}, encoding='{settings.sms_out_encoding}'")
        try:
            message_raw = message.encode(settings.sms_out_encoding)
            self.request.sendall(message_raw)
        except Exception as e:
            logger.error(f"Error while sending response message.\n{e}")


class SMSServer(socketserver.TCPServer):
    def __init__(self):
        logger.debug("Initializing SMSServer ...")

        try:
            # noinspection PyTypeChecker
            super().__init__((settings.server_host, settings.server_port), SMSServerHandler)
        except Exception as e:
            logger.error(f"Error while starting SMSServer: {e}")
            sys.exit(1)

        logger.debug("Initializing gateways ...")
        self._next_sms_gateway_index: int | None = None
        self._gateways: list[BaseGateway] = []
        for gateway_config_name, gateway_config in settings.gateway_configs.items():
            gateway = gateway_config.gateway_cls(server=self, name=gateway_config_name, config=gateway_config)
            self._gateways.append(gateway)

        if len(self._gateways) == 0:
            raise RuntimeError("No gateways configured.")

        logger.debug("Initializing SMSServer ... done")

    @property
    def gateways(self) -> tuple[BaseGateway, ...]:
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

    def serve(self):
        logger.info(f"SMS Server started host='{settings.server_host}', port={settings.server_port}")
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            logger.debug("Stopping SMSServer ...")
            self.shutdown()
            self.server_close()
            logger.info("SMSServer stopped")
