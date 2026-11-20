# cloudflare-fleet

Audit and harden **Cloudflare zone settings** across many domains with a small Python CLI (stdlib only — no `pip install` required).

Use it when you manage a fleet of zones and want a repeatable baseline:

- Always Use HTTPS on
- Minimum TLS 1.2 (raises 1.0/1.1; leaves 1.3 alone)
- Security level `medium` (clears `low` / `under_attack` when applying baseline)
- Rocket Loader off
- Browser Cache TTL `14400`

SSL encryption mode (`flexible` → `full`/`strict`) is **not** changed by the default policy — verify origin HTTPS first.

## Quick start

```bash
git clone https://github.com/mrzcn/cloudflare-fleet.git
cd cloudflare-fleet
cp .env.example .env
# edit .env → set CF_API_TOKEN

chmod +x scripts/cf-fleet
./scripts/cf-fleet audit
./scripts/cf-fleet apply-baseline --dry-run
./scripts/cf-fleet apply-baseline
./scripts/cf-fleet purge --dry-run
```

Or:

```bash
export PYTHONPATH=src
python3 -m cf_fleet audit
```

## API token

Create a **Custom** token at Cloudflare → My Profile → API Tokens.

Suggested permissions:

| Permission | Access |
|------------|--------|
| Zone → Zone | Read |
| Zone → Zone Settings | Edit |
| Zone → Cache Purge | Purge |
| Zone → DNS | Edit (only for `proxy-apex`) |

Scope the token to the zones (or account) you intend to manage. Do not commit `.env`.

Optional: set `CF_ACCOUNT_ID` in `.env` to limit listing to one account.

## Commands

| Command | Purpose |
|---------|---------|
| `audit` | Settings distribution + anomalies; writes `reports/audit.json` (gitignored) |
| `purge` | `purge_everything` for all or `--zone` filtered zones |
| `apply-baseline` | Apply [`policies/baseline.yaml`](policies/baseline.yaml) |
| `set SETTING VALUE` | Set one setting across selected zones |
| `proxy-apex ZONE` | Proxied (orange cloud) apex `A`/`AAAA` |

Common flags:

- `--env-file PATH` — default `./.env`
- `--account-id ID` — account filter
- `--zone a.com,b.com` — limit to named zones
- `--dry-run` — print planned changes only (`purge`, `apply-baseline`, `set`, `proxy-apex`)

Examples:

```bash
./scripts/cf-fleet audit --zone example.com
./scripts/cf-fleet set rocket_loader off --zone example.com
./scripts/cf-fleet proxy-apex example.com --dry-run
```

## Policy file

Edit [`policies/baseline.yaml`](policies/baseline.yaml) or pass `--policy path/to/custom.yaml`.

The bundled YAML loader supports simple nested mappings only (no lists/anchors). Keep policies small.

## Safety

- Never commit API tokens, account dumps, or DNS record contents with origin IPs.
- `reports/` is gitignored — local audits may contain your zone names.
- Prefer `--dry-run` before fleet-wide applies.
- Cache purge increases origin traffic briefly.

## Examples

See [`examples/form-sites-harden.md`](examples/form-sites-harden.md) for a marketing/form-site hardening pattern (Rocket Loader, cache freshness, purge).

## License

MIT — see [LICENSE](LICENSE).
