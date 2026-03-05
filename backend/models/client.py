"""
Client & related models — SQLAlchemy ORM
"""

from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from db.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, index=True)
    phone = Column(String(20))
    dob = Column(Date)
    pan = Column(String(10))
    aadhaar_last4 = Column(String(4))
    address = Column(Text)
    segment = Column(String(50))  # UHNI, HNI, Mass Affluent
    risk_profile = Column(String(50))  # Conservative, Moderate, Aggressive
    kyc_status = Column(String(20), default="pending")  # pending, verified, flagged, incomplete
    annual_income = Column(Float, default=0)
    aum = Column(Float, default=0)
    rm_name = Column(String(200), default="Vikram Sharma")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    holdings = relationship("Holding", back_populates="client", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="client", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="client", cascade="all, delete-orphan")
    interactions = relationship("Interaction", back_populates="client", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    instrument_name = Column(String(200), nullable=False)
    instrument_type = Column(String(50))  # Equity, MF, Bond, Gold, Alternate
    quantity = Column(Float, default=0)
    purchase_price = Column(Float, default=0)
    current_price = Column(Float, default=0)
    purchase_date = Column(Date)

    client = relationship("Client", back_populates="holdings")

    @property
    def invested_value(self) -> float:
        return self.quantity * self.purchase_price

    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return self.current_value - self.invested_value

    @property
    def return_pct(self) -> float:
        if self.invested_value == 0:
            return 0.0
        return (self.unrealized_pnl / self.invested_value) * 100


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    name = Column(String(200), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0)
    target_year = Column(Integer, nullable=False)

    client = relationship("Client", back_populates="goals")

    @property
    def progress_pct(self) -> float:
        if self.target_amount == 0:
            return 0.0
        return min((self.current_amount / self.target_amount) * 100, 100.0)
