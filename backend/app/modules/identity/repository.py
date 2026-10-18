"""Database access for users."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.models import UserAccount


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: uuid.UUID) -> UserAccount | None:
        return self._session.get(UserAccount, user_id)

    def by_username(self, username: str) -> UserAccount | None:
        return self._session.scalar(select(UserAccount).where(UserAccount.username == username))

    def active(self) -> list[UserAccount]:
        query = select(UserAccount).where(UserAccount.active).order_by(UserAccount.display_name)
        return list(self._session.scalars(query))

    def by_ids(self, user_ids: set[uuid.UUID]) -> list[UserAccount]:
        if not user_ids:
            return []
        return list(self._session.scalars(select(UserAccount).where(UserAccount.id.in_(user_ids))))

    def add(self, user: UserAccount) -> UserAccount:
        self._session.add(user)
        self._session.flush()
        return user
