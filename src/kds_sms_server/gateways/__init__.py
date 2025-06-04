from typing import Union

from kds_sms_server.gateways.base import (BaseGateway, BaseGatewayConfig)
from kds_sms_server.gateways.teltonika import (TeltonikaGateway, TeltonikaGatewayConfig)
from kds_sms_server.gateways.vonage import (VonageGateway, VonageGatewayConfig)

AVAILABLE_GATEWAY_CONFIGS = Union[
    TeltonikaGatewayConfig,
    VonageGatewayConfig
]
