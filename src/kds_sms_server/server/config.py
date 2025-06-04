from pydantic import Field

from kds_sms_server.base import BaseConfig


class BaseServerConfig(BaseConfig):
    debug: bool = Field(default=False, title="Debug", description="If set to True, server will be started in debug mode.")
