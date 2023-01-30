from datetime import datetime

from pydantic import BaseModel


class MetricModel(BaseModel):
    sms_count: int
    sms_error_count: int
    end_dt: datetime
