import sys
import time

from wiederverwendbar.logger import LoggerSingleton

from sms_broker.settings import settings
from sms_broker.server.server import BaseServer
from sms_broker.server.file.server import FileServer
from sms_broker.server.tcp.server import TcpServer
from sms_broker.server.api.server import ApiServer
from sms_broker.server.ui.server import UiServer

IGNORED_LOGGERS_LIKE = ["sqlalchemy", "pymysql", "asyncio", "parso", "engineio", "socketio", "python_multipart.multipart"]
# noinspection PyArgumentList
logger = LoggerSingleton(name=__name__,
                         settings=settings.listener,
                         ignored_loggers_like=IGNORED_LOGGERS_LIKE,
                         init=True)


class SmsListener:
    def __init__(self):
        logger.info(f"Initializing SMS-Listener ...")

        # initialize servers
        logger.info("Initializing servers ...")
        self._server: list[BaseServer] = []
        for server_config_name, server_config in settings.listener.server.items():
            if len(server_config_name) > 20:
                logger.error(f"Server name '{server_config_name}' is too long. Max size is 20 characters.")
                sys.exit(1)

            server_cls = None
            if server_config.type == "file":
                server_cls = FileServer
            elif server_config.type == "tcp":
                server_cls = TcpServer
            elif server_config.type == "api":
                server_cls = ApiServer
            elif server_config.type == "ui":
                server_cls = UiServer

            if server_cls is None:
                logger.error(f"Unknown server type '{server_config.type}'.")
                sys.exit(1)

            server = server_cls(name=server_config_name, config=server_config)
            self._server.append(server)
        if len(self._server) == 0:
            logger.error(f"No servers are configured. Please check your settings.")
            sys.exit(1)
        logger.debug("Initializing servers ... done")

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
