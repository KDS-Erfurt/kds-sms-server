class SMSBaseGateway:
    def __init__(self):
        self.state = False

    def check(self) -> bool:
        raise NotImplementedError

    def send_sms(self, number: str, message: str) -> tuple[bool, str]:
        raise NotImplementedError
