"""Apply policy settings across zones."""

from __future__ import annotations

from pathlib import Path

from cf_fleet.api import get_setting, list_zones, set_setting
from cf_fleet.yaml_lite import load_yaml

TLS_ORDER = {"1.0": 0, "1.1": 1, "1.2": 2, "1.3": 3}


def load_policy(path: Path) -> dict:
    data = load_yaml(path)
    if "settings" not in data or not isinstance(data["settings"], dict):
        raise ValueError(f"{path}: missing settings mapping")
    return data


def _should_raise_tls(current: object, floor: str) -> bool:
    return TLS_ORDER.get(str(current), -1) < TLS_ORDER.get(floor, 2)


def apply_baseline(
    token: str,
    policy_path: Path,
    account_id: str | None = None,
    zone_filter: list[str] | None = None,
    dry_run: bool = False,
) -> tuple[list[dict], list[dict]]:
    policy = load_policy(policy_path)
    settings: dict = policy["settings"]
    tls_floor = str(policy.get("min_tls_floor") or settings.get("min_tls_version") or "1.2")

    zones = list_zones(token, account_id=account_id)
    if zone_filter:
        wanted = {z.lower() for z in zone_filter}
        zones = [z for z in zones if z["name"].lower() in wanted]

    changes: list[dict] = []
    failures: list[dict] = []

    for zone in zones:
        zid = zone["id"]
        zname = zone["name"]
        for key, desired in settings.items():
            try:
                current = get_setting(token, zid, key)
            except RuntimeError as exc:
                failures.append({"zone": zname, "setting": key, "error": str(exc)})
                continue

            if key == "min_tls_version":
                if not _should_raise_tls(current, tls_floor):
                    continue
                desired = tls_floor
            elif current == desired:
                continue

            entry = {
                "zone": zname,
                "setting": key,
                "from": current,
                "to": desired,
            }
            if dry_run:
                print(f"dry-run {zname} {key}: {current!r} → {desired!r}")
                changes.append(entry)
                continue
            try:
                set_setting(token, zid, key, desired)
                print(f"ok {zname} {key}: {current!r} → {desired!r}")
                changes.append(entry)
            except RuntimeError as exc:
                failures.append({"zone": zname, "setting": key, "error": str(exc)})

    return changes, failures


def set_one(
    token: str,
    setting: str,
    value: object,
    account_id: str | None = None,
    zone_filter: list[str] | None = None,
    dry_run: bool = False,
) -> tuple[list[dict], list[dict]]:
    # Coerce numeric TTL strings
    if setting == "browser_cache_ttl" and isinstance(value, str) and value.isdigit():
        value = int(value)

    zones = list_zones(token, account_id=account_id)
    if zone_filter:
        wanted = {z.lower() for z in zone_filter}
        zones = [z for z in zones if z["name"].lower() in wanted]

    ok: list[dict] = []
    fail: list[dict] = []
    for zone in zones:
        try:
            current = get_setting(token, zone["id"], setting)
            if current == value:
                print(f"skip {zone['name']} {setting} already {value!r}")
                continue
            if dry_run:
                print(f"dry-run {zone['name']} {setting}: {current!r} → {value!r}")
                ok.append({"zone": zone["name"], "from": current, "to": value})
                continue
            set_setting(token, zone["id"], setting, value)
            print(f"ok {zone['name']} {setting}: {current!r} → {value!r}")
            ok.append({"zone": zone["name"], "from": current, "to": value})
        except RuntimeError as exc:
            fail.append({"zone": zone["name"], "error": str(exc)})
            print(f"FAIL {zone['name']}: {exc}")
    return ok, fail
