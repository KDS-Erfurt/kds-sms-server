import json
import sys
from pathlib import Path

from classes.Console import CONSOLE

BUILD_NUMBER_FILE_PATH = Path("build_number.json")


def increase_build_number():
    if BUILD_NUMBER_FILE_PATH.exists():
        try:
            build_number = json.loads(BUILD_NUMBER_FILE_PATH.read_text())["build_number"]
        except json.JSONDecodeError as e:
            CONSOLE.print(f"[red]ERROR[/red]:\t  {BUILD_NUMBER_FILE_PATH} is not a valid JSON file.")
            CONSOLE.print(f"[red]ERROR[/red]:\t  {e}")
            sys.exit(1)

        build_number += 1
        CONSOLE.print(f"[green]SUCCESS[/green]:\t  Build number increased to {build_number}.")
    else:
        build_number = 1

    with open(BUILD_NUMBER_FILE_PATH, "w") as f:
        json.dump({"build_number": build_number}, f, indent=4)


def get_build_number():
    if BUILD_NUMBER_FILE_PATH.exists():
        try:
            build_number = json.loads(BUILD_NUMBER_FILE_PATH.read_text())["build_number"]
        except json.JSONDecodeError as e:
            CONSOLE.print(f"[red]ERROR[/red]:\t  {BUILD_NUMBER_FILE_PATH} is not a valid JSON file.")
            CONSOLE.print(f"[red]ERROR[/red]:\t  {e}")
            sys.exit(1)
    else:
        build_number = 1

    return build_number
