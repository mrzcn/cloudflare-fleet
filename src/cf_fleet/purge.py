"""Cache purge helpers."""

from __future__ import annotations

from cf_fleet.api import api, list_zones


def purge_everything(
    token: str,
    account_id: str | None = None,
    zone_filter: list[str] | None = None,
    dry_run: bool = False,
) -> tuple[list[str], list[dict]]:
    zones = list_zones(token, account_id=account_id)
    if zone_filter:
        wanted = {z.lower() for z in zone_filter}
        zones = [z for z in zones if z["name"].lower() in wanted]

    ok: list[str] = []
    fail: list[dict] = []
    for zone in zones:
        name = zone["name"]
        if dry_run:
            print(f"dry-run purge_everything zone={name}")
            ok.append(name)
            continue
        code, payload = api(
            token,
            "POST",
            f"/zones/{zone['id']}/purge_cache",
            {"purge_everything": True},
        )
        if code == 200 and payload.get("success"):
            print(f"purged zone={name}")
            ok.append(name)
        else:
            err = {"name": name, "http": code, "errors": payload.get("errors")}
            print(f"FAIL purge zone={name} {err}")
            fail.append(err)
    return ok, fail
