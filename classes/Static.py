import os
from pathlib import Path

from pydantic import BaseModel

from functions.increase_build_number import get_build_number


class Static(BaseModel):
    title: str = "KDS SMS-Server"
    state: str = "stable"
    version: str = "2.0.1"
    build_number: int = get_build_number()
    author: str = "Kirchhoff Datensysteme Services GmbH & Co. KG"
    author_email: str = "info@kds-kg.de"
    url: str = "kds-kg.de"
    description: str = "Ein Broker-Server zum Senden von SMS über Teltonika-Modems."

    cwd = Path(os.path.realpath(__file__)).parent.parent
    settings_file_path: Path = cwd / "settings.json"
    create_settings_file_if_not_exists: bool = True


STATIC = Static()
