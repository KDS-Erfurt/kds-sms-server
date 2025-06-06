from enum import Enum
from ipaddress import IPv4Address, IPv4Network

from pydantic import Field

from sms_broker.server.config import BaseServerConfig


class TcpServerConfig(BaseServerConfig):
    class Type(str, Enum):
        TCP = "tcp"

    type: Type = Field(default=..., title="Type", description="Type of the server.")
    host: IPv4Address = Field(default=..., title="TCP Server Host", description="TCP Server Host to bind to.")
    port: int = Field(default=..., title="TCP Server Port", ge=0, le=65535, description="TCP Server Port to bind to.")
    allowed_networks: list[IPv4Network] = Field(default_factory=lambda: [IPv4Network("0.0.0.0/0")], title="TCP Server Allowed Clients Networks",
                                                description="List of allowed client networks.")
    in_encoding: str = Field(default="auto", title="TCP Server input encoding", description="Encoding of incoming data.")
    out_encoding: str = Field(default="utf-8", title="TCP Server output encoding", description="Encoding of outgoing data.")
    data_max_size: int = Field(default=2048, title="Max Data Size", description="Max Data Size for SMS.", ge=1024)
    success_result: str | None = Field(default=None, title="TCP Server success message",
                                       description="Message to send on success. If set to None, the original message will be sent back to the client.")
    error_result: str | None = Field(default=None, title="TCP Server error message",
                                     description="Message to send on error. If set to None, the original message will be sent back to the client.")
