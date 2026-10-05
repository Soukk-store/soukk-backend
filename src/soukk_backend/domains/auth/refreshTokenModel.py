import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from soukk_backend.database import Base


class LoginType(StrEnum):
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Every token created by rotation points at the token it replaced (parent_id).
    # family_id is the first token of the login, so a whole session can be
    # revoked with one UPDATE instead of walking the parent chain.
    family_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)
    # Indexed because deleting a token makes Postgres find its children to set
    # their parent_id to NULL; without it every delete scans the whole table.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), index=True, nullable=True
    )
    login_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Indexed for the nightly cleanup, which finds expired tokens by this column.
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
