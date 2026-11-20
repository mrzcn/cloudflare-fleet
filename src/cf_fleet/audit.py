"""Fleet settings audit and anomaly detection."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from cf_fleet.api import get_all_settings, list_zones

CRITICAL = [
    "ssl",
    "always_use_https",
    "min_tls_version",
    "security_level",
    "cache_level",
    "development_mode",
    "brotli",
    "http3",
    "rocket_loader",
    "browser_cache_ttl",
    "waf",
]


def _tls_rank(version: object) -> int:
    order = {"1.0": 0, "1.1": 1, "1.2": 2, "1.3": 3}
    return order.get(str(version), -1)


def find_anomalies(zone_name: str, settings: dict[str, object]) -> list[dict]:
    issues: list[dict] = []
    ssl = settings.get("ssl")
    if ssl in ("flexible", "off"):
        issues.append({"zone": zone_name, "type": "ssl", "detail": f"ssl={ssl}"})
    if settings.get("always_use_https") == "off":
        issues.append({"zone": zone_name, "type": "https", "detail": "always_use_https=off"})
    if _tls_rank(settings.get("min_tls_version")) < _tls_rank("1.2"):
        issues.append(
            {
                "zone": zone_name,
                "type": "tls",
                "detail": f"min_tls_version={settings.get('min_tls_version')}",
            }
        )
    level = settings.get("security_level")
    if level in ("essentially_off", "low", "under_attack"):
        issues.append({"zone": zone_name, "type": "security", "detail": f"security_level={level}"})
    if settings.get("development_mode") == "on":
        issues.append({"zone": zone_name, "type": "dev_mode", "detail": "development_mode=on"})
    if settings.get("rocket_loader") == "on":
        issues.append({"zone": zone_name, "type": "rocket", "detail": "rocket_loader=on"})
    ttl = settings.get("browser_cache_ttl")
    if ttl in (0, 60):
        issues.append({"zone": zone_name, "type": "ttl", "detail": f"browser_cache_ttl={ttl}"})
    return issues


def run_audit(
    token: str,
    account_id: str | None = None,
    zone_filter: list[str] | None = None,
    report_path: Path | None = None,
) -> dict:
    zones = list_zones(token, account_id=account_id)
    if zone_filter:
        wanted = {z.lower() for z in zone_filter}
        zones = [z for z in zones if z["name"].lower() in wanted]

    distribution: dict[str, Counter] = defaultdict(Counter)
    zone_critical: list[dict] = []
    anomalies: list[dict] = []

    for zone in zones:
        settings = get_all_settings(token, zone["id"])
        for key, value in settings.items():
            distribution[key][json.dumps(value, sort_keys=True, default=str)] += 1
        row = {"name": zone["name"]}
        for key in CRITICAL:
            row[key] = settings.get(key)
        zone_critical.append(row)
        anomalies.extend(find_anomalies(zone["name"], settings))

    dist_summary: dict[str, list[dict]] = {}
    for key, counter in distribution.items():
        if key in CRITICAL or len(counter) > 1:
            dist_summary[key] = [
                {"value": json.loads(raw), "count": count}
                for raw, count in counter.most_common()
            ]

    report = {
        "zone_count": len(zones),
        "zone_critical": zone_critical,
        "distribution": dist_summary,
        "anomalies": anomalies,
    }

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return report


def print_audit_summary(report: dict) -> None:
    print(f"zones={report['zone_count']} anomalies={len(report['anomalies'])}")
    by_type: Counter = Counter(a["type"] for a in report["anomalies"])
    for kind, count in by_type.most_common():
        print(f"  {kind}: {count}")
    for key in CRITICAL:
        entries = report["distribution"].get(key) or []
        if not entries:
            continue
        parts = [f"{e['value']!r}×{e['count']}" for e in entries[:6]]
        print(f"  {key}: " + ", ".join(parts))
