import os
from copy import deepcopy

from signal import Signals

import psutil as psutil
import uvicorn

from classes.Logger import LOG
from classes.MetricServer import MetricServer
from classes.SMSServer import SMSServer
from classes.Settings import SETTINGS

from fastapi_utils.tasks import repeat_every


def main():
    sms_server = SMSServer()
    sms_server.start()

    try:
        metric_server = MetricServer()

        @metric_server.on_event("startup")
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

        LOG.info("MetricServer serving forever ...")
        try:
            uvicorn_log_config = deepcopy(uvicorn.config.LOGGING_CONFIG)
            del uvicorn_log_config["formatters"]
            del uvicorn_log_config["handlers"]
            del uvicorn_log_config["loggers"]

            uvicorn.run(metric_server,
                        host=SETTINGS.metric_server_host,
                        port=SETTINGS.metric_server_port,
                        log_config=uvicorn_log_config)
        except Exception as e:
            LOG.error(f"Error while starting MetricServer: {e}")
            return
    except KeyboardInterrupt:
        ...
    finally:
        LOG.info("Keyboard interrupt detected, stopping ...")

    LOG.info("MetricServer stopped serving.")

    if sms_server.is_alive():
        sms_server.stop()
