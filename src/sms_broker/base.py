import logging
import warnings
from abc import ABC
from typing import Any, Union

from pydantic import BaseModel, PrivateAttr
from wiederverwendbar.functions.get_pretty_str import get_pretty_str

logger = logging.getLogger(__name__)


class Base(ABC):
    __str_columns__: list[str | tuple[str]] = ["name"]

    def __init__(self, name: str, config: "BaseConfig"):
        self._name = name
        self._config = config
        self._sms_count = 0
        self._sms_error_count = 0

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
        return f"{self.__class__.__name__}(name={self.name}, config={self.config})"

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> Union["BaseConfig", Any]:
        return self._config

    @property
    def sms_count(self) -> int:
        return self._sms_count

    @property
    def sms_error_count(self) -> int:
        return self._sms_error_count

    def init_done(self):
        logger.debug(f"Initializing {self} ... done")

    def increase_sms_count(self) -> None:
        self._sms_count += 1

    def increase_sms_error_count(self) -> None:
        self._sms_error_count += 1

    def reset_metrics(self):
        self._sms_count = 0
        self._sms_error_count = 0

class BaseConfig(BaseModel):
    class Config:
        use_enum_values = True
