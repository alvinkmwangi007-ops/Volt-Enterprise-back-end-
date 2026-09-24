"""models/inspection.py"""

from .base_enum import StrEnum

from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    ForeignKey, TIMESTAMP, Enum as SAEnum, func,
)
from sqlalchemy.orm import relationship

from database import Base


class InspectionStatus(StrEnum):
    requested = "requested"
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class InspectionResult(StrEnum):
    pass_ = "pass"
    fail = "fail"
    flagged = "flagged"


class InspectionPartner(Base):
    __tablename__ = "inspection_partners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    contact_email = Column(String(150))
    contact_phone = Column(String(20))
    api_endpoint = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=True)

    inspections = relationship("Inspection", back_populates="partner")

    def __repr__(self):
        return f"<InspectionPartner id={self.id} name={self.name}>"


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="CASCADE"), nullable=False)
    partner_id = Column(Integer, ForeignKey("inspection_partners.id", ondelete="RESTRICT"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status = Column(SAEnum(InspectionStatus), nullable=False, default=InspectionStatus.requested)
    scheduled_at = Column(TIMESTAMP, nullable=True)
    completed_at = Column(TIMESTAMP, nullable=True)
    report_url = Column(String(255))
    result = Column(SAEnum(InspectionResult), nullable=True)
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    car = relationship("Car", back_populates="inspections")
    partner = relationship("InspectionPartner", back_populates="inspections")
    requester = relationship("User", foreign_keys=[requested_by])

    def __repr__(self):
        return f"<Inspection id={self.id} car_id={self.car_id} status={self.status}>"