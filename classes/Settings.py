import json
import sys

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
    logging_file: str = "sms.log"
    logging_file_rotate_when: str = "midnight"  # D: Day, H: Hour, M: Minute, S: Second, W0-W6: Weekday (0=Monday), midnight
    logging_file_rotate_interval: int = 1
    logging_file_rotate_backup_count: int = 30

    # server settings
    server_host: str = "0.0.0.0"
    server_port: int = 3456

    # sms settings
    sms_data_max_size: int = 2048
    sms_encoding: str = "utf-8"
    sms_number_max_size: int = 20
    sms_message_max_size: int = 160
    sms_success_message: str = "SMS mit Message-Reference 999 ok"
    sms_logging: bool = True

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
            json.dump(SETTINGS.dict(), f, indent=4)
    else:
        CONSOLE.print(f"[red]ERROR[/red]:\t  {STATIC.settings_file_path} does not exist.")
        sys.exit(1)
