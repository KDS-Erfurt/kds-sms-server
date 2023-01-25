import os
from copy import deepcopy
from datetime import datetime
from signal import Signals

import psutil
import uvicorn
from fastapi import FastAPI
from fastapi_utils.tasks import repeat_every
from starlette.middleware import Middleware

from classes.Logger import LOG
from classes.LoggingMiddleware import LoggingMiddleware
from classes.SMSServer import SMSServer
from classes.Settings import SETTINGS
from classes.Static import STATIC
from models.MetricModel import MetricModel
from models.ModemMetricModel import ModemMetricModel
from models.StatusModel import StatusModel


class MetricServer(FastAPI):
    def __init__(self, sms_server: SMSServer, *args, **kwargs):
        kwargs["debug"] = SETTINGS.logging_level == "DEBUG"
        kwargs["title"] = STATIC.title
        kwargs["description"] = STATIC.description
        kwargs["version"] = STATIC.version
        kwargs["openapi_url"] = "/openapi.json" if SETTINGS.metric_docs else None
        kwargs["docs_url"] = "/docs" if SETTINGS.metric_docs else None
        kwargs["redoc_url"] = None
        kwargs["middleware"] = [Middleware(LoggingMiddleware)]
        super().__init__(*args, **kwargs)

        self.sms_server = sms_server
        self.start_dt = datetime.now()

        @self.on_event("startup")
        @repeat_every(seconds=1)
        def check_sms_server():
            LOG.debug("Checking SMSServer ...") if SETTINGS.logging_check else None
            if not sms_server.is_alive():
                LOG.error("SMSServer died!")
                parent = psutil.Process(os.getpid())
                for child in parent.children(recursive=True):
                    child.kill()

                parent.send_signal(Signals.CTRL_C_EVENT)
                return

            LOG.debug("SMSServer is alive.") if SETTINGS.logging_check else None

        @self.post("/status", response_model=StatusModel)
        def status() -> StatusModel:
            s = True
            status_text = "Server is in operational mode."

            sms_gateway_model_dicts = {}
            error_text = ""
            for sms_gateway in self.sms_server.sms_gateways:
                sms_gateway_name = sms_gateway.modem_config.name
                sms_gateway_status = sms_gateway.check()

                st = f"SMS Gateway '{sms_gateway_name}' is operational."
                if not sms_gateway_status:
                    if error_text != "":
                        error_text += " "
                    st = f"Gateway '{sms_gateway_name}' is not available."
                    error_text += st

                sg_model_dict = {
                    "status": sms_gateway_status,
                    "status_text": st
                }
                sms_gateway_model_dicts[sms_gateway_name] = sg_model_dict

            if error_text != "":
                s = False
                status_text = error_text

            runtime_in_sec = (datetime.now() - self.start_dt).seconds

            status_model_dict = {
                "status": s,
                "status_text": status_text,
                "sms_gateways": sms_gateway_model_dicts,
                "runtime_in_sec": runtime_in_sec
            }
            status_model = StatusModel(**status_model_dict)
            return status_model

        @self.post("/metric", response_model=MetricModel)
        def metric() -> MetricModel:
            metric_model_dict = {
                "sms_count": 0,
                "sms_success": 0,
                "end_dt": datetime.now()
            }
            metric_model = MetricModel(**metric_model_dict)
            return metric_model

        @self.post("/metric/{sms_gateway}", response_model=ModemMetricModel)
        def modem_metric(sms_gateway: str) -> ModemMetricModel:
            modem_metric_model_dict = {
                "sms_count": 0,
                "sms_success": 0,
                "end_dt": datetime.now(),
                "sms_gateway": sms_gateway
            }
            modem_metric_model = ModemMetricModel(**modem_metric_model_dict)
            return modem_metric_model

        LOG.debug(f"Initializing MetricServer. "
                  f"host='{SETTINGS.metric_server_host}', port={SETTINGS.metric_server_port}")

    def start(self):
        try:
            LOG.info("MetricServer serving forever ...")
            try:
                uvicorn_log_config = deepcopy(uvicorn.config.LOGGING_CONFIG)
                del uvicorn_log_config["formatters"]
                del uvicorn_log_config["handlers"]
                del uvicorn_log_config["loggers"]

                uvicorn.run(self,
                            host=SETTINGS.metric_server_host,
                            port=SETTINGS.metric_server_port,
                            log_config=uvicorn_log_config)
            except Exception as e:
                LOG.error(f"Error while starting MetricServer: {e}")
                return
        except KeyboardInterrupt:
            ...
        finally:
            LOG.info("Keyboard interrupt detected, stopping MetricServer ...")

        LOG.debug("MetricServer stopped.")

        if self.sms_server.is_alive():
            self.sms_server.stop()
