from datetime import datetime

from pydantic import BaseModel


class MetricModel(BaseModel):
    sms_count: int
    sms_success: int
    end_dt: datetime
