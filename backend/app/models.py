from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)   # "fan" | "light"
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    wattage: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_changed_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    events: Mapped[list["StateEvent"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class StateEvent(Base):
    __tablename__ = "state_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    new_status: Mapped[bool] = mapped_column(Boolean, nullable=False)
    changed_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    device: Mapped["Device"] = relationship(back_populates="events")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)   # after_hours | marathon_room | high_load
    room: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
