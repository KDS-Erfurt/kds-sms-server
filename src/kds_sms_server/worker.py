import sys

from wiederverwendbar.logger import LoggerSingleton
from wiederverwendbar.task_manger import TaskManager, Task, EverySeconds

from kds_sms_server.db import Sms, SmsStatus
from kds_sms_server.settings import settings
from kds_sms_server.gateways.gateway import BaseGateway
from kds_sms_server.gateways.teltonika.gateway import TeltonikaGateway
from kds_sms_server.gateways.vonage.gateway import VonageGateway

# noinspection PyArgumentList
logger = LoggerSingleton(name=__name__,
                         settings=settings.log_server,
                         ignored_loggers_like=["sqlalchemy", "pymysql"],
                         init=True)


class SmsWorker(TaskManager):
    def __init__(self):
        logger.info(f"Initializing SMS-Worker ...")
        super().__init__(name="SMS-Worker", worker_count=settings.sms_background_worker_count, daemon=True, logger=logger)

        # initialize gateway
        logger.info("Initializing gateways ...")
        self._next_sms_gateway_index: int | None = None
        self._gateways: list[BaseGateway] = []
        for gateway_config_name, gateway_config in settings.sms_gateways.items():
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
        Task(name="Handle SMS", manager=self, trigger=EverySeconds(settings.sms_handle_interval), payload=self.handle_sms)
        Task(name="Cleanup SMS", manager=self, trigger=EverySeconds(settings.sms_cleanup_interval), payload=self.cleanup_sms)
        logger.debug("Initializing tasks ... done")

        logger.debug(f"Initializing SMS-Worker ... done")

        logger.info(f"Starting SMS-Worker ...")

        # starting task manager workers
        self.start()

        logger.debug(f"Starting SMS-Worker ... done")

    def handle_sms(self):
        # get all queued sms
        queued_sms = Sms.get_all(status=SmsStatus.QUEUED, order_by=Sms.received_datetime)
        if len(queued_sms) == 0:
            return
        queued_sms_count = len(queued_sms)
        logger.debug(f"Processing {queued_sms_count} queued SMS ...")

        # calculate next_sms_gateway_index
        if self._next_sms_gateway_index is None:
            self._next_sms_gateway_index = 0
        else:
            self._next_sms_gateway_index += 1
        if self._next_sms_gateway_index >= len(self._gateways):
            self._next_sms_gateway_index = 0

        # order gateways
        gateways = []
        for gateway in self._gateways[self._next_sms_gateway_index:]:
            gateways.append(gateway)
        if self._next_sms_gateway_index > 0:
            for gateway in self._gateways[:self._next_sms_gateway_index]:
                gateways.append(gateway)

        # send sms with gateways
        logger.debug("------------------------------------------------------------------------------------------------------")
        result = False
        message = ""
        for gateway in gateways:
            # check if gateway is available
            if not gateway.check():
                continue

            # send it with gateway
            result = gateway.send_sms(number, message)
            if result:
                result = True
                message = f"SMS sent successfully via {gateway}."
                return True, ""
        logger.debug("------------------------------------------------------------------------------------------------------")
        return False, f"Error while sending SMS. Not gateways left."

        print()
        ...

    def cleanup_sms(self):
        ...
