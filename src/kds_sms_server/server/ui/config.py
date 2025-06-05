from enum import Enum
from ipaddress import IPv4Address, IPv4Network

from pydantic import Field
from kds_sms_server.server.config import BaseServerConfig


class UiServerConfig(BaseServerConfig):
    class Type(str, Enum):
        UI = "ui"

    type: Type = Field(default=..., title="Type", description="Type of the server.")
    host: IPv4Address = Field(default=..., title="UI Server Host", description="UI Server Host to bind to.")
    port: int = Field(default=..., title="UI Server Port", ge=0, le=65535, description="UI Server Port to bind to.")
    allowed_networks: list[IPv4Network] = Field(default_factory=lambda: [IPv4Network("0.0.0.0/0")], title="UI Server Allowed Clients Networks",
                                                description="List of allowed client networks.")
    authentication_enabled: bool = Field(default=False, title="UI Server Authentication Enabled", description="Enable UI Server Authentication.")
    authentication_accounts: dict[str, str] = Field(default_factory=dict, title="UI Server Authentication Accounts", description="UI Server Authentication Accounts.")
    success_result: str | None = Field(default=None, title="UI Server success message",
                                       description="Message to send on success. If set to None, the original message will be sent back to the client.")
    error_result: str | None = Field(default=None, title="UI Server error message",
                                     description="Message to send on error. If set to None, the original message will be sent back to the client.")
