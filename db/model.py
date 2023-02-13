from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from .base import Base


class Postcard(Base):
    __tablename__ = 'postcards'
    sender_id = Column(Integer, primary_key=True)
    postcard_message_id = Column(Integer, primary_key=True)
    receiver_id = Column(Integer)
    notify = Column(Boolean)
