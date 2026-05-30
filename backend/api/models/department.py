from datetime import datetime
from typing import Optional
from sqlalchemy import Column, ForeignKey, Integer, String, Date, Numeric,  DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from infrastructures.db.base import Base


class Common(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("branches.branch_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


