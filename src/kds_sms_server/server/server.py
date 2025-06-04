import logging
from abc import abstractmethod
from datetime import datetime
from ipaddress import IPv4Address
from threading import Thread
from typing import Any, TYPE_CHECKING, Literal, Union

from kds_sms_server.base import Base
from kds_sms_server.db import Sms, SmsStatus

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SmsServer
    from kds_sms_server.server.config import BaseServerConfig

logger = logging.getLogger(__name__)


class BaseServer(Base, Thread):
    def __init__(self, server: "SmsServer", name: str, config: "BaseServerConfig"):
        self._is_started = False
        Base.__init__(self, server=server, name=name, config=config)
        Thread.__init__(self, name=name, daemon=True)

    @property
    def is_started(self) -> bool:
        return self._is_started

    @property
    def config(self) -> Union["BaseServerConfig", Any]:
        return super().config

    def run(self):
        logger.info(f"Starting {self} ...")
        try:
            self.enter()
        except KeyboardInterrupt:
            logger.info(f"Stopping {self} ...")
            self.exit()
            logger.debug(f"Stopping {self} ... done")

    @abstractmethod
    def enter(self):
        ...

    def stated_done(self):
        logger.debug(f"Starting {self} ... done.")
        self._is_started = True

    @abstractmethod
    def exit(self):
        ...

    def log_and_handle_response(self, caller: Any, message: str, level: Literal["debug", "info", "warning", "error"] = "debug", error: bool | Exception = False) -> None:
        if message.endswith(".") or message.endswith(":"):
            message = message[:-1]
        e = ""
        if error and isinstance(error, Exception):
            e = str(error)
        if error and self.config.debug:
            response_msg = f"{message}:\n{e}"
        else:
            response_msg = f"{message}."
        if error:
            log_msg = f"{self} - {message}:\n{e}"
        else:
            log_msg = f"{self} - {message}."
        getattr(logger, level)(log_msg)
        self.handle_response(caller=caller, sms_id=None, message=response_msg, error=error)

    def handle_request(self, caller: Any, client_ip: IPv4Address, client_port: int, **kwargs) -> Any:
        logger.debug(f"{self} - Accept message:\nclient='{client_ip}'\nport={client_port}")

        logger.debug(f"{self} - Progressing SMS data ...")
        try:
            number, message = self.handle_sms_data(caller=caller, **kwargs)
        except Exception as e:
            logger.error(f"{self} - Error while processing SMS body:\n{e}")
            return None
        logger.debug(f"{self} - Progressing SMS data ... done")

        logger.debug(f"Validating SMS ...")

        # check number
        if len(number) > self.server.settings.sms_number_max_size:
            return False, f"Received number is too long. Max size is '{self.server.settings.sms_number_max_size}'.\nnumber_size={len(number)}"
        _number = ""
        for char in number:
            if char not in list(self.server.settings.sms_number_allowed_chars):
                return False, f"Received number contains invalid characters. Allowed characters are '{self.server.settings.sms_number_allowed_chars}'.\nnumber='{number}'"
            if char in list(self.server.settings.sms_number_replace_chars):
                char = ""
            _number += char
        number = _number
        del _number

        # replace zero number
        if self.server.settings.sms_replace_zero_numbers is not None:
            if number.startswith("0"):
                number = self.server.settings.sms_replace_zero_numbers + number[1:]

        # check a message
        if len(message) > self.server.settings.sms_message_max_size:
            return False, f"Received message is too long. Max size is '{self.server.settings.sms_message_max_size}'.\nmessage_size={len(message)}"

        logger.debug(f"Validating SMS ... done")

        # log sms
        if self.server.settings.sms_logging:
            logger.debug(f"SMS:\nnumber={number}\nmessage='{message}'")

        # queue sms
        result, sms_id, message = self.queue_sms(number=number, message=message)

        # send a success message
        return self.handle_response(caller=caller, sms_id=sms_id, message=message, error=not result)

    @abstractmethod
    def handle_sms_data(self, caller: Any, **kwargs) -> tuple[str, str]:
        ...

    def handle_response(self, caller: Any, sms_id: int | None, message: str, error: bool = False) -> Any:
        logger.debug(f"{self} - Sending Response.\nmessage='{message}'\nerror={error}\n")
        try:
            if error:
                return self.error_handler(caller=caller, sms_id=sms_id, message=message)
            return self.success_handler(caller=caller, sms_id=sms_id, message=message)
        except Exception as e:
            logger.error(f"{self} - Error while sending response message.\n{e}")
        return None

    @abstractmethod
    def success_handler(self, caller: Any, sms_id: int, message: str) -> Any:
        ...

    @abstractmethod
    def error_handler(self, caller: Any, sms_id: int | None, message: str) -> Any:
        ...

    def queue_sms(self, number: str, message: str) -> tuple[bool, int, str]:
        logger.info(f"Queuing SMS ...")

        try:
            sms = Sms(status=SmsStatus.QUEUED,
                      received_by=self.name,
                      received_datetime=datetime.now(),
                      send_datetime=None,
                      number=number,
                      message=message)
            sms.save()
            result = True
            sms_id = sms.id
            message = f"SMS with id={sms_id} queued successfully."
        except Exception as e:
            result = False
            sms_id = None
            message = f"Error while queuing SMS.\nException: {e}"

        logger.debug(f"Queuing SMS ... done")

        return result, sms_id, message
