import time
from typing import Literal

import typer

from kds_sms_server import __title__, __description__, __author__, __author_email__, __version__, __license__

from kds_sms_server.assets.ascii_logo import ascii_logo
from kds_sms_server.console import console

cli_app = typer.Typer()


def print_header(mode: Literal["info", "server", "worker", "cli"]):
    first_line = f"Starting {__title__}"
    if mode == "info":
        first_line += " ..."
    elif mode == "server":
        first_line += " - Server ..."
    elif mode == "worker":
        first_line += " - Worker ..."
    elif mode == "cli":
        first_line += " - CLI ..."
    console.print(first_line)
    console.print(ascii_logo)
    console.print("_________________________________________________________________________________\n")
    console.print(f"{__description__}")
    console.print(f"by {__author__}({__author_email__})")
    console.print(f"version: {__version__}")
    console.print(f"License: {__license__}")
    console.print("_________________________________________________________________________________")


def main_loop(mode: Literal["server", "worker"]):
    console.print(f"{__title__} - {mode.capitalize()} is ready. Press CTRL+C to quit.")
    try:
        while True:
            time.sleep(0.001)
    except KeyboardInterrupt:
        console.print(f"KeyboardInterrupt received. Stopping {__title__} - {mode.capitalize()} ...")


@cli_app.command(name="version", help=f"Show the version of {__title__}.")
def version_command() -> None:
    """
    Show the version of KDSM Manager.

    :return: None
    """

    # print header
    print_header(mode="info")


@cli_app.command(name="listener", help=f"Start the {__title__} - listener.")
def listener_command():
    """
    Start the server.

    :return: None
    """

    from kds_sms_server.db import db
    from kds_sms_server.listener import SmsListener

    # print header
    print_header(mode="server")

    # init db
    db().create_all()

    # start listener
    SmsListener()

    # entering main loop
    main_loop(mode="server")


@cli_app.command(name="worker", help=f"Start the {__title__} - worker.")
def worker_command():
    """
    Start the worker.

    :return: None
    """

    from kds_sms_server.db import db
    from kds_sms_server.worker import SmsWorker

    # print header
    print_header(mode="server")

    # init db
    db().create_all()

    # start worker
    SmsWorker()

    # entering main loop
    main_loop(mode="server")


@cli_app.command(name="init-db", help="Initialize database.")
def init_db_command():
    """
    Initialize database.
    :return: None
    """

    from kds_sms_server.db import db

    # print header
    print_header(mode="server")

    # init db
    console.print("Initializing database ...")
    db().create_all()
    console.print("Initializing database ... done")
