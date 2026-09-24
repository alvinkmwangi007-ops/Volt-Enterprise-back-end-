"""models/inquiry.py"""

from .base_enum import StrEnum

from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, Enum as SAEnum, func
from sqlalchemy.orm import relationship

from database import Base


class InquiryStatus(StrEnum):
    open = "open"
    in_discussion = "in_discussion"
    closed = "closed"


class Inquiry(Base):
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="CASCADE"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(SAEnum(InquiryStatus), nullable=False, default=InquiryStatus.open)
    created_at = Column(TIMESTAMP, server_default=func.now())

    car = relationship("Car", back_populates="inquiries")
    buyer = relationship("User", back_populates="inquiries_made", foreign_keys=[buyer_id])
    seller = relationship("User", back_populates="inquiries_received", foreign_keys=[seller_id])
    messages = relationship("Message", back_populates="inquiry", cascade="all, delete-orphan")
    brokerage_deal = relationship("BrokerageDeal", back_populates="inquiry", uselist=False)

    def __repr__(self):
        return f"<Inquiry id={self.id} car_id={self.car_id} status={self.status}>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inquiry_id = Column(Integer, ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = Column(Text, nullable=False)
    sent_at = Column(TIMESTAMP, server_default=func.now())

    inquiry = relationship("Inquiry", back_populates="messages")
    sender = relationship("User", back_populates="messages_sent")

    def __repr__(self):
        return f"<Message id={self.id} inquiry_id={self.inquiry_id} sender_id={self.sender_id}>"