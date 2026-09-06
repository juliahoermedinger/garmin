from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    garmin_link: Mapped["GarminLink"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    shoes: Mapped[list["Shoe"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    runs: Mapped[list["Run"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class GarminLink(Base):
    __tablename__ = "garmin_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    encrypted_token_blob: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="connected")  # connected | needs_reauth
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="garmin_link")


class Shoe(Base):
    __tablename__ = "shoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    retired: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="shoes")
    runs: Mapped[list["Run"]] = relationship(back_populates="shoe")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (UniqueConstraint("user_id", "garmin_activity_id", name="uq_user_activity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    garmin_activity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    shoe_id: Mapped[int | None] = mapped_column(ForeignKey("shoes.id"), nullable=True)

    # Naive local time as reported by the watch/Garmin (not UTC) - there is no
    # reliable timezone info attached to it, so we store it as-is for display.
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    distance_meters: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    avg_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="runs")
    shoe: Mapped["Shoe | None"] = relationship(back_populates="runs")

    @property
    def avg_pace_per_km(self) -> float | None:
        """Seconds per kilometer, or None if distance is zero."""
        if not self.distance_meters:
            return None
        km = self.distance_meters / 1000
        return self.duration_seconds / km
