from enum import Enum
from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, VARCHAR

from wiederverwendbar.singleton import Singleton
from wiederverwendbar.sqlalchemy import SqlalchemyDb, Base, EnumValueStr

from kds_sms_server.settings import settings


class Db(SqlalchemyDb, metaclass=Singleton):
    ...


def db() -> Db:
    try:
        return Singleton.get_by_type(Db)
    except RuntimeError:
        # noinspection PyArgumentList
        return Db(settings=settings, init=True)


class SmsStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    ABORTED = "aborted"
    ERROR = "error"


class Sms(Base, db().Base):
    __tablename__ = "sms"
    __str_columns__ = ["id", "status", "received_datetime", "send_datetime", "number"]

    id: int = Column(Integer(), primary_key=True, autoincrement=True, name="sms_id")
    status: SmsStatus = Column(EnumValueStr(SmsStatus), nullable=False, name="sms_status")
    received_by: str = Column(VARCHAR(20), nullable=False, name="sms_received_by")
    received_datetime: datetime = Column(DateTime(), nullable=False, name="sms_received_datetime")
    processed_datetime: datetime = Column(DateTime(), nullable=True, name="sms_processed_datetime")
    sent_by: str = Column(VARCHAR(20), nullable=True, name="sms_sent_by")
    number: str = Column(VARCHAR(50), nullable=False, name="sms_number")
    message: str = Column(VARCHAR(1600), nullable=False, name="sms_message")
    result: str = Column(VARCHAR(1000), nullable=True, name="sms_result")
    log: str = Column(VARCHAR(10000), nullable=True, name="sms_log")
