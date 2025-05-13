import logging
import socketserver
import sys
import threading
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Any

import chardet

from kds_sms_server.server.base import BaseServer
from kds_sms_server.settings import settings

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SMSServer

logger = logging.getLogger(__name__)


class TCPServerHandler(socketserver.BaseRequestHandler):
    server: "TCPServer"

    def handle(self) -> None:
        # get client ip and port
        client_ip, client_port = self.client_address
        try:
            client_ip = IPv4Address(client_ip)
        except Exception as e:
            return self.server.log_and_handle_response(caller=self, message=f"Error while parsing client IP address.", level="error", error=e)

        _ = self.server.handle_request(caller=self, client_ip=client_ip, client_port=client_port)
        return None


class TCPServer(BaseServer, socketserver.TCPServer, threading.Thread):
    def __init__(self, sms_server: "SMSServer"):
        try:
            BaseServer.__init__(self,
                                sms_server=sms_server,
                                host=settings.tcp_server_host,
                                port=settings.tcp_server_port,
                                debug=settings.debug,
                                allowed_networks=settings.tcp_server_allowed_networks,
                                success_message=settings.tcp_server_success_message)
            # noinspection PyTypeChecker
            socketserver.TCPServer.__init__(self, (self.host, self.port), TCPServerHandler)
            threading.Thread.__init__(self, daemon=True)
        except Exception as e:
            logger.error(f"Error while starting {self}: {e}")
            sys.exit(1)
        self.done()

    def start(self):
        threading.Thread.start(self)

    def enter(self):
        self.serve_forever()

    def exit(self):
        self.shutdown()
        self.server_close()

    def _handle_sms_body(self, caller: TCPServerHandler, **kwargs) -> tuple[str, str] | None:
        # get data
        try:
            data = caller.request.recv(settings.sms_data_max_size).strip()
            logger.debug(f"{self} - data={data}")
        except Exception as e:
            return self.log_and_handle_response(caller=self, message=f"Error while receiving data.", level="error", error=e)

        # detect encoding
        try:
            encoding = settings.tcp_server_in_encoding
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

    def _handle_response(self, caller: TCPServerHandler, message: str) -> Any:
        message_raw = message.encode(settings.tcp_server_out_encoding)
        caller.request.sendall(message_raw)
