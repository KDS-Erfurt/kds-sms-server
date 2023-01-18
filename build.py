import subprocess

from classes.Static import STATIC
from functions.increase_build_number import increase_build_number

if __name__ == '__main__':
    increase_build_number()
    import configparser

    config = configparser.ConfigParser()
    config["static"]["title"] = STATIC.title
    config["static"]["state"] = STATIC.state
    config["static"]["version"] = STATIC.version
    config["static"]["build_number"] = STATIC.build_number
    config["static"]["author"] = STATIC.author
    config["static"]["author_email"] = STATIC.author_email
    config["static"]["url"] = STATIC.url
    config["static"]["description"] = STATIC.description
    with open(STATIC.cwd / "static.ini", "w") as f:
        config.write(f)

    subprocess.run(["pyinstaller", "sms_server.spec", "--noconfirm"])
