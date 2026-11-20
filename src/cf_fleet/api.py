"""Minimal Cloudflare API client (stdlib only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.cloudflare.com/client/v4"


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def resolve_token(env_file: Path | None = None) -> str:
    token = (os.environ.get("CF_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()
    if env_file is None:
        env_file = Path.cwd() / ".env"
    if not token and env_file.is_file():
        token = (load_env(env_file).get("CF_API_TOKEN") or "").strip()
    if not token or token.endswith("REPLACE_ME"):
        raise SystemExit(
            "Missing CF_API_TOKEN. Copy .env.example → .env and set a real API token "
            "(or export CF_API_TOKEN)."
        )
    return token


def resolve_account_id(env_file: Path | None = None) -> str | None:
    account = (os.environ.get("CF_ACCOUNT_ID") or "").strip() or None
    if account:
        return account
    if env_file is None:
        env_file = Path.cwd() / ".env"
    if env_file.is_file():
        account = (load_env(env_file).get("CF_ACCOUNT_ID") or "").strip() or None
    return account


def api(token: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"success": False, "errors": [{"message": raw}]}
        return e.code, payload


def list_zones(token: str, account_id: str | None = None, name: str | None = None) -> list[dict]:
    zones: list[dict] = []
    page = 1
    while True:
        params: dict[str, str | int] = {"per_page": 50, "page": page}
        if account_id:
            params["account.id"] = account_id
        if name:
            params["name"] = name
        query = urllib.parse.urlencode(params)
        code, payload = api(token, "GET", f"/zones?{query}")
        if code != 200 or not payload.get("success"):
            raise RuntimeError(f"list zones failed http={code} errors={payload.get('errors')}")
        zones.extend(payload.get("result") or [])
        info = payload.get("result_info") or {}
        total_pages = int(info.get("total_pages") or 1)
        if page >= total_pages:
            break
        page += 1
    return zones


def get_setting(token: str, zone_id: str, setting: str) -> object:
    code, payload = api(token, "GET", f"/zones/{zone_id}/settings/{setting}")
    if code != 200 or not payload.get("success"):
        raise RuntimeError(
            f"get setting {setting} failed http={code} errors={payload.get('errors')}"
        )
    return (payload.get("result") or {}).get("value")


def set_setting(token: str, zone_id: str, setting: str, value: object) -> None:
    code, payload = api(
        token,
        "PATCH",
        f"/zones/{zone_id}/settings/{setting}",
        {"value": value},
    )
    if code != 200 or not payload.get("success"):
        raise RuntimeError(
            f"set setting {setting}={value!r} failed http={code} errors={payload.get('errors')}"
        )


def get_all_settings(token: str, zone_id: str) -> dict[str, object]:
    code, payload = api(token, "GET", f"/zones/{zone_id}/settings")
    if code != 200 or not payload.get("success"):
        raise RuntimeError(f"list settings failed http={code} errors={payload.get('errors')}")
    out: dict[str, object] = {}
    for item in payload.get("result") or []:
        out[item["id"]] = item.get("value")
    return out
