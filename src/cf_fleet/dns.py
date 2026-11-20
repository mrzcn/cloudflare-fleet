"""Targeted DNS helpers."""

from __future__ import annotations

import urllib.parse

from cf_fleet.api import api, list_zones


def proxy_apex(
    token: str,
    zone_name: str,
    dry_run: bool = False,
) -> dict:
    zones = list_zones(token, name=zone_name)
    match = [z for z in zones if z["name"].lower() == zone_name.lower()]
    if not match:
        raise RuntimeError(f"zone not found: {zone_name}")
    zone = match[0]
    zid = zone["id"]

    updated: list[dict] = []
    for rtype in ("A", "AAAA"):
        query = urllib.parse.urlencode(
            {"name": zone["name"], "type": rtype, "per_page": 100}
        )
        code, payload = api(token, "GET", f"/zones/{zid}/dns_records?{query}")
        if code != 200 or not payload.get("success"):
            raise RuntimeError(
                f"list DNS {rtype} failed http={code} errors={payload.get('errors')}"
            )
        for record in payload.get("result") or []:
            if record.get("name") != zone["name"]:
                continue
            if record.get("proxied"):
                updated.append(
                    {
                        "type": rtype,
                        "id": record["id"],
                        "already_proxied": True,
                        # content intentionally omitted from success path prints for safer logs
                    }
                )
                continue
            body = {
                "type": rtype,
                "name": record["name"],
                "content": record["content"],
                "proxied": True,
                "ttl": 1,
            }
            if dry_run:
                print(f"dry-run proxy apex {zone_name} {rtype} id={record['id']}")
                updated.append({"type": rtype, "id": record["id"], "dry_run": True})
                continue
            pcode, ppay = api(
                token,
                "PATCH",
                f"/zones/{zid}/dns_records/{record['id']}",
                body,
            )
            if pcode != 200 or not ppay.get("success"):
                raise RuntimeError(
                    f"proxy apex failed http={pcode} errors={ppay.get('errors')}"
                )
            print(f"ok proxied apex {zone_name} {rtype} id={record['id']}")
            updated.append({"type": rtype, "id": record["id"], "proxied": True})

    if not updated:
        raise RuntimeError(f"no apex A/AAAA records found for {zone_name}")
    return {"zone": zone_name, "records": updated}
