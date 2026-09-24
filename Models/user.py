"""models/user.py"""

from .base_enum import StrEnum

from sqlalchemy import Boolean, Column, Enum as SAEnum, Integer, String, TIMESTAMP, func
from sqlalchemy.orm import relationship

from database import Base


class UserRole(StrEnum):
    buyer = "buyer"
    seller = "seller"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.buyer)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    cars_listed = relationship("Car", back_populates="seller", foreign_keys="Car.seller_id")
    inquiries_made = relationship("Inquiry", back_populates="buyer", foreign_keys="Inquiry.buyer_id")
    inquiries_received = relationship("Inquiry", back_populates="seller", foreign_keys="Inquiry.seller_id")
    messages_sent = relationship("Message", back_populates="sender")

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"