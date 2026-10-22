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
- v1.06 (2026-10-22) — FIX + Update button. 22 Oct ke shadow-E push ne galti se purani copy se index.html/STATE.md likh diye the, jisse SAMU REPORT ka header link aur v1.05 (SAMU REPORT) ki STATE line hat gayi thi — dono wapas. Header me **⟳ Update button**: cache + service worker saaf karke naya version zabardasti load; har load + har 10 min `index.html` ka `APP_VER` check, naya ho to button hara "⬆ vX". Chhoti screen par clock chhupa. SW iw-shell-v6. (Seekh: hamesha repo ki taaza copy par hi badlav.)
- v1.05b (2026-10-22, app) — Shadow result 17–22 Oct (13 complete trades, 0.01 lot): Buster asli +0.31 (10/13 jeet, avg jeet 0.53), A 10000/8000 −2.14, B 15000/12000 −2.46, C 20000/15000 +6.59, **D 30000/20000 +12.58** (avg jeet 3.14) — par D ki badhat 2 bade trades (+7.47, +7.24) se; chhote trade jahan Buster +0.19/+0.69 bacha leta, D −1.50. Buster ka chhupa rule nikla: ~5000–6000 pts par SL ≈ open+5, phir ~5000 pts peeche trail (peak ka ~53% rakhta). Isliye naya **E (hybrid)**: BE 5500 pts par SL = open+500, phir 30000 par shuru 20000 doori. `BTC Trailing Manager v1.02` (5 virtual sets). App: purani A–D table + nayi "E ke saath — sirf naye trades" table. SW iw-shell-v5. Agla kadam: ~1 hafta E vs D vs Buster, phir winner LIVE.
- v1.05 (2026-10-21) — **SAMU REPORT** (`report/` — alag PWA, apna manifest + sw `sr-shell-v1`, scope `report/`). Apne Exness DEMO + REAL accounts (SamuSignal ke trades) ka method-wise hisaab: 📡 Signal app (magic 777001 FXBridge / 777100 SamuSignal EA), 📸 Chart Analysis (PERSONAL FX 111222 + comment `PFXA…`, grid adds `PFX_GRID_ADD` usi basket me), ⚖️ Pair Trading (`PFXP<jodi>_<leg>`, jodi = 1 trade), ✋ Manual (panel / magic 0), 🤖 Dusre EA. Har method: trades, win %, P/L, avg jeet/haar, PF, max DD (band trades), avg/worst "sabse bura" (MAE), band hone ka kaaran (TP/LOCK/SL/EA/KHUD), symbol-wise, trade list (SL/TP/entry/exit/time). Compare tab = kaun sa method aage. Account tab = equity curve + max DD %. Gintee `cfg.start` (default 2026-10-21) se; Aaj/7/30/Sab filter. Accounts apne aap `data/` folder list se (GitHub API). EA v1.05: close record me magic, cm, sl, tp, worst; `IW_equity_<acc>.jsonl` (har 15 min + beech ka low); naya `data/<acc>/report.json` (band hone par 60 sec me, warna har 15 min). Investor Watch header me SAMU REPORT link.
- v1.04 (2026-10-17) — SHADOW test. `BTC Trailing Manager v1.01` (samusignal/vps-ea) SHADOW mode (default, zero risk): real SL nahi chhuta, har Buster trade par 4 trailing settings A 10000/8000, B 15000/12000, C 20000/15000, D 30000/20000 (points) virtual chalata hai (real band hone ke baad bhi jab tak virtual SL/TP na lage), Buster ka REAL result bhi likhta hai → `MQL5\Files\IW_shadow_<acc>.jsonl`. Watcher v1.04 ise trail.json me `shadow` banakar bhejta hai (file size badle to push). App: Trailing tab ke upar "Shadow test — kaunsi setting best" table (sirf complete trades: asli + charon virtual band), hara row = sabse zyada kul $. SW cache iw-shell-v4. Faisla: doosra VPS band hai, naya demo terminal ki jagah nahi → isliye real 3099 par shadow test.
- v1.03 (2026-10-17) — TRAILING focus. EA: 1-sec scan; har SL/TP move ka event (profit move, SL lock vs open, price-SL gap, step, $), har position ka peak, band hone par close summary (peak vs close = give-back, deal reason SL/TP/EA/manual), VPS par JSONL files (restart pe bache), `data/<acc>/trail.json` (only when changed, max every 60s). App: naya **Trailing** tab — inferred rule (start, first lock, gap, step), "peak ka kitna % rakha", "peak par band hota to aur milta", exit reasons, hints, closed trades + SL events tables. SW cache iw-shell-v3.
- Related: `BTC Trailing Manager v1.00` (samusignal/vps-ea) — Buster BTC ke trades ka trailing apni settings se (Buster me UseTrailingStop=false). Trailing tab se iske results compare honge.
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
