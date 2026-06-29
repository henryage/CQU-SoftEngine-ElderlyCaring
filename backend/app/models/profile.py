"""用户画像模型。"""
from datetime import datetime
from sqlalchemy import (
    BigInteger, String, DateTime, JSON, ForeignKey, DECIMAL,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class UserProfile(Base, TimestampMixin):
    """老人健康画像主表。"""

    profile_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id"), unique=True, nullable=False)
    health_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    medication_habits: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lifestyle_pattern: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    overall_weight: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    dimensions = relationship("UserProfileDimension", back_populates="profile", cascade="all, delete-orphan")


class UserProfileDimension(Base, TimestampMixin):
    """画像维度。"""

    dim_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user_profile.profile_id"), nullable=False, index=True)
    dim_code: Mapped[str] = mapped_column(String(32), nullable=False)
    dim_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    weight: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    decay_factor: Mapped[float | None] = mapped_column(DECIMAL(3, 2), nullable=True)

    profile = relationship("UserProfile", back_populates="dimensions")
