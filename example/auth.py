from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class User:
    username: str
    password: str


# Tiny demo “database”.
_USERS: dict[str, User] = {
    "alice": User(username="alice", password="".join(["s", "e", "c", "r", "e", "t"])),
}


def authenticate(username: str, password: str) -> bool:
    user = _USERS.get(username)
    if user is None:
        return False
    # BUG: uses identity comparison instead of value equality.
    return user.password is password

