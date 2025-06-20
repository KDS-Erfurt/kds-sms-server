import time
from typing import Literal

from sms_broker.settings import settings
from wiederverwendbar.typer import Typer

cli_app = Typer(settings=settings)


def main_loop(mode: Literal["listener", "worker"]):
    cli_app.console.print(f"{settings.branding_title} - {mode.capitalize()} is ready. Press CTRL+C to quit.")
    try:
        while True:
            time.sleep(0.001)
    except KeyboardInterrupt:
        cli_app.console.print(f"KeyboardInterrupt received. Stopping {settings.branding_title} - {mode.capitalize()} ...")


@cli_app.command(name="listener", help=f"Start the {settings.branding_title} - listener.")
def listener_command():
    """
    Start the listener.

    :return: None
    """

    from sms_broker.db import db
    from sms_broker.listener import SmsListener

    # print header
    cli_app.console.print(f"Starting {settings.branding_title} - Listener ...")
    cli_app.console.print(f"[white]{cli_app.title_header}[/white]")

    # init db
    db().create_all()

    # start listener
    SmsListener()

    # entering main loop
    main_loop(mode="listener")


@cli_app.command(name="worker", help=f"Start the {settings.branding_title} - worker.")
def worker_command():
    """
    Start the worker.

    :return: None
    """

    from sms_broker.db import db
    from sms_broker.worker import SmsWorker

    # print header
    cli_app.console.print(f"Starting {settings.branding_title} - Worker ...")
    cli_app.console.print(f"[white]{cli_app.title_header}[/white]")

    # init db
    db().create_all()

    # start worker
    SmsWorker()

    # entering main loop
    main_loop(mode="listener")


@cli_app.command(name="init-db", help="Initialize database.")
def init_db_command():
    """
    Initialize database.
    :return: None
    """

    from sms_broker.db import db

    # print header
    cli_app.console.print(f"[white]{cli_app.title_header}[/white]")

    # init db
    cli_app.console.print(f"Initializing database for {settings.branding_title} ...")
    db().create_all()
    cli_app.console.print("Done")
