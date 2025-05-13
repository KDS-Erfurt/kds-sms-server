from pathlib import Path

from pydantic_settings import BaseSettings
from kds_sms_server.gateways import AVAILABLE_CONFIGS
from wiederverwendbar.logger import LoggerSettings
from wiederverwendbar.pydantic import FileConfig


class Settings(FileConfig, BaseSettings, LoggerSettings):
    model_config = {
        "env_prefix": "KDS_SMS_SERVER_",
        "case_sensitive": False
    }

    # server settings
    server_host: str = "0.0.0.0"
    server_port: int = 3456
    server_log_alive_check: bool = True

    # sms settings
    sms_replace_zero_numbers: str | None = "+49"
    sms_data_max_size: int = 2048
    sms_in_encoding: str = "auto"
    sms_out_encoding: str = "utf-8"
    sms_number_max_size: int = 20
    sms_message_max_size: int = 1600
    sms_success_message: str = "SMS mit Message-Reference 999 ok"
    sms_logging: bool = False

    # gateway settings
    gateway_configs: dict[str, AVAILABLE_CONFIGS] = {}
    # modem_disable_check: bool = False ToDo: move to config


settings = Settings(file_path=Path("settings.json"))
