from datetime import datetime
from typing import Optional
from sqlalchemy import Column, ForeignKey, Integer, String, Date, Numeric,  DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from infrastructures.db.base import Base


class Common(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.branch_id"), nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[str] = mapped_column(Text, nullable=False)
    hired_at: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
