import subprocess

from classes.Static import STATIC
from functions.increase_build_number import increase_build_number

if __name__ == '__main__':
    increase_build_number()
    import configparser

    config = configparser.ConfigParser()
    config["static"] = {}
    config["static"]["title"] = str(STATIC.title)
    config["static"]["state"] = str(STATIC.state)
    config["static"]["version"] = str(STATIC.version)
    config["static"]["build_number"] = str(STATIC.build_number)
    config["static"]["author"] = str(STATIC.author)
    config["static"]["author_email"] = str(STATIC.author_email)
    config["static"]["url"] = str(STATIC.url)
    config["static"]["description"] = str(STATIC.description)
    with open(STATIC.cwd / "static.ini", "w") as f:
        config.write(f)

    subprocess.run(["pyinstaller", "sms_server.spec", "--noconfirm"])
