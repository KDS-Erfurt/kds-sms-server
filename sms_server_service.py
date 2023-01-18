import sys

import servicemanager
import win32service
import win32serviceutil

from classes.Logger import LOG
from classes.Static import STATIC
from functions.main import main


class SMSServerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "sms_server_service"
    _svc_display_name_ = "KDS SMS-Server Service"
    _svc_description_ = "Die Service steuert den KDS SMS-Server."

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        main()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


def init():
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SMSServerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SMSServerService)


if __name__ == '__main__':
    LOG.info(f"Starting {STATIC.title} service ...")
    init()
