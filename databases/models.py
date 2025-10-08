from sqlalchemy import Column, Integer, String, ForeignKey, JSON,Text,DateTime
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm.attributes import flag_modified 

class TeacherInfo(Base):
    __tablename__ = 'teacher_info'

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    email = Column(String(50))


class HistoryUser(Base):
    __tablename__ = 'history_user'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("teacher_info.id"))
    interaction = Column(MutableList.as_mutable(JSON), default=[])