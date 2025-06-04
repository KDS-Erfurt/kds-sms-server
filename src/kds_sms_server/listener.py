import sys
import time

from wiederverwendbar.logger import LoggerSingleton

from kds_sms_server.gateways.gateway import BaseGateway
from kds_sms_server.gateways.teltonika.gateway import TeltonikaGateway
from kds_sms_server.gateways.vonage.gateway import VonageGateway
from kds_sms_server.server.server import BaseServer
from kds_sms_server.server.api.server import ApiServer
from kds_sms_server.server.tcp.server import TcpServer
from kds_sms_server.settings import settings

# noinspection PyArgumentList
logger = LoggerSingleton(name=__name__,
                         settings=settings.log_server,
                         ignored_loggers_like=["sqlalchemy", "pymysql", "asyncio", "parso", "engineio", "socketio", "python_multipart.multipart"],
                         init=True)


class SmsListener:
    def __init__(self):
        logger.info(f"Initializing SMS-Listener ...")

        # initialize servers and gateways
        logger.info("Initializing servers ...")
        self._server: list[BaseServer] = []
        for server_config_name, server_config in settings.sms_server.items():
            if len(server_config_name) > 20:
                logger.error(f"Server name '{server_config_name}' is too long. Max size is 20 characters.")
                sys.exit(1)

            server_cls = None
            if server_config.type == "tcp":
                server_cls = TcpServer
            elif server_config.type == "api":
                server_cls = ApiServer

            if server_cls is None:
                logger.error(f"Unknown server type '{server_config.type}'.")
                sys.exit(1)

            server = server_cls(name=server_config_name, config=server_config)
            self._server.append(server)
        if len(self._server) == 0:
            logger.error(f"No servers are configured. Please check your settings.")
            sys.exit(1)
        logger.debug("Initializing servers ... done")

        logger.info("Initializing gateways ...")
        # self._next_sms_gateway_index: int | None = None
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

        logger.debug(f"Initializing SMS-Listener ... done")

        logger.info(f"Starting SMS-Listener ...")
        # starting servers
        for server in self._server:
            server.start()

        # waiting for servers to start
        while True:
            if not any(not server.is_started for server in self._server):
                break
            logger.debug(f"Waiting for servers to start ...")
            time.sleep(1.0)

        logger.debug(f"Starting SMS-Listener ... done")
