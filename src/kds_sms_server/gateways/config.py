from pydantic import Field

from sms_broker.base import BaseConfig


class BaseGatewayConfig(BaseConfig):
    dry_run: bool = Field(default=False, title="Dry run mode", description="If set to True, SMS will not be sent via this gateway."
                                                                           "This is useful for testing purposes.")
    timeout: int = Field(default=5, title="Timeout", description="Timeout for sending SMS via this gateway.")
    check: bool = Field(default=True, title="Check", description="If set to True, gateway will be checked before sending SMS.")
    check_timeout: int = Field(default=1, title="Check timeout", description="Timeout for checking gateway availability.")
    check_retries: int = Field(default=3, title="Check retries", description="Number of retries for checking gateway availability.")
