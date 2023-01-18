from time import sleep

from classes.Logger import LOG
from classes.SMSServer import SMSServer


def main():
    sms_server = SMSServer()
    sms_server.start()

    LOG.info("Entering main loop ...")
    try:
        while True:
            if not sms_server.is_alive():
                LOG.error("SMSServer died!")
                break
            sleep(0.001)
        LOG.info("Exiting main loop ...")
    except KeyboardInterrupt:
        LOG.info("Keyboard interrupt detected, stopping ...")

    if sms_server.is_alive():
        sms_server.stop()
