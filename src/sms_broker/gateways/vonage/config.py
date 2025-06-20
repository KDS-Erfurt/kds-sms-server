from enum import Enum

from pydantic import Field

from sms_broker.gateways.config import BaseGatewayConfig


class VonageGatewayConfig(BaseGatewayConfig):
    class Type(str, Enum):
        VONAGE = "vonage"

    type: Type = Field(default=..., title="Type", description="Type of the gateway.")
    api_key: str = Field(default="", title="API key", description="API key for authentication.")
    api_secret: str = Field(default="", title="API secret", description="API secret for authentication.")
    from_text: str = Field(default="SMS-Broker", title="From Text", description="From Text visible for recipient.")
    check_balance: bool = Field(default=True, title="Check balance", description="If set to True, balance will be checked before sending SMS.")
    check_min_balance: float = Field(default=0.0, title="Check min balance", description="Minimum balance required for checking gateway availability.")
    check_auto_balance: bool = Field(default=True, title="Check auto balance",
                                     description="If set to True, min balance will be ignored if the vonage api returns an auto reload flag.")
