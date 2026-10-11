from fastapi import FastAPI
from app.api.v1.ledger import router as ledger_router
from sqlalchemy import text
from app.api.v1.accounts import router as accounts_router
from app.api.v1.auth import router as auth_router
from app.db.session import engine
from app.api.v1.transfers import router as transfers_router

app = FastAPI(
    title="LedgerFlow",
    description=(
        "Financial transaction and reconciliation API "
        "with authentication, account ownership, and a ledger."
    ),
    version="1.0.0",
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(accounts_router, prefix="/api/v1")
app.include_router(transfers_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from None

app.include_router(ledger_router, prefix="/api/v1")
