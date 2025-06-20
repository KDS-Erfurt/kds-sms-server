import logging
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import chardet
from pydantic import BaseModel, Field

from kds_sms_server.server.server import BaseServer

if TYPE_CHECKING:
    from kds_sms_server.server.file.config import FileServerConfig

logger = logging.getLogger(__name__)


class FileModel(BaseModel):
    number: str = Field(default=..., title="Number", description="The phone number of the SMS.")
    message: str = Field(default=..., title="Message", description="The message of the SMS.")


class FileServer(BaseServer):
    __str_columns__ = ["name",
                       ("debug", "config_debug"),
                       ("directory", "config_directory")]

    def __init__(self, name: str, config: "FileServerConfig"):
        BaseServer.__init__(self, name=name, config=config)

        self.init_done()

    @property
    def config(self) -> "FileServerConfig":
        return super().config

    @property
    def config_directory(self) -> str:
        return str(self.config.directory.absolute())

    def enter(self):
        # check if directory exist
        if not self.config.directory.is_dir():
            if not self.config.directory_creating:
                logger.error(f"Directory '{self.config.directory}' does not exist.")
                sys.exit(1)
            try:
                logger.info(f"Created directory '{self.config.directory}' ...")
                self.config.directory.mkdir(parents=True)
                logger.info(f"Created directory '{self.config.directory}' ... done")
            except Exception as e:
                logger.error(f"Error while creating directory '{self.config.directory}': {e}")
                sys.exit(1)

        self.stated_done()

        while True:
            last = time.perf_counter()

            # iterate files from directory
            for file_path in self.config.directory.iterdir():
                if file_path.suffix not in self.config.file_extensions:
                    continue
                return self.handle_request(caller=None, file_path=file_path)

            # wait loop intervall
            while time.perf_counter() - last < self.config.directory_scan_interval:
                time.sleep(0.01)

    def exit(self):
        ...

    # noinspection DuplicatedCode
    def handle_request(self, caller: None, **kwargs) -> Any | None:
        logger.debug(f"{self} - Accept message:\nfile_path='{kwargs['file_path']}'")
        return super().handle_request(caller=caller, **kwargs)

    def handle_sms_data(self, caller: None, **kwargs) -> tuple[str, str] | None:
        # read file
        file_path: Path = kwargs["file_path"]
        try:
            with file_path.open("rb") as file:
                data  = file.read()
            logger.debug(f"{self} - data={data}")
        except Exception as e:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while reading data.")

        # detect encoding
        try:
            encoding = self.config.file_encoding
            if encoding == "auto":
                encoding = chardet.detect(data)['encoding']
            logger.debug(f"{self} - encoding={encoding}")
        except Exception as e:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while detecting encoding.")

        # decode message
        try:
            data_str = data.decode(encoding)
            logger.debug(f"{self} - data_str='{data_str}'")
        except Exception as e:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while decoding data.")

        # parse to FileModel
        try:
            file_model = FileModel.model_validate_json(data_str)
            logger.debug(f"{self} - file_model={file_model}")
        except Exception as e:
            return self.handle_response(caller=self, log_level=logging.ERROR, success=e, sms_id=None, result=f"Error while parsing data.")

        return file_model.number, file_model.message

    def success_handler(self, caller: None, sms_id: int, result: str, **kwargs) -> Any:
        file_path: Path = kwargs["file_path"]
        if self.config.file_delete_on_success:
            file_path.unlink()

    def error_handler(self, caller: None, sms_id: int | None, result: str, **kwargs) -> Any:
        file_path: Path = kwargs["file_path"]
        if self.config.file_delete_on_error:
            file_path.unlink()
