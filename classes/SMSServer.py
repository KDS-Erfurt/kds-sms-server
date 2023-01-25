import threading

from classes.Logger import LOG
from classes.SMSServerHandler import SMSServerHandler
from classes.Settings import SETTINGS
from classes.TCPServer import TCPServer
from classes.TeltonikaModem import TeltonikaModem


class SMSServer(threading.Thread):
    def __init__(self):
        LOG.debug(f"Initializing SMSServer. host='{SETTINGS.server_host}', port={SETTINGS.server_port}")

        threading.Thread.__init__(self)
        self.server: TCPServer | None = None

        self.sms_gateways: list[TeltonikaModem] = []
        for modem_config in SETTINGS.modem_configs:
            self.sms_gateways.append(TeltonikaModem(modem_config))
        self.next_sms_gateway_index: int = 0

        LOG.debug("SMSServer initialized.")

    def run(self):
        LOG.debug("Starting SMSServer ...")
        try:
            self.server = TCPServer(self, (SETTINGS.server_host, SETTINGS.server_port), SMSServerHandler)
        except Exception as e:
            LOG.error(f"Error while starting SMSServer: {e}")
            return
        LOG.debug("SMSServer started.")

        LOG.info("SMSServer serving forever ...")
        self.server.serve_forever()

    def stop(self):
        if self.server is None:
            LOG.error("SMSServer is not running.")
            return
        LOG.info("Stopping SMSServer ...")
        self.server.shutdown()
        self.server.server_close()
        LOG.debug("SMSServer stopped.")
