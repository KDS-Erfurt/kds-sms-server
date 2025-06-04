import typer

from kds_sms_server import __title__
from kds_sms_server.console import console

cli_app = typer.Typer()


@cli_app.command(name="version", help=f"Show the version of {__title__}.")
def version_command() -> None:
    """
    Show the version of KDSM Manager.

    :return: None
    """

    from kds_sms_server import __title__, __description__, __author__, __author_email__, __version__, __license__

    console.print(f"{__title__} v{__version__} by {__author__}")
    console.print(f"{__description__}")
    console.print(f"E-Mail: {__author_email__}")
    console.print(f"License: {__license__}")


@cli_app.command(name="serve", help="Start the server.")
def serve_command():
    """
    Start the server.

    :return: None
    """

    from kds_sms_server import __title__, __description__, __author__, __author_email__, __version__
    from kds_sms_server.assets.ascii_logo import ascii_logo
    from kds_sms_server.sms_server import SmsServer, logger

    console.print(f"Starting {__title__} ...")
    console.print(ascii_logo)
    console.print("_________________________________________________________________________________\n")
    console.print(f"{__description__}")
    console.print(f"by {__author__}({__author_email__})")
    console.print(f"version: {__version__}")
    console.print("_________________________________________________________________________________")

    # start logging
    logger()

    # start server
    SmsServer()


@cli_app.command(name="init-db", help="Initialize database.")
def init_db_command():
    """
    Initialize database.
    :return: None
    """

    from kds_sms_server.db import db

    db().create_all()
