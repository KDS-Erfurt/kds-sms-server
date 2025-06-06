from enum import Enum
from pathlib import Path

from pydantic import Field

from sms_broker.server.config import BaseServerConfig


class FileServerConfig(BaseServerConfig):
    class Type(str, Enum):
        FILE = "file"

    type: Type = Field(default=..., title="Type", description="Type of the server.")
    directory: Path = Field(default=..., title="File Server Directory", description="Directory for incoming files.")
    directory_creating: bool = Field(default=True, title="File Server Creating Directory", description="Create directory if it doesn't exist.")
    directory_scan_interval: int = Field(default=1, title="File Server Scan Interval", description="Scan interval for incoming files.")
    file_extensions: list[str] = Field(default_factory=lambda: [".json"], title="File extensions", description="List of file extensions accepted by the server.")
    file_encoding: str = Field(default="auto", title="TCP Server input encoding", description="Encoding of incoming files.")
    file_delete_on_success: bool = Field(default=True, title="Delete file on success", description="Delete file on success.")
    file_delete_on_error: bool = Field(default=True, title="Delete file on error", description="Delete file on error.")
