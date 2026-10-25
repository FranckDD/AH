# models/report.py
"""Rapports / controle quotidien : controles du jour et reglages de seuils (migration 028)."""
from sqlalchemy import (
    Column, Integer, SmallInteger, Text, Date, DateTime, Boolean, ForeignKey,
    CheckConstraint, UniqueConstraint, Index, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base


class DailyControl(Base):
    __tablename__ = 'daily_controls'
    __table_args__ = (
        UniqueConstraint("business_date", name="daily_controls_business_date_key"),
        CheckConstraint("jsonb_typeof(anomalies) = 'array'", name="daily_controls_anomalies_array_check"),
        CheckConstraint("new_count >= 0", name="daily_controls_new_count_check"),
        CheckConstraint("open_count >= 0", name="daily_controls_open_count_check"),
        CheckConstraint("notify_reason IN ('nouveau', 'rappel')",
                        name="daily_controls_notify_reason_check"),
        Index("idx_daily_controls_business_date", "business_date"),
    )

    id = Column(Integer, primary_key=True)
    business_date = Column(Date, nullable=False)
    # liste d'objets {key, kind, ref, label, detail, first_seen}
    anomalies = Column(JSONB, nullable=False, default=list,
                       server_default=text("'[]'::jsonb"))
    new_count = Column(Integer, nullable=False, default=0, server_default='0')
    open_count = Column(Integer, nullable=False, default=0, server_default='0')
    computed_at = Column(DateTime, nullable=False,
                         server_default=text("(now() AT TIME ZONE 'UTC')"))  # UTC naif
    notified_at = Column(DateTime, nullable=True)
    reminder_sent_at = Column(DateTime, nullable=True)
    recomputed = Column(Boolean, nullable=False, default=False, server_default=text('false'))
    # decision d'envoi prise a l'ecriture (migration 029) : en attente ssi notify_reason non
    # NULL et notified_at NULL ; la relance envoie exactement cette decision
    notify_reason = Column(Text, nullable=True)
    notify_new_count = Column(Integer, nullable=False, default=0, server_default='0')
    notify_open_count = Column(Integer, nullable=False, default=0, server_default='0')


class ReportSettings(Base):
    __tablename__ = 'report_settings'
    __table_args__ = (
        CheckConstraint("id = 1", name="report_settings_single_row_check"),
        CheckConstraint("cancelled_sales_threshold BETWEEN 1 AND 1000",
                        name="report_settings_cancelled_threshold_check"),
        CheckConstraint("adjustment_pending_days BETWEEN 1 AND 365",
                        name="report_settings_adjustment_days_check"),
    )

    id = Column(SmallInteger, primary_key=True)
    cancelled_sales_threshold = Column(Integer, nullable=False, default=3, server_default='3')
    adjustment_pending_days = Column(Integer, nullable=False, default=3, server_default='3')
    updated_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    updated_at = Column(DateTime, nullable=False,
                        server_default=text("(now() AT TIME ZONE 'UTC')"))
