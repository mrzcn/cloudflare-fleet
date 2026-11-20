"""cloudflare-fleet CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cf_fleet import __version__
from cf_fleet.api import resolve_account_id, resolve_token
from cf_fleet.apply import apply_baseline, set_one
from cf_fleet.audit import print_audit_summary, run_audit
from cf_fleet.dns import proxy_apex
from cf_fleet.purge import purge_everything

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "policies" / "baseline.yaml"
DEFAULT_REPORT = ROOT / "reports" / "audit.json"


def _zones_arg(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cf-fleet",
        description="Audit and harden Cloudflare zone settings across a fleet.",
    )
    parser.add_argument("--version", action="version", version=f"cf-fleet {__version__}")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path.cwd() / ".env",
        help="Path to .env containing CF_API_TOKEN (default: ./.env)",
    )
    parser.add_argument(
        "--account-id",
        default=None,
        help="Optional Cloudflare account id filter",
    )
    parser.add_argument(
        "--zone",
        default=None,
        help="Comma-separated zone names (default: all zones visible to the token)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    audit_p = sub.add_parser("audit", help="Dump settings distribution and anomalies")
    audit_p.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Write JSON report (default: {DEFAULT_REPORT})",
    )

    purge_p = sub.add_parser("purge", help="Purge everything for selected zones")
    purge_p.add_argument("--dry-run", action="store_true")

    apply_p = sub.add_parser("apply-baseline", help="Apply policies/baseline.yaml")
    apply_p.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY,
        help=f"Policy YAML (default: {DEFAULT_POLICY})",
    )
    apply_p.add_argument("--dry-run", action="store_true")

    set_p = sub.add_parser("set", help="Set one zone setting on selected zones")
    set_p.add_argument("setting", help="Setting id, e.g. always_use_https")
    set_p.add_argument("value", help="Desired value, e.g. on / 1.2 / 14400")
    set_p.add_argument("--dry-run", action="store_true")

    apex_p = sub.add_parser("proxy-apex", help="Set apex A/AAAA records to proxied")
    apex_p.add_argument("zone_name", help="Exact zone name, e.g. example.com")
    apex_p.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    token = resolve_token(args.env_file)
    account_id = args.account_id or resolve_account_id(args.env_file)
    zones = _zones_arg(args.zone)

    try:
        if args.command == "audit":
            report = run_audit(
                token,
                account_id=account_id,
                zone_filter=zones,
                report_path=args.report,
            )
            print_audit_summary(report)
            print(f"report={args.report}")
            return 0

        if args.command == "purge":
            ok, fail = purge_everything(
                token,
                account_id=account_id,
                zone_filter=zones,
                dry_run=args.dry_run,
            )
            print(f"purged={len(ok)} failed={len(fail)}")
            return 1 if fail else 0

        if args.command == "apply-baseline":
            changes, fail = apply_baseline(
                token,
                policy_path=args.policy,
                account_id=account_id,
                zone_filter=zones,
                dry_run=args.dry_run,
            )
            print(f"changes={len(changes)} failed={len(fail)}")
            return 1 if fail else 0

        if args.command == "set":
            value: object = args.value
            if value.isdigit():
                value = int(value)
            ok, fail = set_one(
                token,
                setting=args.setting,
                value=value,
                account_id=account_id,
                zone_filter=zones,
                dry_run=args.dry_run,
            )
            print(f"updated={len(ok)} failed={len(fail)}")
            return 1 if fail else 0

        if args.command == "proxy-apex":
            result = proxy_apex(token, args.zone_name, dry_run=args.dry_run)
            # Avoid printing record content (may be origin IPs)
            safe = {
                "zone": result["zone"],
                "records": [
                    {k: v for k, v in rec.items() if k != "content"}
                    for rec in result["records"]
                ],
            }
            print(json.dumps(safe, indent=2))
            return 0
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command {args.command}")
    return 2
