from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.account import Account
from app.models.user import User
from app.schemas.account import AccountCreate, AccountResponse

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = Account(
        owner_id=current_user.id,
        name=data.name.strip(),
        currency=data.currency,
        status="active",
    )

    if not account.name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Account name cannot be blank",
        )

    db.add(account)
    db.commit()
    db.refresh(account)

    return account


@router.get("", response_model=list[AccountResponse])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Account)
        .where(Account.owner_id == current_user.id)
        .order_by(Account.created_at.desc())
    )

    return db.scalars(statement).all()


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Account).where(
        Account.id == account_id,
        Account.owner_id == current_user.id,
    )

    account = db.scalar(statement)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return account