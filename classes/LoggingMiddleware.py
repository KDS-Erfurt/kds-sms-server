from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from classes.Logger import LOG
from classes.Settings import SETTINGS


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not SETTINGS.metric_logging:
            return await call_next(request)

        LOG.info(f"MetricServer request received. client='{request.client.host}:{request.client.port}'")
        LOG.debug(f"method='{request.method}'")
        LOG.debug(f"url='{request.url}'")
        LOG.debug(f"headers='")
        for header_key, header_value in request.headers.items():
            LOG.debug(f"    {header_key}: {header_value}")
        LOG.debug(f"'")
        LOG.debug(f"path_params='")
        for path_param_key, path_param_value in request.path_params.items():
            LOG.debug(f"    {path_param_key}: {path_param_value}")
        LOG.debug(f"'")
        LOG.debug(f"query_params='")
        for query_param_key, query_param_value in request.query_params.items():
            LOG.debug(f"    {query_param_key}: {query_param_value}")
        LOG.debug(f"'")

        response: Response = await call_next(request)
        LOG.info(f"MetricServer send response. client='{request.client.host}:{request.client.port}'")
        LOG.debug(f"status_code={response.status_code}")
        LOG.debug(f"headers='")
        for header_key, header_value in response.headers.items():
            LOG.debug(f"    {header_key}: {header_value}")
        LOG.debug(f"'")
        if "body" in dir(response):
            LOG.debug(f"body='{response.body}'")

        return response
