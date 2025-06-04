from wiederverwendbar.singleton import Singleton
from wiederverwendbar.logger import LoggerSingleton

from kds_sms_server import __name__ as __module_name__
from kds_sms_server.settings import settings


def logger() -> LoggerSingleton:
    try:
        return Singleton.get_by_type(LoggerSingleton)
    except RuntimeError:
        return LoggerSingleton(name=__module_name__,
                               settings=settings,
                               ignored_loggers_equal=settings.log_ignored_loggers_equal,
                               ignored_loggers_like=settings.log_ignored_loggers_like,
                               init=True)
