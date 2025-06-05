from pathlib import Path
from typing import Union

from pydantic import Field
from pydantic_settings import BaseSettings
from wiederverwendbar.sqlalchemy import SqlalchemySettings

from wiederverwendbar.logger import LoggerSettings
from wiederverwendbar.pydantic import FileConfig

from kds_sms_server.server.file.config import FileServerConfig
from kds_sms_server.server.tcp.config import TcpServerConfig
from kds_sms_server.server.api.config import ApiServerConfig
from kds_sms_server.server.ui.config import UiServerConfig
from kds_sms_server.gateways.teltonika.config import TeltonikaGatewayConfig
from kds_sms_server.gateways.vonage.config import VonageGatewayConfig

AVAILABLE_SERVER_CONFIGS = Union[
    FileServerConfig,
    TcpServerConfig,
    ApiServerConfig,
    UiServerConfig
]
AVAILABLE_GATEWAY_CONFIGS = Union[
    TeltonikaGatewayConfig,
    VonageGatewayConfig
]


class Settings(FileConfig, BaseSettings, SqlalchemySettings):
    model_config = {
        "env_prefix": "KDS_SMS_SERVER_",
        "case_sensitive": False
    }

    class ListenerSettings(LoggerSettings):
        # sms
        sms_number_allowed_chars: str = Field(default="+*#()0123456789 ", title="Allowed Number Characters", description="Allowed Number Characters.")
        sms_number_replace_chars: str = Field(default="() ", title="Replace Number Characters", description="Replace Number Characters.")
        sms_replace_zero_numbers: str | None = Field(default=None, title="Replace Zero Numbers",
                                                     description="Replace all zero numbers with this string.")
        sms_number_max_size: int = Field(default=20, title="Max Number Size", description="Max Number Size for SMS.", ge=1, le=50)
        sms_message_max_size: int = Field(default=1600, title="Max Message Size", description="Max Message Size for SMS.", ge=1, le=1600)
        sms_logging: bool = Field(default=False, title="SMS Logging", description="Enable SMS Logging content logging.")

        # server
        server: dict[str, AVAILABLE_SERVER_CONFIGS] = Field(default_factory=dict, title="Server",
                                                            description="Server configuration.")

    # listener
    listener: ListenerSettings = Field(default_factory=ListenerSettings, title="Listener Settings", description="Listener settings.")

    class WorkerSettings(LoggerSettings):
        # worker
        count: int | None = Field(default=None, title="Background Worker Count",
                                  description="Number of background workers. If None, worker count will be calculated by cpu count but max 4.")

        # sms
        sms_handle_interval: int = Field(default=1, title="SMS handle Interval", description="Interval for handling SMS in seconds.")
        sms_cleanup_max_age: int | None = Field(default=60 * 60 * 24 * 30, title="DB SMS cleanup max age",
                                                description="Time after cleanup SMS from DB in seconds. If None, no cleanup will be performed.")
        sms_cleanup_interval: int = Field(default=60, title="DB SMS cleanup interval", description="Interval for cleanup SMS from DB in seconds.")

        # gateways
        gateways: dict[str, AVAILABLE_GATEWAY_CONFIGS] = Field(default_factory=dict, title="Gateways",
                                                               description="Gateways configuration.")

    # worker
    worker: WorkerSettings = Field(default_factory=WorkerSettings, title="Worker Settings", description="Worker settings.")


# noinspection PyArgumentList
settings = Settings(file_path=Path("settings.json"), file_must_exist="yes_print")
