# Strategy Scan (MT4) — ***366 (InstaFinance-Singapore.com)
Scan: 2026.11.18 04:23:53 UTC · history 2026.06.15 → 2026.11.18 · 2262 trades · balance 20041.07 USD

> Ye sab trade history se nikala andaaza hai (EA ka asli code nahi). "pakka" = data se saaf dikh raha, "kamzor" = kam data.

## EA magic 666888 — 2237 trades
| Cheez | Kya mila | Bharosa |
|---|---|---|
| EA type | Grid / averaging + Martingale (lot × 1.29) + Hedge (buy + sell ek saath) | pakka |
| Symbol | GOLD (100% trades) | pakka |
| Direction | BUY 1197 / SELL 1040 | pakka |
| Entry kab | Candle open se nahi — tick par / beech me (price level ya condition par) | achha andaaza |
| Trading time | Lagbhag poore din (koi time filter nahi dikhta) | kamzor (kam data) |
| Direction rule (andaaza) | Close > EMA50 → SELL, warna BUY [M5] — 68.5% entries se match | achha andaaza |
| Filter (andaaza) | BUY entries me 'Close > EMA50' 15.3% (normal 35.9%) [M5] | achha andaaza |
| Filter (andaaza) | SELL entries me 'Pichhli candle badi (avg se 1.5x)' 35.1% (normal 15.0%) [H1] | achha andaaza |
| Lot | Shuru 0.01 (min 0.01, max 2.47) | pakka |
| Grid gap | ≈ 167.0 points (ghaate me add, 100.0% adverse) — har add ~2.5 min baad | kamzor (kam data) |
| Lot badhna | × 1.0 har level | pakka |
| Max levels | 22 (avg 5.6) | pakka |
| Basket exit | Basket ek saath band (96.2%) — basket profit ≈ $19.47 hote hi band (median $31.62) | pakka |
| SL | ≈ 235.0 points (8.2% trades par SL) | kamzor (kam data) |
| Trailing / BE | 76.2% SL-close profit me — trailing/breakeven lagta hai (median 247.0 pts lock) | achha andaaza |
| Risk | Max 26 trade ek saath · sabse bada loss $-242.64 · closed DD $-1934.31 | pakka |
| Result | Net $15020.92 · jeet 55.5% · PF 1.7 · 143.2 trade/din | pakka |

**Clone EA ke liye inputs (andaaza):**
```
Symbol = GOLD
Magic = 666888
StartLot = 0.01
GridGapPoints = 167.0
LotMultiplier = 1.0
MaxLevels = 22
BasketTargetUSD = 19.47
SLPoints = 235.0
```
**Direction rules (top match):**
- [M5] Close > EMA50 → SELL, warna BUY — 68.5% (231 entries, ulta (reversal))
- [M5] EMA9 > EMA20 → SELL, warna BUY — 67.8% (231 entries, ulta (reversal))
- [M15] Close > EMA20 → SELL, warna BUY — 67.6% (416 entries, ulta (reversal))
- [M15] RSI14 > 50 → SELL, warna BUY — 66.2% (416 entries, ulta (reversal))
- [M5] EMA20 > EMA50 → SELL, warna BUY — 66.0% (231 entries, ulta (reversal))
- [M5] Close > EMA100 → SELL, warna BUY — 65.5% (216 entries, ulta (reversal))
**Filters (entries vs normal market):**
- [M5] BUY: Close > EMA50 — entries me 15.3%, normal 35.9%
- [H1] SELL: Pichhli candle badi (avg se 1.5x) — entries me 35.1%, normal 15.0%
**RSI14 entry par:** M5 BUY med 41.9 (17.9–80.6), SELL med 50.6 (17.9–76.5); M15 BUY med 42.8 (15.5–82.3), SELL med 52.5 (15.6–82.3); H1 BUY med 43.3 (18.5–84.1), SELL med 49.0 (18.7–84.1)
**Entries ghante ke hisaab se (IST):** 0:00=11, 1:00=8, 2:00=12, 3:00=4, 4:00=6, 5:00=14, 6:00=33, 7:00=24, 8:00=20, 9:00=17, 10:00=9, 11:00=27, 12:00=17, 13:00=11, 14:00=17, 15:00=7, 16:00=4, 17:00=12, 18:00=15, 19:00=43, 20:00=38, 21:00=26, 22:00=32, 23:00=9
**Din:** Som=86, Mangal=99, Budh=65, Guru=104, Shukra=62

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