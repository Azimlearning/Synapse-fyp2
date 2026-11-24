# Deployment

> v4 hard constraint 12 holds: no public URL until the deploy gate (`../../Synapse-V4/refdocs/guides/checklist.md`) is met, or the owner grants a time-boxed waiver recorded as a decision (as v4 D-75 did). Decision V5-D11 is open.

## 1. Shape

| Part | Host | Why |
|---|---|---|
| Web app | Vercel (root `web`) | Next.js; already configured in v4 |
| API | A container with Chromium, a persistent disk and long streaming responses | The verifier runs Chromium; SQLite store and the **spend ledger** must persist |

## 2. Hosts compared

| Host | 2 GB price | Fit | Against |
|---|---|---|---|
| **Render Standard (recommended)** | About $25 a month (secondary sources) | v4's Blueprint (`render.yaml`, `Dockerfile`) exists; Singapore region; disk | Blueprint never run; a 15-minute first boot while the library seeds |
| Fly.io | $13.39 shared CPU, $33 performance-1x (Virginia prices; Singapore not confirmed) | Per-second billing; can stop when idle | New config; shared CPU may slow Chromium; cold starts |
| Cloud Run | Pay per use; 60-minute request limit | Streaming fits | Instance disk does not persist (general knowledge, not re-read), so the store and ledger would be lost: unsafe without a database change |
| A laptop and a tunnel | $0 | Only as a venue fallback | Rejected in v4 D-75 |

## 3. Changes v5 makes for deployment

1. **CI green first.** v4's last four runs failed or were cancelled (a smoke timeout, a Python job cancelled at its 45-minute limit). Split the suite, cache Playwright, raise or shard the timeout.
2. **Docker build in CI**, so the image is proven before any host sees it.
3. **Library built into the image** for a fixed origin, so boot takes seconds. Environments are bound to one origin by their CSP, so the production origin is settled first, ideally a custom domain.
4. **Shared access code** for any waiver deploy. Today the only spend guards are per-address limits and the cap.
5. **Settings checked at boot:** live mode, cap, ledger path (as v4), plus the model tier and `effort` printed in `/health`.
6. **The no-network verification container** (deploy-gate item): verify generated HTML in a separate container with no network and memory limits.
7. **Corpus decision (A-8):** without the corpus on the server, no deployed environment can earn `source-verified`.

## 4. Gate status carried from v4

| Gate item | State | v5 plan |
|---|---|---|
| Per-session and per-day limits | Built, per process | Same limits at the proxy |
| Spend cap and dashboard | Built (`/spend`) | Add per-lane cost |
| No-network verification container | Not built | Item 6 above |
| Free lane policy and label shown | Built | Per-part badges |
| Corpus position (A-8) | Open | Owner |
| Name (A-14) | Open | Owner |
| Security review | Not run | Before deploy |
| Licence | Not chosen | Owner |
| Real phone at 360 px | Not done | V5-6 |
