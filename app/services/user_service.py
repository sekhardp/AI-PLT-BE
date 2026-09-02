import logging
import uuid
from typing import Any, List, Optional
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CreditTransaction, User

logger = logging.getLogger(__name__)


class UserService:
    """
    Service managing User profiles, Role-Based Access, and Credit Bank balances.
    """

    async def get_or_create_user(
        self,
        email: str,
        username: str = "",
        role: str = "user",
        db: Optional[AsyncSession] = None,
    ) -> User:
        """Fetch an existing user or create a new one with initial credit bank allocation."""
        if not db:
            raise ValueError("Database session required")

        norm_email = email.lower().strip()
        user = await db.scalar(select(User).where(User.email == norm_email))
        if user:
            return user

        is_admin = "admin" in norm_email or role == "admin"
        assigned_role = "admin" if is_admin else "user"
        initial_credits = 100 if is_admin else 20
        display_name = username or (norm_email.split("@")[0] if not is_admin else "Admin Manager")

        user = User(
            username=display_name,
            email=norm_email,
            role=assigned_role,
            credits=initial_credits,
            tokens_used=0,
        )
        db.add(user)
        await db.flush()

        # Log initial welcome credit allocation in ledger
        tx = CreditTransaction(
            user_id=user.id,
            amount=initial_credits,
            tokens_charged=0,
            balance_after=initial_credits,
            action_type="welcome_grant",
            reason="Welcome Credit Grant",
            metadata_json={"role": assigned_role},
        )
        db.add(tx)
        await db.commit()
        await db.refresh(user)
        logger.info("user_created: %s (id=%s), role=%s, credits=%s", norm_email, user.id, assigned_role, initial_credits)
        return user

    async def list_users(self, db: AsyncSession) -> List[User]:
        """List all users in the platform."""
        result = await db.scalars(select(User).order_by(User.created_at.asc()))
        return list(result.all())

    async def get_user_by_email(self, email: str, db: AsyncSession) -> Optional[User]:
        """Fetch user by email."""
        norm_email = email.lower().strip()
        return await db.scalar(select(User).where(User.email == norm_email))

    async def get_user_by_id(self, user_id: uuid.UUID | str, db: AsyncSession) -> Optional[User]:
        """Fetch user by primary key UUID."""
        try:
            uid = uuid.UUID(str(user_id).strip()) if isinstance(user_id, str) else user_id
            return await db.scalar(select(User).where(User.id == uid))
        except (ValueError, TypeError):
            return None

    async def resolve_user(self, identifier: Any, db: AsyncSession) -> Optional[User]:
        """
        Resolve a User object given either UUID, UUID string, or email address.
        """
        if not identifier or not db:
            return None
        ident_str = str(identifier).strip()
        if not ident_str:
            return None

        # 1. Try resolving by UUID
        try:
            uid = uuid.UUID(ident_str)
            user = await self.get_user_by_id(uid, db)
            if user:
                return user
        except ValueError:
            pass

        # 2. Try resolving by email
        return await self.get_user_by_email(ident_str, db)

    async def is_admin_user(self, identifier: Any, db: AsyncSession) -> bool:
        """Check if an identifier (UUID or email) corresponds to an admin user."""
        if not identifier or not db:
            return False
        ident_str = str(identifier).strip().lower()
        if "admin" in ident_str:
            return True
        user = await self.resolve_user(identifier, db)
        if user and user.role == "admin":
            return True
        return False

    async def update_credits(self, email: str, new_credits: int, db: AsyncSession) -> User:
        """Admin top-up or manual credit update."""
        user = await self.resolve_user(email, db)
        if not user:
            raise ValueError(f"User '{email}' not found")

        diff = new_credits - user.credits
        user.credits = max(0, new_credits)
        user.version += 1

        tx = CreditTransaction(
            user_id=user.id,
            amount=diff,
            tokens_charged=0,
            balance_after=user.credits,
            action_type="admin_adjustment",
            reason="Admin Credit Adjustment",
            metadata_json={"previous_balance": user.credits - diff, "new_balance": user.credits},
        )
        db.add(tx)
        await db.commit()
        await db.refresh(user)
        logger.info("user_credits_updated: %s, new_credits=%s, delta=%s", email, new_credits, diff)
        return user

    async def deduct_credit(
        self,
        email: str,
        amount: int = 1,
        tokens_used: int = 0,
        reason: str = "Chat Execution",
        action_type: str = "chat_execution",
        metadata: Optional[dict] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[User]:
        """Deduct credits on prompt completion and log tokens in Credit Bank ledger atomically."""
        if not db:
            return None

        user = await self.resolve_user(email, db)
        if not user:
            return None

        deduction = 0 if user.role == "admin" else amount
        new_balance = max(0, user.credits - deduction)
        user.credits = new_balance
        user.tokens_used += tokens_used
        user.version += 1

        tx = CreditTransaction(
            user_id=user.id,
            amount=-deduction,
            tokens_charged=tokens_used,
            balance_after=new_balance,
            action_type=action_type,
            reason=reason,
            metadata_json=metadata or {},
        )
        db.add(tx)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_transactions(self, email: str, db: AsyncSession) -> List[CreditTransaction]:
        """Get credit ledger history for user."""
        user = await self.resolve_user(email, db)
        if not user:
            return []

        result = await db.scalars(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user.id)
            .order_by(desc(CreditTransaction.created_at))
            .limit(50)
        )
        return list(result.all())


user_service = UserService()
