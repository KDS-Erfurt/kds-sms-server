import logging
import socketserver
import sys
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Any

import chardet

from kds_sms_server.server.server import BaseServer

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SmsServer
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
            return self.server.log_and_handle_response(caller=self, message=f"Error while parsing client IP address.", level="error", error=e)

        self.server.handle_request(caller=self, client_ip=client_ip, client_port=client_port)
        return None


class TcpServer(BaseServer, socketserver.TCPServer):
    def __init__(self, server: "SmsServer", name: str, config: "TcpServerConfig"):
        BaseServer.__init__(self, server=server, name=name, config=config)

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

    def enter(self):
        self.stated_done()
        self.serve_forever()

    def exit(self):
        self.shutdown()
        self.server_close()

    def handle_request(self, caller: Any, client_ip: IPv4Address, client_port: int, **kwargs) -> Any:
        # check if client ip is allowed
        allowed = False
        for network in self.config.allowed_networks:
            if client_ip in network:
                allowed = True
                break
        if not allowed:
            return self.log_and_handle_response(caller=self, message=f"Client IP address '{client_ip}' is not allowed.", level="warning", error=True)
        return super().handle_request(caller=caller, client_ip=client_ip, client_port=client_port, **kwargs)

    def handle_sms_data(self, caller: TcpServerHandler, **kwargs) -> tuple[str, str] | None:
        # get data
        try:
            data = caller.request.recv(self.server.settings.sms_data_max_size).strip()
            logger.debug(f"{self} - data={data}")
        except Exception as e:
            return self.log_and_handle_response(caller=self, message=f"Error while receiving data.", level="error", error=e)

        # detect encoding
        try:
            encoding = self.config.in_encoding
            if encoding == "auto":
                encoding = chardet.detect(data)['encoding']
            logger.debug(f"{self} - encoding={encoding}")
        except Exception as e:
            return self.log_and_handle_response(caller=self, message=f"Error while detecting encoding.", level="error", error=e)

        # decode message
        try:
            data_str = data.decode(encoding)
            logger.debug(f"{self} - data_str='{data_str}'")

            # split message
            if "\r\n" not in data_str:
                return self.log_and_handle_response(caller=self, message=f"Received data is not valid.", level="error", error=True)
            number, message = data_str.split("\r\n")
            return number, message
        except Exception as e:
            return self.log_and_handle_response(caller=self, message=f"Error while decoding data.", level="error", error=e)

    def success_handler(self, caller: TcpServerHandler, sms_id: int, message: str) -> Any:
        if self.config.success_message is not None:
            message = self.config.success_message
        message_raw = message.encode(self.config.out_encoding)
        caller.request.sendall(message_raw)

    def error_handler(self, caller: TcpServerHandler, sms_id: int | None, message: str) -> Any:
        if self.config.error_message is not None:
            message = self.config.error_message
        message_raw = message.encode(self.config.out_encoding)
        caller.request.sendall(message_raw)
