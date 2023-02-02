from classes.Logger import LOG


class SMSBaseGateway:
    def __init__(self):
        self.state = False
        self.sms_send_count = 0
        self.sms_send_error_count = 0

    def check(self) -> bool:
        self.state = self._check()
        return self.state

    def _check(self) -> bool:
        raise NotImplementedError

    def send_sms(self, number: str, message: str) -> tuple[bool, str]:
        self.sms_send_count += 1
        if self.state:
            result, msg = self._send_sms(number, message)
        else:
            LOG.error("SMS gateway is not available")
            result, msg = False, "SMS gateway is not available"

        if not result:
            self.sms_send_error_count += 1

        return result, msg

    def _send_sms(self, number: str, message: str) -> tuple[bool, str]:
        raise NotImplementedError

    def reset_metrics(self):
        self.sms_send_count = 0
        self.sms_send_error_count = 0
