from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.account import Account
from app.models.ledger_entry import LedgerEntry
from app.models.transfer import Transfer
from app.models.user import User

router = APIRouter(tags=["Ledger"])


class FundingRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=19, decimal_places=4)


def balance_for(db: Session, account_id: UUID) -> Decimal:
    value = db.scalar(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.entry_type == "credit", LedgerEntry.amount),
                        else_=-LedgerEntry.amount,
                    )
                ),
                0,
            )
        ).where(LedgerEntry.account_id == account_id)
    )
    return Decimal(str(value))


@router.post(
    "/accounts/{account_id}/fund",
    status_code=status.HTTP_201_CREATED,
)
def fund_account(
    account_id: UUID,
    data: FundingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        account = db.scalar(
            select(Account)
            .where(
                Account.id == account_id,
                Account.owner_id == current_user.id,
            )
            .with_for_update()
        )
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        if account.status != "active":
            raise HTTPException(status_code=409, detail="Account is not active")
        if account.opening_funded:
            raise HTTPException(
                status_code=409,
                detail="Opening funding has already been recorded for this account",
            )

        # This is simulated opening funding for a portfolio project,
        # not a real payment or external deposit.
        db.add(
            LedgerEntry(
                transfer_id=None,
                account_id=account.id,
                entry_type="credit",
                amount=data.amount,
                currency=account.currency,
            )
        )
        account.opening_funded = True
        db.commit()
        return {
            "account_id": str(account.id),
            "funded_amount": str(data.amount),
            "currency": account.currency,
            "balance": str(balance_for(db, account.id)),
            "note": "Simulated opening funding; no real money was moved.",
        }
    except Exception:
        db.rollback()
        raise


@router.get("/accounts/{account_id}/balance")
def read_balance(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = db.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.owner_id == current_user.id,
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    return {
        "account_id": str(account.id),
        "currency": account.currency,
        "balance": str(balance_for(db, account.id)),
    }


@router.get("/ledger/entries")
def list_ledger_entries(
    account_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(LedgerEntry)
        .join(Account, LedgerEntry.account_id == Account.id)
        .where(Account.owner_id == current_user.id)
        .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id)
        .limit(limit)
        .offset(offset)
    )
    if account_id is not None:
        statement = statement.where(LedgerEntry.account_id == account_id)

    entries = db.scalars(statement).all()
    return [
        {
            "id": str(item.id),
            "transfer_id": str(item.transfer_id) if item.transfer_id else None,
            "account_id": str(item.account_id),
            "entry_type": item.entry_type,
            "amount": str(item.amount),
            "currency": item.currency,
            "created_at": item.created_at,
        }
        for item in entries
    ]


@router.get("/ledger/reconcile")
def reconcile_ledger(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transfers = db.scalars(
        select(Transfer)
        .where(Transfer.owner_id == current_user.id)
        .order_by(Transfer.created_at)
    ).all()

    discrepancies = []
    for transfer in transfers:
        entries = db.scalars(
            select(LedgerEntry).where(
                LedgerEntry.transfer_id == transfer.id
            )
        ).all()
        debits = [e for e in entries if e.entry_type == "debit"]
        credits = [e for e in entries if e.entry_type == "credit"]
        debit_total = sum((e.amount for e in debits), Decimal("0"))
        credit_total = sum((e.amount for e in credits), Decimal("0"))

        if (
            len(entries) != 2
            or len(debits) != 1
            or len(credits) != 1
            or debit_total != credit_total
            or debit_total != transfer.amount
            or any(e.currency != transfer.currency for e in entries)
        ):
            discrepancies.append({
                "transfer_id": str(transfer.id),
                "entry_count": len(entries),
                "debit_total": str(debit_total),
                "credit_total": str(credit_total),
            })

    return {
        "transfers_checked": len(transfers),
        "balanced": not discrepancies,
        "discrepancies": discrepancies,
    }
