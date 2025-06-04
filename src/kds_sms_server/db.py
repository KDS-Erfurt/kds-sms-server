from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, Enum, VARCHAR

from wiederverwendbar.singleton import Singleton
from wiederverwendbar.sqlalchemy import SqlalchemyDb, EnumValueStr

from kds_sms_server.settings import settings


class Db(SqlalchemyDb, metaclass=Singleton):
    ...


def db() -> Db:
    try:
        return Singleton.get_by_type(Db)
    except RuntimeError:
        return Db(settings=settings, init=True)


class MessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    ERROR = "error"


class Messages(db().Base):
    __tablename__ = "messages"
    __str_columns__ = ["id", "status", "received_datetime", "send_datetime", "number"]

    id: int = Column(Integer(), primary_key=True, autoincrement=True, name="message_id")
    status: MessageStatus = Column(EnumValueStr(MessageStatus), nullable=False, name="message_status")
    received_datetime: datetime = Column(DateTime(), nullable=False, name="message_received_datetime")
    send_datetime: datetime = Column(DateTime(), nullable=True, name="message_send_datetime")
    number: str = Column(VARCHAR(50), nullable=False, name="message_number")
    text: str = Column(VARCHAR(1600), nullable=False, name="message_text")
