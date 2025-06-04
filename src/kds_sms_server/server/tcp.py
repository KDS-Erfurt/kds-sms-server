import logging
import socketserver
import sys
import threading
from enum import Enum
from ipaddress import IPv4Address, IPv4Network
from typing import TYPE_CHECKING, Any

import chardet
from pydantic import Field

from kds_sms_server.server.base import BaseServer, BaseServerConfig

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SmsServer

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
    def __init__(self, server: "SmsServer", name: str, config: "BaseServerConfig"):
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

    def handle_sms_body(self, caller: TcpServerHandler, **kwargs) -> tuple[str, str] | None:
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

    def success_handler(self, caller: TcpServerHandler, message: str) -> Any:
        if self.config.success_message is not None:
            message = self.config.success_message
        message_raw = message.encode(self.config.out_encoding)
        caller.request.sendall(message_raw)

    def error_handler(self, caller: TcpServerHandler, message: str) -> Any:
        if self.config.error_message is not None:
            message = self.config.error_message
        message_raw = message.encode(self.config.out_encoding)
        caller.request.sendall(message_raw)


class TcpServerConfig(BaseServerConfig):
    _cls = TcpServer

    class Type(str, Enum):
        TCP = "tcp"

    type: Type = Field(default=..., title="Type", description="Type of the server.")
    host: IPv4Address = Field(default=..., title="TCP Server Host", description="TCP Server Host to bind to.")
    port: int = Field(default=..., title="TCP Server Port", ge=0, le=65535, description="TCP Server Port to bind to.")
    allowed_networks: list[IPv4Network] = Field(default_factory=lambda: [IPv4Network("0.0.0.0/0")], title="TCP Server Allowed Clients Networks",
                                                description="List of allowed client networks.")
    in_encoding: str = Field(default="auto", title="TCP Server input encoding", description="Encoding of incoming data.")
    out_encoding: str = Field(default="utf-8", title="TCP Server output encoding", description="Encoding of outgoing data.")
    success_message: str | None = Field(default="OK", title="TCP Server success message",
                                        description="Message to send on success. If set to None, the original message will be sent back to the client.")
    error_message: str | None = Field(default="ERROR", title="TCP Server error message",
                                      description="Message to send on error. If set to None, the original message will be sent back to the client.")
