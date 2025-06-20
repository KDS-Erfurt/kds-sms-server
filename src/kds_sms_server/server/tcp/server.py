import logging
import socketserver
import sys
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Any

import chardet

from kds_sms_server.server.server import BaseServer

if TYPE_CHECKING:
    from kds_sms_server.server.tcp.config import TcpServerConfig

logger = logging.getLogger(__name__)


class TcpServerHandler(socketserver.BaseRequestHandler):
    server: "TcpServer"

    def handle(self) -> None:
        # get client ip and port
        client_ip, client_port = self.client_address
        try:
            client_ip = IPv4Address(client_ip)
        except Exception as e:
            return self.server.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while parsing client IP address.")

        self.server.handle_request(caller=self, client_ip=client_ip, client_port=client_port)
        return None


class TcpServer(BaseServer, socketserver.TCPServer):
    __str_columns__ = ["name",
                       ("debug", "config_debug"),
                       ("host", "config_host"),
                       ("port", "config_port"),
                       ("allowed_networks", "config_allowed_networks")]

    def __init__(self, name: str, config: "TcpServerConfig"):
        BaseServer.__init__(self, name=name, config=config)

        try:
            # noinspection PyTypeChecker
            socketserver.TCPServer.__init__(self, (str(self.config.host), self.config.port), TcpServerHandler)
        except Exception as e:
            logger.error(f"Error while initializing {self}: {e}")
            sys.exit(1)

        self.init_done()

    @property
    def config(self) -> "TcpServerConfig":
        return super().config

    @property
    def config_host(self) -> str:
        return str(self.config.host)

    @property
    def config_port(self) -> int:
        return self.config.port

    @property
    def config_allowed_networks(self) -> list[str]:
        return [str(allowed_network) for allowed_network in self.config.allowed_networks]

    def enter(self):
        self.stated_done()
        self.serve_forever()

    def exit(self):
        self.shutdown()
        self.server_close()

    # noinspection DuplicatedCode
    def handle_request(self, caller: Any, **kwargs) -> Any | None:
        # check if client ip is allowed
        allowed = False
        for network in self.config.allowed_networks:
            if kwargs["client_ip"] in network:
                allowed = True
                break
        if not allowed:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=False, sms_id=None, result=f"Client IP address '{kwargs['client_ip']}' is not allowed.")

        logger.debug(f"{self} - Accept message:\nclient='{kwargs['client_ip']}'\nport={kwargs['client_ip']}")

        return super().handle_request(caller=caller, **kwargs)

    def handle_sms_data(self, caller: TcpServerHandler, **kwargs) -> tuple[str, str] | None:
        # get data
        try:
            data = caller.request.recv(self.config.data_max_size).strip()
            logger.debug(f"{self} - data={data}")
        except Exception as e:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while receiving data.")

        # detect encoding
        try:
            encoding = self.config.in_encoding
            if encoding == "auto":
                encoding = chardet.detect(data)['encoding']
            logger.debug(f"{self} - encoding={encoding}")
        except Exception as e:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while detecting encoding.")

        # decode message
        try:
            data_str = data.decode(encoding)
            logger.debug(f"{self} - data_str='{data_str}'")

            # split message
            if "\r\n" not in data_str:
                return self.handle_response(caller=self, log_level=logging.ERROR, success=False, sms_id=None, result=f"Received data is not valid.")
            number, message = data_str.split("\r\n")
            return number, message
        except Exception as e:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while decoding data.")

    def success_handler(self, caller: TcpServerHandler, sms_id: int, result: str, **kwargs) -> Any:
        if self.config.success_result is not None:
            result = self.config.success_result
        result_raw = result.encode(self.config.out_encoding)
        caller.request.sendall(result_raw)

    def error_handler(self, caller: TcpServerHandler, sms_id: int | None, result: str, **kwargs) -> Any:
        if self.config.error_result is not None:
            result = self.config.error_result
        result_raw = result.encode(self.config.out_encoding)
        caller.request.sendall(result_raw)
