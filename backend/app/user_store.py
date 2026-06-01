from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any


STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "user_store.json"
_STORE_LOCK = Lock()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _empty_store() -> dict[str, list[dict[str, Any]]]:
    return {"users": [], "tokens": [], "teams": []}


def _store_path(path: Path | None = None) -> Path:
    return path or STORE_PATH


def _read_store(path: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    resolved_path = _store_path(path)
    if not resolved_path.exists():
        return _empty_store()

    try:
        payload = json.loads(resolved_path.read_text())
    except json.JSONDecodeError:
        return _empty_store()

    return {
        "users": payload.get("users", []),
        "tokens": payload.get("tokens", []),
        "teams": payload.get("teams", []),
    }


def _write_store(store: dict[str, list[dict[str, Any]]], path: Path | None = None) -> None:
    resolved_path = _store_path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(json.dumps(store, indent=2, sort_keys=True))


def _update_store(
    callback: Callable[[dict[str, list[dict[str, Any]]]], Any],
    path: Path | None = None,
) -> Any:
    with _STORE_LOCK:
        store = _read_store(path)
        result = callback(store)
        _write_store(store, path)
        return result


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def _public_user(record: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(record["id"]),
        "email": str(record["email"]),
        "display_name": str(record["display_name"]),
    }


def create_user(email: str, password: str, display_name: str | None = None) -> tuple[dict[str, str], str]:
    normalized_email = _normalize_email(email)
    normalized_name = (display_name or normalized_email.split("@")[0]).strip()

    def _create(store: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, str], str]:
        for existing in store["users"]:
            if existing["email"] == normalized_email:
                raise ValueError("User already exists")

        now = _utc_now()
        salt = secrets.token_hex(16)
        user_id = secrets.token_hex(8)
        user = {
            "id": user_id,
            "email": normalized_email,
            "display_name": normalized_name,
            "salt": salt,
            "password_hash": _hash_password(password, salt),
            "created_at": now,
        }
        token = secrets.token_urlsafe(32)
        store["users"].append(user)
        store["tokens"].append({"token": token, "user_id": user_id, "created_at": now})
        return _public_user(user), token

    return _update_store(_create)


def authenticate_user(email: str, password: str) -> tuple[dict[str, str], str]:
    normalized_email = _normalize_email(email)

    def _authenticate(store: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, str], str]:
        for existing in store["users"]:
            if existing["email"] != normalized_email:
                continue

            if existing["password_hash"] != _hash_password(password, existing["salt"]):
                break

            token = secrets.token_urlsafe(32)
            store["tokens"].append(
                {
                    "token": token,
                    "user_id": existing["id"],
                    "created_at": _utc_now(),
                }
            )
            return _public_user(existing), token

        raise ValueError("Invalid email or password")

    return _update_store(_authenticate)


def get_user_for_token(token: str) -> dict[str, str] | None:
    store = _read_store()
    token_record = next((entry for entry in store["tokens"] if entry["token"] == token), None)
    if token_record is None:
        return None

    user_record = next((user for user in store["users"] if user["id"] == token_record["user_id"]), None)
    if user_record is None:
        return None

    return _public_user(user_record)


def list_saved_teams(user_id: str) -> list[dict[str, Any]]:
    store = _read_store()
    teams = [team for team in store["teams"] if team["user_id"] == user_id]
    teams.sort(key=lambda team: team["updated_at"], reverse=True)
    return [
        {
            "id": team["id"],
            "name": team["name"],
            "notes": team.get("notes"),
            "created_at": team["created_at"],
            "updated_at": team["updated_at"],
            "team": team["team"],
        }
        for team in teams
    ]


def save_team(user_id: str, name: str, notes: str | None, team: dict[str, Any]) -> dict[str, Any]:
    cleaned_name = name.strip()
    cleaned_notes = notes.strip() if notes else None

    def _save(store: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        now = _utc_now()
        saved_team = {
            "id": secrets.token_hex(6),
            "user_id": user_id,
            "name": cleaned_name,
            "notes": cleaned_notes,
            "created_at": now,
            "updated_at": now,
            "team": team,
        }
        store["teams"].append(saved_team)
        return {
            "id": saved_team["id"],
            "name": saved_team["name"],
            "notes": saved_team["notes"],
            "created_at": saved_team["created_at"],
            "updated_at": saved_team["updated_at"],
            "team": saved_team["team"],
        }

    return _update_store(_save)
