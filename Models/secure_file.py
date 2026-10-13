from sqlalchemy import Column, ForeignKey, Integer, String, TIMESTAMP, func
from sqlalchemy.orm import relationship

from database import Base


class SecureFile(Base):
    __tablename__ = "secure_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="CASCADE"), nullable=True, index=True)
    kind = Column(String(32), nullable=False, index=True)
    original_name = Column(String(255), nullable=False)
    storage_name = Column(String(80), nullable=False, unique=True)
    media_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    owner = relationship("User")
    car = relationship("Car")
