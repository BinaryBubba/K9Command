from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.database import Base


class DailyUpdate(Base):
    __tablename__ = "daily_updates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dog_id = Column(UUID(as_uuid=True), nullable=False)
    booking_id = Column(UUID(as_uuid=True), nullable=True)

    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    approved = Column(Boolean, default=False)

    created_by = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
