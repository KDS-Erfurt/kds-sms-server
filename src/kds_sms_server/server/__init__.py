from typing import Union

from kds_sms_server.server.base import (BaseServer, BaseServerConfig)
from kds_sms_server.server.tcp import (TcpServer, TcpServerConfig)
from kds_sms_server.server.api import (ApiServer, ApiServerConfig)

AVAILABLE_SERVER_CONFIGS = Union[
    TcpServerConfig,
    ApiServerConfig
]
