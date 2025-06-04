from pydantic import Field
from enum import Enum

from kds_sms_server.gateways.config import BaseGatewayConfig


class TeltonikaGatewayConfig(BaseGatewayConfig):
    class Type(str, Enum):
        TELTONIKA = "teltonika"

    type: Type = Field(default=..., title="Type", description="Type of the gateway.")
    ip: str = Field(default=..., title="IP address", description="IP address of the gateway.")
    port: int = Field(default=80, title="Port", description="Port of the gateway.")
    username: str = Field(default="", title="Username", description="Username for authentication.")
    password: str = Field(default="", title="Password", description="Password for authentication.")
