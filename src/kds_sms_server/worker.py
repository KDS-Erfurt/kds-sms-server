import time

from wiederverwendbar.logger import LoggerSingleton
from wiederverwendbar.task_manger import TaskManager, Task, EverySeconds

from kds_sms_server.console import console
from kds_sms_server.settings import settings

# noinspection PyArgumentList
logger = LoggerSingleton(name=__name__,
                         settings=settings.log_server,
                         ignored_loggers_like=["sqlalchemy", "pymysql"],
                         init=True)


class SmsWorker(TaskManager):
    def __init__(self):
        logger.info(f"Initializing SMS-Worker ...")
        super().__init__(worker_count=settings.sms_background_worker_count, daemon=True, logger=logger)

        # create tasks
        logger.info("Initializing tasks ...")
        Task(name="Handle SMS", manager=self, trigger=EverySeconds(settings.sms_handle_interval), payload=self.handle_sms)
        Task(name="Cleanup SMS", manager=self, trigger=EverySeconds(settings.sms_cleanup_interval), payload=self.cleanup_sms)
        logger.debug("Initializing tasks ... done")

        logger.debug(f"Initializing SMS-Worker ... done")

        logger.info(f"Starting SMS-Worker ...")

        # starting task manager workers
        self.start()

        logger.debug(f"Starting SMS-Worker ... done")

    # @property
    # def gateways(self) -> tuple[BaseGateway, ...]:
    #     with self.lock:
    #         if self._next_sms_gateway_index is None:
    #             self._next_sms_gateway_index = 0
    #         else:
    #             self._next_sms_gateway_index += 1
    #         if self._next_sms_gateway_index >= len(self._gateways):
    #             self._next_sms_gateway_index = 0
    #
    #         gateways = []
    #         for gateway in self._gateways[self._next_sms_gateway_index:]:
    #             gateways.append(gateway)
    #         if self._next_sms_gateway_index > 0:
    #             for gateway in self._gateways[:self._next_sms_gateway_index]:
    #                 gateways.append(gateway)
    #     return tuple(gateways)

    # def handle_sms(self, server: TcpServer | ApiServer, number: str, message: str) -> tuple[bool, str]:
    #     logger.debug(f"{server} - Processing SMS ...")
    #
    #     # check number
    #     if len(number) > self.settings.sms_number_max_size:
    #         return False, f"Received number is too long. Max size is '{self.settings.sms_number_max_size}'.\nnumber_size={len(number)}"
    #     _number = ""
    #     for char in number:
    #         if char not in list(self.settings.sms_number_allowed_chars):
    #             return False, f"Received number contains invalid characters. Allowed characters are '{self.settings.sms_number_allowed_chars}'.\nnumber='{number}'"
    #         if char in list(self.settings.sms_number_replace_chars):
    #             char = ""
    #         _number += char
    #     number = _number
    #     del _number
    #
    #     # replace zoro number
    #     if self.settings.sms_replace_zero_numbers is not None:
    #         if number.startswith("0"):
    #             number = self.settings.sms_replace_zero_numbers + number[1:]
    #
    #     # check a message
    #     if len(message) > self.settings.sms_message_max_size:
    #         return False, f"Received message is too long. Max size is '{self.settings.sms_message_max_size}'.\nmessage_size={len(message)}"
    #
    #     # log sms received successfully
    #     if self.settings.sms_logging:
    #         logger.debug(f"{server} - Processing SMS ... done\nnumber={number}\nmessage='{message}'")
    #     else:
    #         logger.debug(f"{server} - Processing SMS ... done\nnumber={number}")
    #
    #     # send sms to gateways
    #     for gateway in self.gateways:
    #         # check if gateway is available
    #         if not gateway.check():
    #             continue
    #
    #         # send it with gateway
    #         result = gateway.send_sms(number, message)
    #         if result:
    #             return True, ""
    #     return False, f"Error while sending SMS. Not gateways left."

    def handle_sms(self):
        logger.debug("Handle SMS ...")

    def cleanup_sms(self):
        logger.debug("Handle SMS ...")
