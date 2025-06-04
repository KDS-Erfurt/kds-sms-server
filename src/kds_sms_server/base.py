import logging
import warnings
from abc import ABC
from typing import Any, TYPE_CHECKING, Union

from pydantic import BaseModel, PrivateAttr
from wiederverwendbar.functions.get_pretty_str import get_pretty_str

if TYPE_CHECKING:
    from kds_sms_server.sms_server import SmsServer

logger = logging.getLogger(__name__)


class Base(ABC):
    __str_columns__: list[str | tuple[str]] = ["name"]

    def __init__(self, server: "SmsServer", name: str, config: "BaseConfig"):
        self._name = name
        self._server = server
        self._config = config

        logger.info(f"Initializing {self} ...")

    def __str__(self):
        out = f"{self.__class__.__name__}("
        for attr_name in self.__str_columns__:
            if type(attr_name) is tuple:
                attr_view_name = attr_name[0]
                attr_name = attr_name[1]
            else:
                attr_view_name = attr_name
            if not hasattr(self, attr_name):
                warnings.warn(f"Attribute '{attr_name}' is not set for {self}.")
            out += f"{attr_view_name}={get_pretty_str(getattr(self, attr_name))}, "
        out = out[:-2] + ")"
        return out

    def __repr__(self):
        return f"{self.__class__.__name__}(server={self.server}, name={self.name}, config={self.config})"

    @property
    def name(self) -> str:
        return self._name

    @property
    def server(self) -> "SmsServer":
        return self._server

    @property
    def config(self) -> Union["BaseConfig", Any]:
        return self._config

    def init_done(self):
        logger.debug(f"Initializing {self} ... done")


class BaseConfig(BaseModel):
    class Config:
        use_enum_values = True

    _cls: type[Any] | None = PrivateAttr(None)

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        _ = self.cls

    @property
    def cls(self) -> type[Any]:
        if self._cls is None:
            raise ValueError("Class is not set")
        return self._cls
