# STATE — INVESTOR-ID

Read-only MT5 account watcher. A Reader EA (investor login) pushes an account's
trades + history to this GitHub repo as JSON; a mobile PWA shows them live and
auto-detects the EA's behaviour (grid gap, martingale, basket close, TP/SL).
Purpose: study a purchased/observed EA's behaviour to build your own clone.
The EA NEVER trades.

## Files
- `index.html` — mobile PWA dashboard (GitHub Pages). Reads data via raw.githubusercontent.
- `Investor Account Watcher v1.00.mq5` — Reader EA for MT5 (load in MetaEditor, run on VPS). Not required in the repo to work, kept here for safekeeping.
- `data/<account>/live.json` — current open positions + balance (auto-written by EA every ~20s)
- `data/<account>/history.json` — closed deals, last N days (auto-written by EA, refreshed ~30 min)

## How it connects
Reader EA (VPS, investor login) → GitHub contents API (fine-grained PAT) → repo JSON → PWA (raw.githubusercontent, 30s refresh).

## Decisions
- Backend = GitHub files (no Firebase). Repo must be **public** so the PWA can read without a token.
- Only the **masked** login (last 3 digits) is stored. No passwords, no PAT in the repo.
- Multi-account: PWA keeps the account list in the phone (localStorage); add any account number in the app. One EA instance per account (one MT5 terminal/chart per login).
- Live is near-real-time (raw CDN cache ~1–5 min). Fine for behaviour study.

## Settings (EA inputs)
GitHubOwner, GitHubRepo, GitHubBranch(main), GitHubToken(PAT), LiveSeconds(20), HistoryDays(60), HistoryRefreshMin(30), MaxDeals(1500).

## Version history
- v1.02 (2026-10-17) — Pending orders. EA: live.json me `orders` (pending buy/sell stop/limit: price, SL, TP, market price, magic, comment, setup time); history.json me `orders` (placed/canceled/filled/expired); positions/deals me magic + comment. App: Live tab me Pending orders table, History tab me Order history, Behaviour me "Pending-order behaviour" card (order types, pending gap, distance from market, fill rate, orders/day, EA magic + comment). SW cache iw-shell-v2. Test (4 live BTC orders): Stop-order breakout grid, SL ~150, TP ~4000.
- EA v1.01 (2026-10-17) — FIX 401 "Bad credentials": token trim, token length in Experts log, optional TokenFile (MQL5\Files\investor_token.txt). Also delivered via samusignal/vps-ea (VPS Helper auto-compiles).
- APK v1.0.1 built via apk-factory (release v1.0.1-build30).
- v1.01 (2026-10-17) — PWA installable: manifest.json, icons (192/512 + maskable), apple-touch-icon, favicon, service worker (network-first app shell, data fetches bypass SW). App now installs on mobile with the Investor Watch lens+candles icon.
- v1.00 (2026-10-17) — first build: Reader EA + PWA dashboard + behaviour summary.

## Notes
- Account 362293099 (XMGlobal-MT5 12) watched; token via MQL5\Files\investor_token.txt (TokenFile) — fixed 401.
- APK auto-updates (wraps Pages URL) — no rebuild needed for app changes.

## Pending / ideas
- Offline service worker for the PWA (currently online-only).
- Optional: store running max-concurrent trades over time for a better grid estimate.
- Optional: per-symbol point size so grid gap can show pips, not raw price.
