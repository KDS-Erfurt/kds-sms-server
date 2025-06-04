from ipaddress import IPv4Address, IPv4Network
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings
from wiederverwendbar.uvicorn import UvicornServerSettings

from kds_sms_server.gateways import AVAILABLE_GATEWAY_CONFIGS
from wiederverwendbar.logger import LoggerSettings
from wiederverwendbar.pydantic import FileConfig


class Settings(FileConfig, BaseSettings, LoggerSettings, UvicornServerSettings):
    model_config = {
        "env_prefix": "KDS_SMS_SERVER_",
        "case_sensitive": False
    }

    # debug
    debug: bool = Field(default=False, title="Debug", description="Enable Debug.")

    # log
    log_console_format: str = Field(default="%(message)s",
                                    title="Console Log Format",
                                    description="The log format for the console")

    # tcp server settings
    tcp_server_enabled: bool = Field(default=False, title="TCP Server Enabled", description="Enable TCP Server.")
    tcp_server_host: IPv4Address | str = Field(default=IPv4Address("127.0.0.1"), title="TCP Server Host", description="TCP Server Host to bind to.")
    tcp_server_port: int = Field(default=3456, title="TCP Server Port", ge=0, le=65535, description="TCP Server Port to bind to.")
    tcp_server_allowed_networks: list[IPv4Network] = Field(default=[IPv4Network("0.0.0.0/0")], title="TCP Server Allowed Clients Networks",
                                                           description="List of allowed client networks.")
    tcp_server_in_encoding: str = Field(default="auto", title="TCP Server input encoding", description="Encoding of incoming data.")
    tcp_server_out_encoding: str = Field(default="utf-8", title="TCP Server output encoding", description="Encoding of outgoing data.")
    tcp_server_success_message: str = Field(default="OK", title="TCP Server success message", description="Message to send on success.")

    # api server settings
    api_server_enabled: bool = Field(default=False, title="API Server Enabled", description="Enable API Server.")
    api_server_host: IPv4Address | str = Field(default=IPv4Address("127.0.0.1"), title="API Server Host", description="API Server Host to bind to.")
    api_server_port: int = Field(default=8000, title="API Server Port", ge=0, le=65535, description="API Server Port to bind to.")
    api_server_docs_web_path: str | None = Field(default=None, title="API Server Docs Web Path", description="API Server Docs Web Path.")
    api_server_redoc_web_path: str | None = Field(default=None, title="API Server Redoc Web Path", description="API Server Redoc Web Path.")
    api_server_allowed_networks: list[IPv4Network] = Field(default=[IPv4Network("0.0.0.0/0")], title="API Server Allowed Clients Networks",
                                                           description="List of allowed client networks.")
    api_server_authentication_enabled: bool = Field(default=False, title="API Server Authentication Enabled", description="Enable API Server Authentication.")
    api_server_authentication_accounts: dict[str, str] = Field(default={}, title="API Server Authentication Accounts", description="API Server Authentication Accounts.")
    api_server_success_message: str = Field(default="OK", title="API Server success message", description="Message to send on success.")

    # sms settings
    sms_number_allowed_chars: str = Field(default="+*#()0123456789 ", title="Allowed Number Characters", description="Allowed Number Characters.")
    sms_number_replace_chars: str = Field(default="() ", title="Replace Number Characters", description="Replace Number Characters.")
    sms_replace_zero_numbers: str | None = Field(default=None, title="Replace Zero Numbers", description="Replace all zero numbers with this string.")
    sms_data_max_size: int = Field(default=2048, title="Max Data Size", description="Max Data Size for SMS.")
    sms_number_max_size: int = Field(default=20, title="Max Number Size", description="Max Number Size for SMS.")
    sms_message_max_size: int = Field(default=1600, title="Max Message Size", description="Max Message Size for SMS.")
    sms_logging: bool = Field(default=False, title="SMS Logging", description="Enable SMS Logging content logging.")

    # gateway settings
    gateways: dict[str, AVAILABLE_GATEWAY_CONFIGS] = Field(default_factory=dict, title="Gateways", description="Gateways configuration.")


# noinspection PyArgumentList
settings = Settings(file_path=Path("settings.json"))
