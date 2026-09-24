"""models/car.py"""

from .base_enum import StrEnum

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DECIMAL,
    ForeignKey, TIMESTAMP, Enum as SAEnum, func,
)
from sqlalchemy.orm import relationship

from database import Base


class FuelType(StrEnum):
    petrol = "petrol"
    diesel = "diesel"
    hybrid = "hybrid"
    electric = "electric"


class Transmission(StrEnum):
    manual = "manual"
    automatic = "automatic"


class CarStatus(StrEnum):
    draft = "draft"
    active = "active"
    pending_sale = "pending_sale"
    sold = "sold"
    removed = "removed"


class VerificationStatus(StrEnum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    mileage = Column(Integer, nullable=False)
    price = Column(DECIMAL(12, 2), nullable=False)
    fuel_type = Column(SAEnum(FuelType), nullable=False)
    transmission = Column(SAEnum(Transmission), nullable=False)
    condition_notes = Column(Text)
    location = Column(String(150))
    status = Column(SAEnum(CarStatus), nullable=False, default=CarStatus.draft)
    verification_status = Column(
        SAEnum(VerificationStatus), nullable=False, default=VerificationStatus.unverified
    )
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    seller = relationship("User", back_populates="cars_listed", foreign_keys=[seller_id])
    images = relationship("CarImage", back_populates="car", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="car", cascade="all, delete-orphan")
    inquiries = relationship("Inquiry", back_populates="car")
    brokerage_deals = relationship("BrokerageDeal", back_populates="car")

    def __repr__(self):
        return f"<Car id={self.id} {self.year} {self.make} {self.model}>"


class CarImage(Base):
    __tablename__ = "car_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(255), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    uploaded_at = Column(TIMESTAMP, server_default=func.now())

    car = relationship("Car", back_populates="images")

    def __repr__(self):
        return f"<CarImage id={self.id} car_id={self.car_id}>"