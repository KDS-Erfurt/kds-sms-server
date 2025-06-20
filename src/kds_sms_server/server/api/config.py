from enum import Enum
from ipaddress import IPv4Address, IPv4Network

from pydantic import Field
from kds_sms_server.server.config import BaseServerConfig


class ApiServerConfig(BaseServerConfig):
    class Type(str, Enum):
        API = "api"

    type: Type = Field(default=..., title="Type", description="Type of the server.")
    host: IPv4Address = Field(default=..., title="API Server Host", description="API Server Host to bind to.")
    port: int = Field(default=..., title="API Server Port", ge=0, le=65535, description="API Server Port to bind to.")
    docs_web_path: str | None = Field(default=None, title="API Server Docs Web Path", description="API Server Docs Web Path.")
    redoc_web_path: str | None = Field(default=None, title="API Server Redoc Web Path", description="API Server Redoc Web Path.")
    allowed_networks: list[IPv4Network] = Field(default_factory=lambda: [IPv4Network("0.0.0.0/0")], title="API Server Allowed Clients Networks",
                                                description="List of allowed client networks.")
    authentication_enabled: bool = Field(default=False, title="API Server Authentication Enabled", description="Enable API Server Authentication.")
    authentication_accounts: dict[str, str] = Field(default_factory=dict, title="API Server Authentication Accounts", description="API Server Authentication Accounts.")
    success_result: str | None = Field(default=None, title="API Server success message",
                                       description="Message to send on success. If set to None, the original message will be sent back to the client.")
    error_result: str | None = Field(default=None, title="API Server error message",
                                     description="Message to send on error. If set to None, the original message will be sent back to the client.")
