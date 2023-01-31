#!/opt/kds_environments/testing/python/Python-3.7.2/bin/python3.7

from enum import Enum

import requests
import typer as typer

debugging = False
app = typer.Typer()


class ExitCodes(Enum):
    UP = 0
    OK = 0
    WARNING = 1
    DOWN = 2
    CRITICAL = 2
    UNKNOWN = 3


def exit(code: ExitCodes, message: str, **perf_data):
    if perf_data:
        message += " | "
        for key, value in perf_data.items():
            message += f"'{key}'={value};0;0 "
    typer.echo(message)
    raise typer.Exit(code.value)


def debug(msg):
    global debugging
    if not debugging:
        return

    print(msg)


def request(host: str, port: int, timeout: int, retries: int, path: str = ""):
    json_response = None
    for retry in range(retries):
        try:
            response = requests.post(f"http://{host}:{port}{path}", timeout=timeout)
            if response.status_code == 200:
                json_response = response.json()
                break
            else:
                print(f"HTTP Status Code: {response.status_code}")
                print(f"Response: {response.text}")
            break
        except requests.exceptions.ConnectionError as e:
            print(f"ConnectionError: {e}")
    return json_response


@app.command()
def status(host: str, port: int = 8000, timeout: int = 5, retries: int = 3):
    response = request(host, port, timeout, retries, "/status")

    if response is None:
        exit(ExitCodes.DOWN, "Unable to connect to server")

    all_gateways_down = True
    perf_data = {"runtime_in_sec": response["runtime_in_sec"]}
    for k, v in response["sms_gateways"].items():
        perf_data[k] = 1 if v["status"] else 0
        if v["status"]:
            all_gateways_down = False
    msg = response["status_text"]

    if response["status"]:
        exit(ExitCodes.UP, msg, **perf_data)
    else:
        if all_gateways_down:
            exit(ExitCodes.CRITICAL, msg, **perf_data)
        else:
            exit(ExitCodes.WARNING, msg, **perf_data)


@app.command()
def metric(host: str, port: int = 8000, timeout: int = 1, retries: int = 3, sms_gateway_name: str = ""):
    path = "/metric"
    if sms_gateway_name:
        path += f"/{sms_gateway_name}"
    response = request(host, port, timeout, retries, path)

    if response is None:
        exit(ExitCodes.DOWN, "Unable to connect to server")

    perf_data = {
        "sms_count": response["sms_count"],
        "sms_error_count": response["sms_error_count"],
    }

    msg = f"Since {response['end_dt']} '{response['sms_count']}' SMS sent"
    if sms_gateway_name:
        msg += f" with gateway '{sms_gateway_name}'"
    msg += f", '{response['sms_error_count']}' errors."

    if response["sms_error_count"] > 0:
        exit(ExitCodes.WARNING, msg, **perf_data)
    else:
        exit(ExitCodes.OK, msg, **perf_data)


if __name__ == '__main__':
    app()
