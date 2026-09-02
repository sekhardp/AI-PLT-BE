import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users & Credit Bank"])


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    username: Optional[str] = Field(None, description="Optional display name")
    password: Optional[str] = Field("", description="User password")


class UpdateCreditsRequest(BaseModel):
    credits: int = Field(..., ge=0, description="New credit balance")


class DeductCreditRequest(BaseModel):
    amount: int = Field(1, ge=1, description="Credits to deduct")
    tokens: int = Field(0, ge=0, description="Tokens charged")
    reason: Optional[str] = Field("Chat Execution", description="Transaction reason")


@router.post("/login")
async def login_user(req: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    """Authenticate or register user in Cloud SQL and return active balance."""
    try:
        user = await user_service.get_or_create_user(
            email=req.email,
            username=req.username or "",
            db=db,
        )
        return {
            "status": "ok",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "credits": user.credits,
                "tokensUsed": user.tokens_used,
            },
        }
    except Exception as e:
        logger.error("User login/registration failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_all_users(db: AsyncSession = Depends(get_db_session)):
    """Retrieve all users and credit balances for Admin Dashboard."""
    users = await user_service.list_users(db)
    return {
        "users": [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "credits": u.credits,
                "tokensUsed": u.tokens_used,
                "createdAt": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    }


@router.get("/{email}")
async def get_user_profile(email: str, db: AsyncSession = Depends(get_db_session)):
    """Fetch user profile and current Credit Bank balance."""
    user = await user_service.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "credits": user.credits,
            "tokensUsed": user.tokens_used,
        }
    }


@router.patch("/{email}/credits")
async def update_user_credits(
    email: str,
    req: UpdateCreditsRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Admin grants or recharges user credits."""
    try:
        user = await user_service.update_credits(email=email, new_credits=req.credits, db=db)
        return {
            "status": "ok",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "credits": user.credits,
                "tokensUsed": user.tokens_used,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to update credits: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{email}/deduct")
async def deduct_user_credits(
    email: str,
    req: DeductCreditRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Deduct credit and record token usage in Cloud SQL ledger."""
    user = await user_service.deduct_credit(
        email=email,
        amount=req.amount,
        tokens_used=req.tokens,
        reason=req.reason or "Chat Execution",
        db=db,
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "status": "ok",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "credits": user.credits,
            "tokensUsed": user.tokens_used,
        },
    }


@router.get("/{email}/transactions")
async def get_user_transactions(email: str, db: AsyncSession = Depends(get_db_session)):
    """Retrieve audit trail of credit deductions and recharges."""
    txs = await user_service.get_transactions(email, db)
    return {
        "transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "tokensCharged": t.tokens_charged,
                "balanceAfter": t.balance_after,
                "actionType": t.action_type,
                "reason": t.reason,
                "createdAt": t.created_at.isoformat() if t.created_at else None,
            }
            for t in txs
        ]
    }
