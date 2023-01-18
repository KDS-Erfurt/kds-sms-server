import logging
import logging.handlers as handlers
from enum import Enum
from typing import Callable

from classes.Console import CONSOLE
from classes.Settings import SETTINGS
from classes.Static import STATIC


class Logger:
    class Lvl(Enum):
        DEBUG = 0
        INFO = 1
        WARNING = 2
        ERROR = 3

    def __init__(self, logging_enabled: bool, logging_level: str):
        self.logging_enabled: bool = logging_enabled
        self.logging_level: str = logging_level
        self._logging_functions: list[Callable] = []

    def _log(self, message: str, level: Lvl):
        if not self.logging_enabled:
            return

        log_lvl = [lvl_name for lvl_name, lvl in self.Lvl.__members__.items()]
        log_lvl = log_lvl[:log_lvl.index(level.name) + 1]
        if self.logging_level not in log_lvl:
            return

        for log_func in self._logging_functions:
            log_func(message, level)

    def log(self, message: str, level: Lvl):
        self._log(message, level)

    def debug(self, message: str):
        self._log(message, self.Lvl.DEBUG)

    def info(self, message: str):
        self._log(message, self.Lvl.INFO)

    def warning(self, message: str):
        self._log(message, self.Lvl.WARNING)

    def error(self, message: str):
        self._log(message, self.Lvl.ERROR)

    def add_logging_function(self, log_func: Callable):
        self._logging_functions.append(log_func)

    def remove_logging_function(self, log_func: Callable):
        self._logging_functions.remove(log_func)


LOG = Logger(logging_enabled=SETTINGS.logging, logging_level=SETTINGS.logging_level)


def textual_log(message: str, level: Logger.Lvl):
    if level == Logger.Lvl.DEBUG:
        CONSOLE.print(f"[magenta]{level.name}[/magenta]:\t  {message}")
    elif level == Logger.Lvl.INFO:
        CONSOLE.print(f"[green]{level.name}[/green]:\t  {message}")
    elif level == Logger.Lvl.WARNING:
        CONSOLE.print(f"[yellow]{level.name}[/yellow]:\t  {message}")
    elif level == Logger.Lvl.ERROR:
        CONSOLE.print(f"[red]{level.name}[/red]:\t  {message}")
    else:
        CONSOLE.print(f"[white]{level.name}[/white]:\t  {message}")


LOG.add_logging_function(textual_log)

logger = logging.getLogger("")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
log_handler = handlers.TimedRotatingFileHandler(STATIC.cwd / SETTINGS.logging_file,
                                                when=SETTINGS.logging_file_rotate_when,
                                                interval=SETTINGS.logging_file_rotate_interval,
                                                backupCount=SETTINGS.logging_file_rotate_backup_count)
log_handler.setLevel(logging.DEBUG)
log_handler.setFormatter(formatter)

logger.addHandler(log_handler)


def file_log(message: str, level: Logger.Lvl):
    if level == Logger.Lvl.DEBUG:
        logger.debug(message)
    elif level == Logger.Lvl.INFO:
        logger.info(message)
    elif level == Logger.Lvl.WARNING:
        logger.warning(message)
    elif level == Logger.Lvl.ERROR:
        logger.error(message)
    else:
        logger.critical(message)


LOG.add_logging_function(file_log)
