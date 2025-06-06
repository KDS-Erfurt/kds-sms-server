from pydantic import Field

from sms_broker.base import BaseConfig


class BaseServerConfig(BaseConfig):
    debug: bool = Field(default=False, title="Debug", description="If set to True, server will be started in debug mode.")
