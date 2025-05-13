from typing import Union

from sms_server.gateways.base import (BaseConfig, BaseGateway)
from sms_server.gateways.teltonika import (TeltonikaConfig, TeltonikaGateway)
from sms_server.gateways.vonage import (VonageConfig, VonageGateway)

AVAILABLE_CONFIGS = Union[
    TeltonikaConfig,
    VonageConfig
]
