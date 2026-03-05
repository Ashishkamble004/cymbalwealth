"""
Transaction & Interaction models — SQLAlchemy ORM
"""

from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    instrument_name = Column(String(200), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # BUY, SELL, SIP, DIVIDEND, REDEMPTION
    quantity = Column(Float, default=0)
    price = Column(Float, default=0)
    amount = Column(Float, default=0)
    transaction_date = Column(Date, nullable=False)
    notes = Column(Text)

    client = relationship("Client", back_populates="transactions")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    interaction_type = Column(String(50))  # call, meeting, email, voice_session
    summary = Column(Text)
    interaction_date = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="interactions")
