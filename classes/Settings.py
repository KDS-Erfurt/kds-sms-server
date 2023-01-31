import json
import sys
from pathlib import Path

from pydantic import BaseModel

from classes.Console import CONSOLE
from classes.Static import STATIC


class Settings(BaseModel):
    class ModemConfig(BaseModel):
        name: str
        ip: str
        port: int = 80
        username: str = ""
        password: str = ""
        timeout: int = 5
        check_timeout: float = 0.5
        check_retries: int = 3
        snmp_version: int = 2
        snmp_community: str = "public"
        snmp_timeout: int = 5

    logging: bool = True
    logging_level: str = "INFO"
    logging_file: Path = Path("C:/KDS/sms_server/sms_server.log")
    logging_file_rotate_when: str = "midnight"  # D: Day, H: Hour, M: Minute, S: Second, W0-W6: Weekday (0=Monday), midnight
    logging_file_rotate_interval: int = 1
    logging_file_rotate_backup_count: int = 30
    logging_check: bool = True

    # server settings
    server_host: str = "0.0.0.0"
    server_port: int = 3456

    # metric server settings
    metric_server_host: str = "0.0.0.0"
    metric_server_port: int = 8000
    metric_logging: bool = True
    metric_docs: bool = True
    metric_test_sms_receiver: str = ""  # "015126695526"

    # sms settings
    sms_data_max_size: int = 2048
    sms_in_encoding: str = "auto"
    sms_out_encoding: str = "utf-8"
    sms_number_max_size: int = 20
    sms_message_max_size: int = 1600
    sms_success_message: str = "SMS mit Message-Reference 999 ok"
    sms_logging: bool = False

    # modem settings
    modem_configs: list[ModemConfig] = [
        ModemConfig(name="SampleConfig", ip="1.2.3.4")
    ]
    modem_disable_check: bool = False


if STATIC.settings_file_path.exists():
    try:
        SETTINGS = Settings.parse_file(STATIC.settings_file_path)
    except json.JSONDecodeError as e:
        CONSOLE.print(f"[red]ERROR[/red]:\t  {STATIC.settings_file_path} is not a valid JSON file.")
        CONSOLE.print(f"[red]ERROR[/red]:\t  {e}")
        sys.exit(1)
else:
    if STATIC.create_settings_file_if_not_exists:
        SETTINGS = Settings()
        with open(STATIC.settings_file_path, "w") as f:
            json.dump(json.loads(SETTINGS.json()), f, indent=4)
    else:
        CONSOLE.print(f"[red]ERROR[/red]:\t  {STATIC.settings_file_path} does not exist.")
        sys.exit(1)
