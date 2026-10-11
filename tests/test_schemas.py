from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.ledger import FundingRequest
from app.schemas.account import AccountCreate
from app.schemas.transfer import TransferCreate


def test_account_currency_must_be_uppercase():
    with pytest.raises(ValidationError):
        AccountCreate(name="Checking", currency="usd")


def test_funding_amount_must_be_positive():
    assert FundingRequest(amount="25.5000").amount == Decimal("25.5000")
    with pytest.raises(ValidationError):
        FundingRequest(amount="0")


def test_transfer_amount_must_be_positive():
    with pytest.raises(ValidationError):
        TransferCreate(
            source_account_id="00000000-0000-0000-0000-000000000001",
            destination_account_id="00000000-0000-0000-0000-000000000002",
            amount="-1",
        )
