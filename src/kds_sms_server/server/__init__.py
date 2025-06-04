from typing import Union

from kds_sms_server.server.base import (BaseServer, BaseServerConfig)
from kds_sms_server.server.tcp_server import (TcpServer, TcpServerConfig)
from kds_sms_server.server.api_server import (ApiServer, ApiServerConfig)

AVAILABLE_SERVER_CONFIGS = Union[
    TcpServer,
    ApiServer
]
