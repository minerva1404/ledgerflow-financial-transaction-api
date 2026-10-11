import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
    CheckConstraint(
        "amount > 0",
        name="ck_ledger_entries_amount_positive",
    ),
    CheckConstraint(
        "entry_type IN ('debit', 'credit')",
        name="ck_ledger_entries_type",
    ),
    CheckConstraint(
        "currency ~ '^[A-Z]{3}$'",
        name="ck_ledger_entries_currency_format",
    ),
)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    transfer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transfers.id"), nullable=True, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True
    )
    entry_type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )