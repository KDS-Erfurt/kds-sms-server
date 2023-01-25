from classes.MetricServer import MetricServer
from classes.SMSServer import SMSServer


def main():
    sms_server = SMSServer()
    sms_server.start()

    metric_server = MetricServer(sms_server=sms_server)
    metric_server.start()
