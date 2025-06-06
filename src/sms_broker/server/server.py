import logging
from abc import abstractmethod
from datetime import datetime
from threading import Thread
from typing import Any, TYPE_CHECKING, Union

from sms_broker.base import Base
from sms_broker.db import Sms, SmsStatus
from sms_broker.settings import settings

if TYPE_CHECKING:
    from sms_broker.server.config import BaseServerConfig

logger = logging.getLogger(__name__)


class BaseServer(Base, Thread):
    __str_columns__ = ["name",
                       ("debug", "config_host")]

    def __init__(self, name: str, config: "BaseServerConfig"):
        self._is_started = False
        Base.__init__(self, name=name, config=config)
        Thread.__init__(self, name=name, daemon=True)

    @property
    def is_started(self) -> bool:
        return self._is_started

    @property
    def config(self) -> Union["BaseServerConfig", Any]:
        return super().config

    @property
    def config_debug(self) -> bool:
        return self.config.debug

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

    def handle_request(self, caller: Any, **kwargs) -> Any | None:
        logger.debug(f"{self} - Progressing SMS data ...")
        try:
            number, message = self.handle_sms_data(caller=caller, **kwargs)
        except Exception as e:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while processing SMS body.")
        logger.debug(f"{self} - Progressing SMS data ... done")

        logger.debug(f"Validating SMS ...")

        # check number
        if len(number) > settings.listener.sms_number_max_size:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=False, sms_id=None, result=f"Received number is too long. "
                                                                                                                 f"Max size is '{settings.listener.sms_number_max_size}'.\n"
                                                                                                                 f"number_size={len(number)}")
        _number = ""
        for char in number:
            if char not in list(settings.listener.sms_number_allowed_chars):
                return self.handle_response(caller=self, log_level=logging.ERROR, success=False, sms_id=None, result=f"Received number contains invalid characters. "
                                                                                                                     f"Allowed characters are '{settings.listener.sms_number_allowed_chars}'.\n"
                                                                                                                     f"number='{number}'")
            if char in list(settings.listener.sms_number_replace_chars):
                char = ""
            _number += char
        number = _number
        del _number

        # replace zero number
        if settings.listener.sms_replace_zero_numbers is not None:
            if number.startswith("0"):
                number = settings.listener.sms_replace_zero_numbers + number[1:]

        # check a message
        if len(message) > settings.listener.sms_message_max_size:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=False, sms_id=None, result=f"Received message is too long. "
                                                                                                                 f"Max size is '{settings.listener.sms_message_max_size}'.\n"
                                                                                                                 f"message_size={len(message)}")

        logger.debug(f"Validating SMS ... done")

        # log sms
        if settings.listener.sms_logging:
            logger.debug(f"SMS:\nnumber={number}\nmessage='{message}'")

        # queue sms
        logger.info(f"Queuing SMS ...")
        try:
            sms = Sms(status=SmsStatus.QUEUED,
                      received_by=self.name,
                      received_datetime=datetime.now(),
                      number=number,
                      message=message)
            sms.save()
            success = True
            sms_id = sms.id
            result = f"SMS with id={sms_id} queued successfully."
        except Exception as e:
            success = False
            sms_id = None
            result = f"Error while queuing SMS."
            if self.config.debug:
                result += f"\nException: {e}"
        logger.log(logging.DEBUG if success else logging.ERROR, f"Queuing SMS ... {'done' if success else 'failed'} --> {result}")

        # send response
        if success:
            log_level = logging.DEBUG
        else:
            log_level = logging.ERROR
        return self.handle_response(caller=caller, log_level=log_level, success=success, sms_id=sms_id, result=result, **kwargs)

    def handle_response(self, caller: Any, log_level: int, success: bool | Exception, sms_id: int | None, result: str, **kwargs) -> Any | None:
        if result.endswith(".") or result.endswith(":"):
            result = result[:-1]
        e = ""
        if isinstance(success, Exception):
            e = str(success)
            success = False
        if not success and self.config.debug:
            result = f"{result}:\n{e}"
        else:
            result = f"{result}."
        if not success:
            log_msg = f"{self} - {result}:\n{e}"
        else:
            log_msg = f"{self} - {result}."
        logger.log(log_level, log_msg)

        logger.debug(f"{self} - Sending Response.\nsuccess='{success}'\nsms_id={sms_id}\nresult={result}")
        try:
            self.increase_sms_count()
            if not success:
                self.increase_sms_error_count()
                return self.error_handler(caller=caller, sms_id=sms_id, result=result, **kwargs)
            return self.success_handler(caller=caller, sms_id=sms_id, result=result, **kwargs)
        except Exception as e:
            logger.error(f"{self} - Error while sending response message.\n{e}")
        return None

    @abstractmethod
    def handle_sms_data(self, caller: Any, **kwargs) -> tuple[str, str]:
        ...

    @abstractmethod
    def success_handler(self, caller: Any, sms_id: int, result: str, **kwargs) -> Any:
        ...

    @abstractmethod
    def error_handler(self, caller: Any, sms_id: int | None, result: str, **kwargs) -> Any:
        ...
