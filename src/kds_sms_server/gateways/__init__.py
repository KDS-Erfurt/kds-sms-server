from typing import Union

from kds_sms_server.gateways.base import (BaseConfig, BaseGateway)
from kds_sms_server.gateways.teltonika import (TeltonikaConfig, TeltonikaGateway)
from kds_sms_server.gateways.vonage import (VonageConfig, VonageGateway)

AVAILABLE_CONFIGS = Union[
    TeltonikaConfig,
    VonageConfig
]
