from typing import Any

from pydantic import BaseModel, PrivateAttr


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
