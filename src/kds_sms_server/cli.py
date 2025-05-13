import typer
from wiederverwendbar.logger import LoggerSingleton

from kds_sms_server import __title__, __description__, __author__, __author_email__, __version__
from kds_sms_server.assets.ascii_logo import ascii_logo
from kds_sms_server.settings import settings
from kds_sms_server.console import console
from kds_sms_server.sms_server import SMSServer

LoggerSingleton(name=__name__,
                settings=settings,
                init=True)

cli_app = typer.Typer()


@cli_app.command(name="version", help="Print version and exit.")
def version():
    console.print(f"{__title__} v{__version__}")
    console.print(f"{__description__}")
    console.print(f"by {__author__}({__author_email__})")


@cli_app.command(name="serve", help="Run in foreground.")
def serve():
    console.print(f"Starting {__title__} ...")
    console.print(ascii_logo)
    console.print("_________________________________________________________________________________\n")
    console.print(f"{__description__}")
    console.print(f"by {__author__}({__author_email__})")
    console.print(f"version: {__version__}")
    console.print("_________________________________________________________________________________")

    SMSServer().serve()
