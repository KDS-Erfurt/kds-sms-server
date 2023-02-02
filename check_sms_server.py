#!/opt/kds_environments/testing/python/Python-3.7.2/bin/python3.7

from pathlib import Path

import nagiosplugin
import requests
import typer
from nagiosplugin import Range

cache_path = Path("/var/lib/centreon-engine/")
app = typer.Typer()
global_summary_text = ""
global_request: dict = {}
global_response: dict = {}


class Status(nagiosplugin.Resource):
    def __init__(self,
                 host: str,
                 port: int,
                 timeout: int,
                 retries: int,
                 ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        global global_summary_text
        global_summary_text = ""

    def probe(self):
        response = request(self.host, self.port, self.timeout, self.retries, "/status")

        yield nagiosplugin.Metric("runtime_in_sec",
                                  response["runtime_in_sec"],
                                  min=0,
                                  uom="sec",
                                  context="runtime_in_sec")
        gateway_count = len(response["sms_gateways"])
        gateway_with_error_count = 0
        for k, v in response["sms_gateways"].items():
            if not v["status"]:
                gateway_with_error_count += 1

        yield nagiosplugin.Metric("gateways_with_error",
                                  gateway_with_error_count,
                                  min=0,
                                  max=gateway_count,
                                  context="gateways_with_error")

        global global_summary_text
        global_summary_text = response["status_text"]


class Metric(nagiosplugin.Resource):
    def __init__(self,
                 host: str,
                 port: int,
                 timeout: int,
                 retries: int,
                 sms_gateway_name: str = "",
                 ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.retries = retries
        self.sms_gateway_name = sms_gateway_name
        global global_summary_text
        global_summary_text = ""

    def probe(self):
        path = "/metric"
        if self.sms_gateway_name:
            path += f"/{self.sms_gateway_name}"
        response = request(self.host, self.port, self.timeout, self.retries, path)

        sms_count = response["sms_count"]

        yield nagiosplugin.Metric("sms_count",
                                  sms_count,
                                  min=0.0,
                                  context="sms_count")

        sms_error_count = response["sms_error_count"]

        yield nagiosplugin.Metric("sms_error_count",
                                  sms_error_count,
                                  min=0.0,
                                  context="sms_error_count")

        global global_summary_text
        global_summary_text = f"SMS Count: {sms_count}, SMS Error Count: {sms_error_count}"


class Summary(nagiosplugin.Summary):
    def ok(self, results):
        global global_summary_text
        return global_summary_text

    def problem(self, results):
        global global_summary_text
        return global_summary_text

    def verbose(self, results):
        global global_request, global_response
        verbose_msg = "Verbose:\n"

        verbose_msg += f"* Results:\n"
        for result in results:
            verbose_msg += f" * {result}\n"

        if global_request:
            verbose_msg += f"* Request:\n"
            verbose_msg += f" * URL: {global_request['url']}\n"
            verbose_msg += f" * Method: {global_request['method']}\n"
            verbose_msg += f" * Headers: {global_request['headers']}\n"
            verbose_msg += f" * Body: {global_request['body']}\n"

        if global_response:
            verbose_msg += f"* Response:\n"
            verbose_msg += f" * Status Code: {global_response['status_code']}\n"
            verbose_msg += f" * Text: {global_response['text']}\n"

        return verbose_msg


def request(host: str, port: int, timeout: int, retries: int, path: str = ""):
    global global_request, global_response
    for retry in range(retries):
        try:
            response = requests.post(f"http://{host}:{port}{path}", timeout=timeout)
            global_request = {
                "url": response.request.url,
                "method": response.request.method,
                "headers": response.request.headers,
                "body": response.request.body
            }
            global_response = {
                "status_code": response.status_code,
                "text": response.text
            }
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"HTTP Status Code: {response.status_code} Response: {response.text}")
        except requests.exceptions.ConnectTimeout:
            raise Exception(f"Connection Timeout")


@app.command()
def status(host: str = typer.Option(..., "-h", "--host", help="Host to check"),
           port: int = typer.Option(8000, "-p", "--port", help="Port to check"),
           timeout: int = typer.Option(5, "-t", "--timeout", help="Timeout in seconds"),
           retries: int = typer.Option(3, "-r", "--retries", help="Number of retries"),
           warning_count_gateway_with_error: int = typer.Option(1,
                                                                "-w",
                                                                "--warning",
                                                                help="Warning threshold for gateways with error"),
           critical_count_gateway_with_error: int = typer.Option(2,
                                                                 "-c",
                                                                 "--critical",
                                                                 help="Critical threshold for gateways with error"),
           verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output")
           ):
    nagiosplugin.Check(
        Status(host, port, timeout, retries),

        nagiosplugin.ScalarContext("runtime_in_sec"),
        nagiosplugin.ScalarContext("gateways_with_error",
                                   Range(warning_count_gateway_with_error - 0.001),
                                   Range(critical_count_gateway_with_error - 0.001),
                                   fmt_metric='{value} gateways with error'),
        Summary()).main(verbose=verbose)


@app.command()
def metric(host: str = typer.Option(..., "-h", "--host", help="Host to check"),
           port: int = typer.Option(8000, "-p", "--port", help="Port to check"),
           timeout: int = typer.Option(5, "-t", "--timeout", help="Timeout in seconds"),
           retries: int = typer.Option(3, "-r", "--retries", help="Number of retries"),
           sms_gateway_name: str = typer.Option("", "-g", "--gateway", help="SMS Gateway Name"),
           verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output")
           ):
    nagiosplugin.Check(
        Metric(host, port, timeout, retries, sms_gateway_name),

        nagiosplugin.ScalarContext("sms_count"),
        nagiosplugin.ScalarContext("sms_error_count", 0.999, 0.999),
        Summary()).main(verbose=verbose)


@nagiosplugin.guarded
def main():
    app()


if __name__ == '__main__':
    main()
