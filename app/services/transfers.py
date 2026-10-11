from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.ledger_entry import LedgerEntry
from app.models.transfer import Transfer
from app.models.user import User


def get_account_balance(db: Session, account_id: UUID) -> Decimal:
    credits = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.entry_type == "credit",
        )
    )

    debits = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.entry_type == "debit",
        )
    )

    return Decimal(str(credits)) - Decimal(str(debits))


def execute_transfer(
    db: Session,
    current_user: User,
    source_account_id: UUID,
    destination_account_id: UUID,
    amount: Decimal,
    idempotency_key: str,
) -> Transfer:
    if source_account_id == destination_account_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source and destination accounts must differ",
        )

    if not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency key cannot be blank",
        )

    try:
        # Serialize transfers involving these accounts in a stable order.
        account_ids = sorted(
            [source_account_id, destination_account_id],
            key=str,
        )

        accounts = db.scalars(
            select(Account)
            .where(
                Account.id.in_(account_ids),
                Account.owner_id == current_user.id,
            )
            .order_by(Account.id)
            .with_for_update()
        ).all()

        account_map = {account.id: account for account in accounts}
        source = account_map.get(source_account_id)
        destination = account_map.get(destination_account_id)

        if source is None or destination is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both accounts were not found",
            )

        existing = db.scalar(
            select(Transfer).where(
                Transfer.owner_id == current_user.id,
                Transfer.idempotency_key == idempotency_key,
            )
        )

        if existing is not None:
            if (
                existing.source_account_id != source_account_id
                or existing.destination_account_id != destination_account_id
                or existing.amount != amount
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key was already used for another request",
                )

            return existing

        if source.status != "active" or destination.status != "active":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Both accounts must be active",
            )

        if source.currency != destination.currency:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Transfers between different currencies are not supported",
            )

        if get_account_balance(db, source.id) < amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient funds",
            )

        transfer = Transfer(
            id=uuid4(),
            owner_id=current_user.id,
            source_account_id=source.id,
            destination_account_id=destination.id,
            amount=amount,
            currency=source.currency,
            status="completed",
            idempotency_key=idempotency_key,
        )
        db.add(transfer)
        db.flush()

        db.add_all(
            [
                LedgerEntry(
                    transfer_id=transfer.id,
                    account_id=source.id,
                    entry_type="debit",
                    amount=amount,
                    currency=source.currency,
                ),
                LedgerEntry(
                    transfer_id=transfer.id,
                    account_id=destination.id,
                    entry_type="credit",
                    amount=amount,
                    currency=source.currency,
                ),
            ]
        )

        db.commit()
        db.refresh(transfer)
        return transfer

    except Exception:
        db.rollback()
        raise