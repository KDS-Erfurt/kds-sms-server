from fastapi import FastAPI
from starlette.middleware import Middleware

from classes.Logger import LOG
from classes.LoggingMiddleware import LoggingMiddleware
from classes.Settings import SETTINGS


class MetricServer(FastAPI):
    def __init__(self, *args, **kwargs):
        kwargs["middleware"] = [Middleware(LoggingMiddleware)]
        super().__init__(*args, **kwargs)

        LOG.debug(
            f"Initializing MetricServer. host='{SETTINGS.metric_server_host}', port={SETTINGS.metric_server_port}")
