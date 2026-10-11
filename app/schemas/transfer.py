import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransferCreate(BaseModel):
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal = Field(
        gt=0,
        max_digits=19,
        decimal_places=4,
    )


class TransferResponse(BaseModel):
    id: uuid.UUID
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal
    currency: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)