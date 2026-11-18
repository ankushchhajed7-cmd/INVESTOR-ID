# Strategy Scan (MT5) — ***829 (CapitalNineGlobal-Server)
Scan: 2026.11.18 19:44:16 UTC · history 2026.09.21 → 2026.11.18 · 1655 trades · balance 2075.44 USD

> Ye sab trade history se nikala andaaza hai (EA ka asli code nahi). "pakka" = data se saaf dikh raha, "kamzor" = kam data.

## EA magic 9697842 — 1440 trades
| Cheez | Kya mila | Bharosa |
|---|---|---|
| EA type | Single trade (ek signal = ek trade) | pakka |
| Symbol | XAUUSD.e (100% trades) | pakka |
| Direction | BUY 791 / SELL 649 | pakka |
| Entry kab | Candle open se nahi — tick par / beech me (price level ya condition par) | achha andaaza |
| Trading time (server) | 23:00–21:59 | kamzor (kam data) |
| Direction rule (andaaza) | Pichhli candle green → BUY, warna SELL [M5] — 98.9% entries se match | pakka |
| Filter (andaaza) | BUY entries me 'Pichhli candle green' 98.6% (normal 49.3%) [M5] | achha andaaza |
| Filter (andaaza) | SELL entries me 'Pichhli candle green' 0.8% (normal 49.3%) [M5] | achha andaaza |
| Lot | Shuru 0.01 (min 0.01, max 0.01) | pakka |
| Basket exit | Basket ek saath band (100.0%) — profit median $0.92 | pakka |
| SL | SL nahi lagta (0%) — risk zyada | pakka |
| Trailing / BE | 77.3% SL-close profit me — trailing/breakeven lagta hai (median 32.0 pts lock) | achha andaaza |
| Risk | Max 11 trade ek saath · sabse bada loss $-65.5 · closed DD $-190.76 | pakka |
| Result | Net $524.33 · jeet 77.8% · PF 1.46 · 57.7 trade/din | pakka |

**Clone EA ke liye inputs (andaaza):**
```
Symbol = XAUUSD.e
Magic = 9697842
EntryRule = M5: Pichhli candle green → BUY, warna SELL
StartLot = 0.01
```
**Direction rules (top match):**
- [M5] Pichhli candle green → BUY, warna SELL — 98.9% (1327 entries, trend)
- [M5] 20-candle high/low breakout → BUY, warna SELL — 93.9% (295 entries, trend)
- [M15] 20-candle high/low breakout → BUY, warna SELL — 92.2% (234 entries, trend)
- [M5] Pichhli 2 candle green → BUY, warna SELL — 84.1% (1327 entries, trend)
- [M5] Close > EMA20 → BUY, warna SELL — 77.1% (1327 entries, trend)
- [M5] RSI14 > 50 → BUY, warna SELL — 74.5% (1327 entries, trend)
**Filters (entries vs normal market):**
- [M5] BUY: Pichhli candle green — entries me 98.6%, normal 49.3%
- [M5] SELL: Pichhli candle green — entries me 0.8%, normal 49.3%
- [M15] BUY: Pichhli candle green — entries me 71.3%, normal 48.8%
- [M5] BUY: Close > EMA50 — entries me 69.8%, normal 48.4%
**RSI14 entry par:** M5 BUY med 57.1 (26.2–86.9), SELL med 41.6 (17.9–81.5); M15 BUY med 51.5 (30.4–78.3), SELL med 48.9 (31.3–80.8); H1 BUY med 50.5 (29.8–68.6), SELL med 52.2 (36.1–71.4)
**Din:** Som=294, Mangal=348, Budh=73, Guru=298, Shukra=299, Ravi=15

## EA magic 26092026 — 215 trades
| Cheez | Kya mila | Bharosa |
|---|---|---|
| EA type | Single trade (ek signal = ek trade) | pakka |
| Symbol | XAUUSD.e (100% trades) | pakka |
| Direction | BUY 78 / SELL 137 | pakka |
| Entry kab | M15 candle khulte hi (97.2% entries candle ke pehle 10 sec me) | pakka |
| Trading time (server) | 23:00–21:59 | kamzor (kam data) |
| Direction rule (andaaza) | Close > EMA100 → BUY, warna SELL [M5] — 100.0% entries se match | pakka |
| Filter (andaaza) | BUY entries me 'Close > EMA200' 100.0% (normal 37.2%) [M5] | achha andaaza |
| Filter (andaaza) | BUY entries me 'Close > EMA50' 100.0% (normal 39.1%) [M15] | achha andaaza |
| Lot | Shuru 0.01 (min 0.01, max 0.32) | pakka |
| TP | ≈ 835.0 points (100.0% trades par TP) | achha andaaza |
| SL | ≈ 696.0 points (100.0% trades par SL) | achha andaaza |
| Risk | Max 1 trade ek saath · sabse bada loss $-234.88 · closed DD $-531.65 | pakka |
| Result | Net $551.11 · jeet 45.6% · PF 1.2 · 5.9 trade/din | pakka |

**Clone EA ke liye inputs (andaaza):**
```
Symbol = XAUUSD.e
Magic = 26092026
Timeframe = M15
EntryRule = M5: Close > EMA100 → BUY, warna SELL
StartLot = 0.01
TPPoints = 835.0
SLPoints = 696.0
```
**Direction rules (top match):**
- [M5] Close > EMA100 → BUY, warna SELL — 100.0% (215 entries, trend)
- [M5] Close > EMA200 → BUY, warna SELL — 100.0% (215 entries, trend)
- [M15] Close > EMA50 → BUY, warna SELL — 100.0% (215 entries, trend)
- [M15] Close > EMA20 → BUY, warna SELL — 100.0% (215 entries, trend)
- [M15] RSI14 > 50 → BUY, warna SELL — 100.0% (215 entries, trend)
- [M15] EMA20 > EMA50 → BUY, warna SELL — 100.0% (215 entries, trend)
**Filters (entries vs normal market):**
- [M5] BUY: Close > EMA200 — entries me 100.0%, normal 37.2%
- [M15] BUY: Close > EMA50 — entries me 100.0%, normal 39.1%
- [M5] BUY: Close > EMA50 — entries me 100.0%, normal 41.4%
- [M15] BUY: Close > EMA200 — entries me 79.5%, normal 32.6%
- [M5] SELL: Close > EMA50 — entries me 0.7%, normal 41.4%
- [M15] SELL: Close > EMA50 — entries me 0.0%, normal 39.1%
**RSI14 entry par:** M5 BUY med 62.3 (44.5–86.1), SELL med 38.6 (16.3–56.9); M15 BUY med 60.8 (55.2–82.3), SELL med 36.9 (17.2–44.8); H1 BUY med 56.6 (38.0–81.6), SELL med 38.2 (17.4–53.7)
**Din:** Som=34, Mangal=44, Budh=59, Guru=41, Shukra=35, Ravi=2


_Raw detail: strategy.json_