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
    session_secret_key: str = Field(default=..., title="UI Server Session Secret Key", description="UI Server Session Secret Key.", min_length=64)
    session_cookie: str = Field(default="session", title="UI Server Session Cookie", description="UI Server Session Cookie.")
    session_max_age: int = Field(default=60 * 60 * 24 * 14, title="UI Server Session Max Age", description="UI Server Session Max Age.")
