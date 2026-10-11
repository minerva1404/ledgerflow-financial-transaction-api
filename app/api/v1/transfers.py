from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.transfer import TransferCreate, TransferResponse
from app.services.transfers import execute_transfer

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post(
    "",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transfer(
    data: TransferCreate,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Transfer:
    return execute_transfer(
        db=db,
        current_user=current_user,
        source_account_id=data.source_account_id,
        destination_account_id=data.destination_account_id,
        amount=data.amount,
        idempotency_key=idempotency_key,
    )