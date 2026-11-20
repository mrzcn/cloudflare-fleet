# Example: harden marketing / form brand zones

This is a **generic** pattern inspired by multi-zone form landing sites.
Replace `example.com` with your zones. Do not commit real tokens or origin IPs.

## Goals

1. Turn **Rocket Loader** off (often breaks modern JS forms).
2. Keep HTML / contact pages fresher with Cache Rules (bypass cache for HTML/PHP and key SEO paths).
3. Purge stale URLs after deploy.

## Token permissions

- Zone → Zone → Read
- Zone → Zone Settings → Edit
- Zone → Cache Purge → Purge
- Zone → Cache Rules → Edit (for rules work outside this CLI)

## With this CLI

```bash
cp .env.example .env   # set CF_API_TOKEN

# Audit a subset
./scripts/cf-fleet audit --zone example.com,www-example.net

# Dry-run baseline (HTTPS on, min TLS 1.2, security medium, Rocket off, TTL 14400)
./scripts/cf-fleet apply-baseline --zone example.com --dry-run
./scripts/cf-fleet apply-baseline --zone example.com

# Purge after a content deploy
./scripts/cf-fleet purge --zone example.com
```

## Cache Rules (manual / dashboard or API)

Create a Cache Rule that bypasses cache when:

- path extension is `html` / `htm` / `php`, or
- path is `/`, `/robots.txt`, `/sitemap.xml`, or
- response is a redirect (301/302)

Exact expression syntax depends on your plan and ruleset version; validate in the Cloudflare dashboard first.

## Safety notes

- Prefer a **dedicated** API token scoped to the zones you manage.
- Run `apply-baseline --dry-run` before applying.
- Raising SSL from `flexible` to `full`/`strict` is **not** part of the default baseline — confirm origin HTTPS first.
