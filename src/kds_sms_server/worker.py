import logging
import logging.handlers
import sys
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy import and_, or_
from wiederverwendbar.logger import LoggerSingleton, LoggingContext, remove_logger
from wiederverwendbar.task_manger import TaskManager, Task, EverySeconds

from kds_sms_server.db import Sms, SmsStatus
from kds_sms_server.settings import settings
from kds_sms_server.gateways.gateway import BaseGateway
from kds_sms_server.gateways.teltonika.gateway import TeltonikaGateway
from kds_sms_server.gateways.vonage.gateway import VonageGateway

IGNORED_LOGGERS_LIKE = ["sqlalchemy", "pymysql"]
# noinspection PyArgumentList
logger = LoggerSingleton(name=__name__,
                         settings=settings.worker,
                         ignored_loggers_like=IGNORED_LOGGERS_LIKE,
                         init=True)


class SmsWorker(TaskManager):
    class SmsLogHandler(logging.handlers.BufferingHandler):
        def __init__(self, buffer_target: Callable):
            super().__init__(capacity=10)
            self.buffer_target = buffer_target

        def flush(self):
            for record in self.buffer:
                self.buffer_target(self.format(record))
            super().flush()

    def __init__(self):
        logger.info(f"Initializing SMS-Worker ...")
        super().__init__(name="SMS-Worker", worker_count=settings.worker.count, daemon=True, logger=logger)

        # initialize gateway
        logger.info("Initializing gateways ...")
        self._next_sms_gateway_index: int | None = None
        self._gateways: list[BaseGateway] = []
        for gateway_config_name, gateway_config in settings.worker.gateways.items():
            if len(gateway_config_name) > 20:
                logger.error(f"Gateway name '{gateway_config_name}' is too long. Max size is 20 characters.")
                sys.exit(1)

            gateway_cls = None
            if gateway_config.type == "teltonika":
                gateway_cls = TeltonikaGateway
            elif gateway_config.type == "vonage":
                gateway_cls = VonageGateway

            if gateway_cls is None:
                logger.error(f"Unknown gateway type '{gateway_config.type}'.")
                sys.exit(1)

            gateway = gateway_cls(name=gateway_config_name, config=gateway_config)
            self._gateways.append(gateway)
        if len(self._gateways) == 0:
            logger.error(f"No gateways are configured. Please check your settings.")
            sys.exit(1)
        logger.debug("Initializing gateways ... done")

        # create tasks
        logger.info("Initializing tasks ...")
        Task(name="Handle SMS", manager=self, trigger=EverySeconds(settings.worker.sms_handle_interval), payload=self.handle_sms)
        Task(name="Cleanup SMS", manager=self, trigger=EverySeconds(settings.worker.sms_cleanup_interval), payload=self.cleanup_sms)
        logger.debug("Initializing tasks ... done")

        logger.debug(f"Initializing SMS-Worker ... done")

        logger.info(f"Starting SMS-Worker ...")

        # starting task manager workers
        self.start()

        logger.debug(f"Starting SMS-Worker ... done")

    def handle_sms(self):
        sms: Sms | None = None

        def get_sms() -> Sms | None:
            nonlocal sms
            sms = Sms.get(status=SmsStatus.QUEUED)
            return sms

        while get_sms():
            try:
                logger.info(f"Processing SMS with id={sms.id} ...")

                # calculate next_sms_gateway_index
                if self._next_sms_gateway_index is None:
                    self._next_sms_gateway_index = 0
                else:
                    self._next_sms_gateway_index += 1
                if self._next_sms_gateway_index >= len(self._gateways):
                    self._next_sms_gateway_index = 0

                # order gateways
                gateways: list[BaseGateway] = []
                for gateway in self._gateways[self._next_sms_gateway_index:]:
                    gateways.append(gateway)
                if self._next_sms_gateway_index > 0:
                    for gateway in self._gateways[:self._next_sms_gateway_index]:
                        gateways.append(gateway)

                # create sms logger
                sms_log = ""

                def add_sms_log(sms_log_msg: str):
                    nonlocal sms_log
                    if len(sms_log) > 0:
                        sms_log += "\n"
                    sms_log += sms_log_msg

                sms_logger = logging.Logger(name=f"{logger.name}", )
                sms_logger_handler = self.SmsLogHandler(buffer_target=add_sms_log)
                sms_logger_handler.setLevel(settings.worker.log_level.get_level_number())
                sms_logger_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
                sms_logger.addHandler(sms_logger_handler)
                sms_logger.setLevel(settings.worker.log_level.get_level_number())

                # send sms with gateways
                with LoggingContext(sms_logger, ignore_loggers_like=IGNORED_LOGGERS_LIKE):
                    log_level = logging.ERROR
                    result = "Error while sending SMS. Not gateways left."
                    status = SmsStatus.ERROR
                    send_by = None
                    for gateway in gateways:
                        gateway.increase_sms_count()
                        # check if gateway is available
                        if not gateway.check():
                            gateway.increase_sms_error_count()
                            continue

                        # send it with gateway
                        success, log_level, result = gateway.send_sms(sms.number, sms.message)
                        if success:
                            status = SmsStatus.SENT
                            send_by = gateway.name
                            break
                        gateway.increase_sms_error_count()
                    sms_logger.log(log_level, result)
                    logger.log(log_level, result)

                # flush sms_logger_handler
                sms_logger_handler.flush()

                # remove logger
                remove_logger(sms_logger)

                # update sms
                sms.update(status=status,
                           processed_datetime=datetime.now(),
                           sent_by=send_by,
                           result=result,
                           log=sms_log)

                logger.debug(f"Processing SMS with id={sms.id} ... done")
            except Exception as e:
                logger.error(f"Error while processing SMS with id={sms.id}.\nException: {e}")

    def cleanup_sms(self):
        try:
            cleanup_datetime = datetime.now() - timedelta(seconds=settings.worker.sms_cleanup_max_age)
            expression = and_(Sms.status != SmsStatus.QUEUED,
                              or_(
                                  and_(
                                      Sms.received_datetime <= cleanup_datetime,
                                      Sms.processed_datetime is None
                                  ),
                                  Sms.processed_datetime <= cleanup_datetime
                              ))
            cleanup_sms_count = Sms.length(expression)
            if cleanup_sms_count == 0:
                return
            logger.info(f"Cleaning up {cleanup_sms_count} SMS ...")
            Sms.delete_all(expression)
            logger.debug(f"Cleaning up {cleanup_sms_count} SMS ... done")
        except Exception as e:
            logger.error(f"Error while getting SMS to cleanup.\nException: {e}")
