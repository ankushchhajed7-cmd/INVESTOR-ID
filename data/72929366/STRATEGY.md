# Strategy Scan (MT4) — ***366 (InstaFinance-Singapore.com)
Scan: 2026.11.18 06:33:16 UTC · history 2026.06.15 → 2026.11.18 · 2283 trades · balance 20161.46 USD

> Ye sab trade history se nikala andaaza hai (EA ka asli code nahi). "pakka" = data se saaf dikh raha, "kamzor" = kam data.

## EA magic 666888 — 2258 trades
| Cheez | Kya mila | Bharosa |
|---|---|---|
| EA type | Grid / averaging + Dono side alag grid (BUY basket + SELL basket saath chalte) | pakka |
| Symbol | GOLD (100% trades) | pakka |
| Direction | BUY 1210 / SELL 1048 | pakka |
| Entry kab | Candle open se nahi — tick par / beech me (price level ya condition par) | achha andaaza |
| Trading time | Lagbhag poore din (koi time filter nahi dikhta) | kamzor (kam data) |
| Direction rule (andaaza) | Close > EMA50 → SELL, warna BUY [M5] — 67.7% entries se match | achha andaaza |
| Lot | Shuru 0.01 (min 0.01, max 2.47) | pakka |
| Grid gap | ≈ 167.0 points (ghaate me add, 100.0% adverse) — har add ~2.5 min baad | kamzor (kam data) |
| Lot badhna | +0.01 har level (50.5% adds), kabhi same lot (34.7%) | kamzor (kam data) |
| Max levels | 22 (avg 5.6) | pakka |
| Basket exit | Basket ek saath band (96.2%) — basket profit ≈ $19.47 hote hi band (median $31.62) | pakka |
| SL | ≈ 239.0 points (8.5% trades par SL) | kamzor (kam data) |
| Trailing / BE | 76.2% SL-close profit me — trailing/breakeven lagta hai (median 247.0 pts lock) | achha andaaza |
| Risk | Max 26 trade ek saath · sabse bada loss $-242.64 · closed DD $-1934.31 | pakka |
| Result | Net $15141.31 · jeet 55.6% · PF 1.71 · 143.7 trade/din | pakka |

**Clone EA ke liye inputs (andaaza):**
```
Symbol = GOLD
Magic = 666888
StartLot = 0.01
GridGapPoints = 167.0
LotStep = 0.01
MaxLevels = 22
BasketTargetUSD = 19.47
SLPoints = 239.0
```
**Direction rules (top match):**
- [M5] Close > EMA50 → SELL, warna BUY — 67.7% (227 entries, ulta (reversal))
- [M15] Close > EMA20 → SELL, warna BUY — 67.4% (419 entries, ulta (reversal))
- [M5] EMA9 > EMA20 → SELL, warna BUY — 67.4% (234 entries, ulta (reversal))
- [M15] RSI14 > 50 → SELL, warna BUY — 66.0% (419 entries, ulta (reversal))
- [M5] Close > EMA100 → SELL, warna BUY — 65.2% (217 entries, ulta (reversal))
- [M5] RSI14 > 50 → SELL, warna BUY — 65.1% (234 entries, ulta (reversal))
**RSI14 entry par:** M5 BUY med 42.0 (17.9–80.6), SELL med 50.6 (17.9–76.5); M15 BUY med 42.8 (15.5–82.3), SELL med 52.4 (15.6–82.3); H1 BUY med 43.3 (18.5–84.1), SELL med 48.4 (18.7–84.1)
**Entries ghante ke hisaab se (IST):** 0:00=11, 1:00=8, 2:00=12, 3:00=4, 4:00=6, 5:00=14, 6:00=33, 7:00=24, 8:00=20, 9:00=17, 10:00=11, 11:00=28, 12:00=17, 13:00=11, 14:00=17, 15:00=7, 16:00=4, 17:00=12, 18:00=15, 19:00=43, 20:00=38, 21:00=26, 22:00=32, 23:00=9
**Din:** Som=86, Mangal=99, Budh=68, Guru=104, Shukra=62

## EA magic 9569 — 25 trades
| Cheez | Kya mila | Bharosa |
|---|---|---|
| EA type | Single trade (ek signal = ek trade) | pakka |
| Symbol | XAUUSD (100% trades) | pakka |
| Direction | BUY 24 / SELL 1 | pakka |
| Entry kab | Candle open se nahi — tick par / beech me (price level ya condition par) | achha andaaza |
| Trading time (IST) | 14:00–23:59 (entry wale ghante: 14, 15, 17, 19, 20, 23) | achha andaaza |
| Note | Lagbhag ek hi side (BUY 24 / SELL 1) — direction rule nahi, filters dekho |  |
| Lot | Shuru 0.01 (min 0.01, max 0.01) | pakka |
| SL | SL nahi lagta (0%) — risk zyada | pakka |
| Risk | Max 2 trade ek saath · sabse bada loss $-467.05 · closed DD $-478.7 | pakka |
| Result | Net $20.15 · jeet 88.0% · PF 1.04 · 13.3 trade/din | pakka |

**Clone EA ke liye inputs (andaaza):**
```
Symbol = XAUUSD
Magic = 9569
StartLot = 0.01
```
**Entries ghante ke hisaab se (IST):** 14:00=8, 15:00=4, 17:00=1, 19:00=5, 20:00=5, 23:00=2
**Din:** Som=2, Mangal=18, Budh=5


_Raw detail: strategy.json_