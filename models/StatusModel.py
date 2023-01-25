from pydantic import BaseModel


class StatusModel(BaseModel):
    class SMSGateway(BaseModel):
        status: bool
        status_text: str

    status: bool
    status_text: str
    sms_gateways: dict[str, SMSGateway] = {}
    runtime_in_sec: int
