"""models/deal.py"""

import enum

from sqlalchemy import Column, Integer, DECIMAL, ForeignKey, TIMESTAMP, Enum as SAEnum, func
from sqlalchemy.orm import relationship

from database import Base


class DealStatus(str, enum.Enum):
    negotiating = "negotiating"
    agreed = "agreed"
    payment_pending = "payment_pending"
    completed = "completed"
    cancelled = "cancelled"


class BrokerageDeal(Base):
    __tablename__ = "brokerage_deals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="RESTRICT"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    inquiry_id = Column(Integer, ForeignKey("inquiries.id", ondelete="SET NULL"), nullable=True)
    agreed_price = Column(DECIMAL(12, 2), nullable=False)
    commission_rate = Column(DECIMAL(5, 2), nullable=False)
    commission_amount = Column(DECIMAL(12, 2), nullable=False)
    status = Column(SAEnum(DealStatus), nullable=False, default=DealStatus.negotiating)
    closed_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    car = relationship("Car", back_populates="brokerage_deals")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])
    inquiry = relationship("Inquiry", back_populates="brokerage_deal")

    def __repr__(self):
        return f"<BrokerageDeal id={self.id} car_id={self.car_id} status={self.status} closed_at={self.closed_at}>"