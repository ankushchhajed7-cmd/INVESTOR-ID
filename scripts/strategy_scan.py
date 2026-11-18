# Investor Watch v1.08 — STRATEGY ANALYSER
# raw.json (mt5_fetch.py ka output) -> strategy.json + STRATEGY.md (+ history.json / live.json for app)
# Sirf python standard library. Trade history se EA ka "behaviour" nikalta hai:
#   type (single / grid / martingale / pending breakout / hedge), symbol, timeframe, entry time,
#   direction rule (EMA / candle / RSI / breakout se match), grid gap, lot multiplier,
#   TP / SL / basket $ target, trailing, risk.  Sab andaaza = history par based, confidence ke saath.
#
# Usage: python scripts/strategy_scan.py scan_tmp/raw.json data/<login>
import bisect, json, math, os, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone

TYPES = {0: 'BUY', 1: 'SELL', 2: 'BUY_LIMIT', 3: 'SELL_LIMIT', 4: 'BUY_STOP', 5: 'SELL_STOP',
         6: 'BUY_STOP_LIMIT', 7: 'SELL_STOP_LIMIT', 8: 'CLOSE_BY'}
ENTRY = {0: 'IN', 1: 'OUT', 2: 'INOUT', 3: 'OUT_BY'}
REASON = {0: 'MANUAL', 1: 'MOBILE', 2: 'WEB', 3: 'EA', 4: 'SL', 5: 'TP', 6: 'STOP-OUT', 7: 'ROLLOVER', 8: 'VMARGIN', 9: 'SPLIT'}
OSTATE = {0: 'STARTED', 1: 'PLACED', 2: 'CANCELED', 3: 'PARTIAL', 4: 'FILLED', 5: 'REJECTED', 6: 'EXPIRED'}
TF_SEC = {'M1': 60, 'M5': 300, 'M15': 900, 'M30': 1800, 'H1': 3600, 'H4': 14400, 'D1': 86400}
WD = ['Som', 'Mangal', 'Budh', 'Guru', 'Shukra', 'Shani', 'Ravi']


# ---------------- helpers ----------------
def ts(t):
    return datetime.fromtimestamp(int(t), timezone.utc).strftime('%Y.%m.%d %H:%M:%S')


def med(a):
    a = sorted(a)
    if not a:
        return None
    n = len(a)
    return a[n // 2] if n % 2 else (a[n // 2 - 1] + a[n // 2]) / 2


def mean(a):
    return sum(a) / len(a) if a else None


def cv(a):
    """spread / average — kam = pakka fixed value"""
    m = mean(a)
    if not a or not m or len(a) < 2:
        return None
    sd = math.sqrt(sum((x - m) ** 2 for x in a) / len(a))
    return abs(sd / m)


def pct(a, b):
    return round(100.0 * a / b, 1) if b else 0.0


def r2(x, n=2):
    return None if x is None else round(x, n)


def mode_round(a, step):
    """sabse common value (step me round karke)"""
    if not a:
        return None, 0
    c = Counter(round(x / step) * step for x in a)
    v, n = c.most_common(1)[0]
    return v, n


def conf(n, strength):
    """confidence label: n = samples, strength 0..1"""
    if n >= 20 and strength >= 0.8:
        return 'pakka'
    if n >= 8 and strength >= 0.65:
        return 'achha andaaza'
    return 'kamzor (kam data)'


def strength(c):
    """cv -> 0..1 (0 cv = bilkul fixed = 1.0)"""
    return 0.5 if c is None else max(0.0, 1 - min(1.0, c))


def hour_range(hours):
    """circular ghante -> 'HH:00–HH:59' (sabse bada khaali gap chhod kar)"""
    h = sorted(set(hours))
    if not h:
        return None
    if len(h) == 24:
        return '24 ghante'
    gaps = [((h[(i + 1) % len(h)] - h[i]) % 24, i) for i in range(len(h))]
    g, i = max(gaps)
    start, end = h[(i + 1) % len(h)], h[i]
    return f'{start:02d}:00–{end:02d}:59'


def side_of(t):
    return 'BUY' if str(t).startswith('BUY') else 'SELL'


# ---------------- indicators ----------------
def ema(vals, n):
    out, k, e = [], 2.0 / (n + 1), None
    for i, v in enumerate(vals):
        e = v if e is None else v * k + e * (1 - k)
        out.append(e if i >= n - 1 else None)
    return out


def rsi(vals, n=14):
    out = [None] * len(vals)
    if len(vals) <= n:
        return out
    g = l = 0.0
    for i in range(1, n + 1):
        d = vals[i] - vals[i - 1]
        g += max(d, 0)
        l += max(-d, 0)
    g /= n
    l /= n
    out[n] = 100 - 100 / (1 + g / l) if l else 100.0
    for i in range(n + 1, len(vals)):
        d = vals[i] - vals[i - 1]
        g = (g * (n - 1) + max(d, 0)) / n
        l = (l * (n - 1) + max(-d, 0)) / n
        out[i] = 100 - 100 / (1 + g / l) if l else 100.0
    return out


class Bars:
    def __init__(self, rows, tf):
        rows = sorted(rows)
        self.tf, self.sec = tf, TF_SEC[tf]
        self.t = [r[0] for r in rows]
        self.o = [r[1] for r in rows]
        self.h = [r[2] for r in rows]
        self.l = [r[3] for r in rows]
        self.c = [r[4] for r in rows]
        self.ema = {n: ema(self.c, n) for n in (9, 20, 50, 100, 200)}
        self.rsi = rsi(self.c)

    def last_closed(self, t):
        i = bisect.bisect_right(self.t, t - self.sec) - 1
        return i if i >= 0 else None

    def price_at(self, t):
        i = bisect.bisect_right(self.t, t) - 1
        return self.o[i] if i >= 0 else None

    def feats(self, i, price):
        """bullish = True conditions (closed bar i, entry price)"""
        if i is None or i < 25:
            return None
        c = self.c[i]
        f = {}
        for n in (20, 50, 100, 200):
            if self.ema[n][i] is not None:
                f[f'Close > EMA{n}'] = c > self.ema[n][i]
        for a, b in ((9, 20), (20, 50), (50, 200)):
            if self.ema[a][i] is not None and self.ema[b][i] is not None:
                f[f'EMA{a} > EMA{b}'] = self.ema[a][i] > self.ema[b][i]
        f['Pichhli candle green'] = c > self.o[i]
        f['Pichhli 2 candle green'] = c > self.o[i] and self.c[i - 1] > self.o[i - 1]
        if self.rsi[i] is not None:
            f['RSI14 > 50'] = self.rsi[i] > 50
        hh = max(self.h[i - 19:i + 1])
        ll = min(self.l[i - 19:i + 1])
        if price is not None and (price > hh or price < ll):
            f['20-candle high/low breakout'] = price > hh
        return f

    def filters(self, i, price):
        """filter conditions (side ke hisaab se nahi) — baseline se tulna ke liye"""
        if i is None or i < 25:
            return None
        f = {}
        if self.rsi[i] is not None:
            f['RSI14 < 30'] = self.rsi[i] < 30
            f['RSI14 > 70'] = self.rsi[i] > 70
        rng = [self.h[j] - self.l[j] for j in range(i - 13, i + 1)]
        f['Pichhli candle badi (avg se 1.5x)'] = (self.h[i] - self.l[i]) > 1.5 * (sum(rng) / len(rng))
        for n in (50, 200):
            if self.ema[n][i] is not None:
                f[f'Close > EMA{n}'] = self.c[i] > self.ema[n][i]
        f['Pichhli candle green'] = self.c[i] > self.o[i]
        return f


# ---------------- core ----------------
def build_positions(raw):
    deals = [d for d in raw['deals'] if d.get('type') in (0, 1) and d.get('symbol')]
    orders = {o['ticket']: o for o in raw['orders']}
    byp = defaultdict(list)
    for d in deals:
        byp[d.get('position_id') or d.get('order')].append(d)
    P = []
    for pid, L in byp.items():
        L.sort(key=lambda d: (d['time_msc'] if d.get('time_msc') else d['time'] * 1000))
        ins = [d for d in L if d.get('entry') in (0, 2)]
        outs = [d for d in L if d.get('entry') in (1, 2, 3)]
        if not ins:
            continue
        i0 = ins[0]
        vin = sum(d['volume'] for d in ins) or i0['volume']
        op = sum(d['price'] * d['volume'] for d in ins) / vin
        o = orders.get(i0.get('order')) or {}
        p = {'id': pid, 'sym': i0['symbol'], 'side': 'BUY' if i0['type'] == 0 else 'SELL',
             'vol': round(vin, 2), 'ot': i0['time'], 'op': op, 'magic': i0.get('magic', 0),
             'cm': i0.get('comment', ''), 'sl': o.get('sl') or 0, 'tp': o.get('tp') or 0,
             'otype': TYPES.get(o.get('type'), 'BUY' if i0['type'] == 0 else 'SELL'),
             'setup': o.get('time_setup') or i0['time'], 'oprice': o.get('price_open') or op,
             'profit': sum((d.get('profit') or 0) + (d.get('commission') or 0) + (d.get('swap') or 0) + (d.get('fee') or 0) for d in L),
             'closed': False}
        if outs:
            vo = sum(d['volume'] for d in outs) or 1
            p.update({'ct': outs[-1]['time'], 'cp': sum(d['price'] * d['volume'] for d in outs) / vo,
                      'reason': REASON.get(outs[-1].get('reason'), str(outs[-1].get('reason'))),
                      'closed': vo >= vin - 1e-9, 'ccm': outs[-1].get('comment', '')})
        P.append(p)
    for x in raw.get('positions', []):          # abhi khule trades
        if any(p['id'] == x.get('identifier', x['ticket']) and not p['closed'] for p in P):
            for p in P:
                if p['id'] == x.get('identifier', x['ticket']):
                    p.update({'sl': x.get('sl') or p['sl'], 'tp': x.get('tp') or p['tp'], 'float': x.get('profit')})
            continue
        if any(p['id'] == x.get('identifier', x['ticket']) for p in P):
            continue
        P.append({'id': x.get('identifier', x['ticket']), 'sym': x['symbol'], 'side': 'BUY' if x['type'] == 0 else 'SELL',
                  'vol': x['volume'], 'ot': x['time'], 'op': x['price_open'], 'magic': x.get('magic', 0),
                  'cm': x.get('comment', ''), 'sl': x.get('sl') or 0, 'tp': x.get('tp') or 0, 'otype': 'BUY' if x['type'] == 0 else 'SELL',
                  'setup': x['time'], 'oprice': x['price_open'], 'profit': 0.0, 'float': x.get('profit'), 'closed': False})
    P.sort(key=lambda p: p['ot'])
    return P


def point_of(raw, sym, price):
    s = raw.get('symbols', {}).get(sym)
    if s and s.get('point'):
        return s['point']
    return 0.01 if price > 50 else (0.001 if price > 5 else 0.00001)


def make_baskets(P):
    """same symbol + side, ek saath khule (overlap) trades = ek basket"""
    B = []
    groups = defaultdict(list)
    for p in P:
        groups[(p['sym'], p['side'])].append(p)
    for k, L in groups.items():
        L.sort(key=lambda p: p['ot'])
        cur, cur_end = [], -1
        for p in L:
            end = p.get('ct', 10 ** 12) if p['closed'] else 10 ** 12
            if cur and p['ot'] < cur_end:
                cur.append(p)
                cur_end = max(cur_end, end)
            else:
                if cur:
                    B.append(cur)
                cur, cur_end = [p], end
        if cur:
            B.append(cur)
    B.sort(key=lambda b: b[0]['ot'])
    return B


def alignment(times):
    """kitne % entries candle khulne ke 0-10 sec me — kaunsa timeframe"""
    res = {}
    if len(times) < 5:
        return res, None
    for tf in ('M5', 'M15', 'M30', 'H1', 'H4', 'D1'):
        s = TF_SEC[tf]
        res[tf] = pct(sum(1 for t in times if t % s < 10), len(times))
    best = None
    if res['M5'] >= 60:
        for tf in ('M5', 'M15', 'M30', 'H1', 'H4', 'D1'):
            if res[tf] >= 0.9 * res['M5']:
                best = tf
    return res, best


def analyse_group(raw, P, bars, offset):
    out = {}
    n = len(P)
    sym_c = Counter(p['sym'] for p in P)
    main_sym = sym_c.most_common(1)[0][0]
    side_c = Counter(p['side'] for p in P)
    closed = [p for p in P if p['closed']]
    out['trades'] = n
    out['symbols'] = {s: c for s, c in sym_c.most_common()}
    out['buy'] = side_c.get('BUY', 0)
    out['sell'] = side_c.get('SELL', 0)
    out['net'] = r2(sum(p['profit'] for p in closed))
    wins = [p['profit'] for p in closed if p['profit'] > 0]
    losses = [p['profit'] for p in closed if p['profit'] < 0]
    out['win_pct'] = pct(len(wins), len(closed))
    out['pf'] = r2(sum(wins) / -sum(losses)) if losses else None
    out['avg_win'] = r2(mean(wins))
    out['avg_loss'] = r2(mean(losses))
    out['first'] = ts(P[0]['ot'])
    out['last'] = ts(P[-1]['ot'])
    days = max(1.0, (P[-1]['ot'] - P[0]['ot']) / 86400)
    out['trades_per_day'] = r2(n / days, 1)
    holds = [p['ct'] - p['ot'] for p in closed if p.get('ct')]
    out['hold_min_median'] = r2((med(holds) or 0) / 60, 1)

    # lots
    lots = [p['vol'] for p in P]
    out['lots'] = {'min': min(lots), 'max': max(lots), 'common': Counter(lots).most_common(1)[0][0],
                   'distinct': len(set(lots))}

    # ---- baskets ----
    B = make_baskets(P)
    sizes = [len(b) for b in B]
    multi = [b for b in B if len(b) >= 2]
    out['baskets'] = len(B)
    out['basket_pct'] = pct(len(multi), len(B))
    out['levels_max'] = max(sizes)
    out['levels_avg'] = r2(mean(sizes), 1)
    out['levels_dist'] = {str(k): v for k, v in sorted(Counter(sizes).items())}
    gaps, ratios, adds_profit, add_mins, first_lots = [], [], 0, [], []
    for b in B:
        first_lots.append(b[0]['vol'])
        for a, c in zip(b, b[1:]):
            pt = point_of(raw, a['sym'], a['op'])
            g = (a['op'] - c['op']) / pt if a['side'] == 'BUY' else (c['op'] - a['op']) / pt
            gaps.append(g)
            if g < 0:
                adds_profit += 1
            add_mins.append((c['ot'] - a['ot']) / 60)
            if a['vol'] > 0:
                ratios.append(c['vol'] / a['vol'])
    grid = {}
    if gaps:
        adverse = [g for g in gaps if g > 0]
        grid['adds'] = len(gaps)
        grid['adverse_pct'] = pct(len(adverse), len(gaps))      # ghaate me add (grid/averaging)
        grid['gap_points_median'] = r2(med([abs(g) for g in gaps]), 0)
        grid['gap_cv'] = r2(cv([abs(g) for g in gaps]))
        gm, gn = mode_round([abs(g) for g in gaps], max(1, round((med([abs(g) for g in gaps]) or 10) / 20)))
        grid['gap_common'] = gm
        grid['gap_common_pct'] = pct(gn, len(gaps))
        grid['add_minutes_median'] = r2(med(add_mins), 1)
        grid['lot_ratio_median'] = r2(med(ratios), 2)
        grid['lot_ratio_common'] = r2(Counter(round(r, 2) for r in ratios).most_common(1)[0][0], 2) if ratios else None
        grid['lot_fixed_pct'] = pct(sum(1 for r in ratios if abs(r - 1) < 0.02), len(ratios))
        diffs = [round(c['vol'] - a['vol'], 2) for b in B for a, c in zip(b, b[1:])]
        dc = Counter(diffs).most_common(1)[0] if diffs else (0, 0)
        grid['lot_add_common'] = dc[0]
        grid['lot_add_pct'] = pct(dc[1], len(diffs))
    out['grid'] = grid

    # basket close
    bclose = []
    for b in B:
        if not all(p['closed'] for p in b):
            continue
        cts = [p['ct'] for p in b]
        prof = sum(p['profit'] for p in b)
        vol = sum(p['vol'] for p in b)
        pt = point_of(raw, b[0]['sym'], b[0]['op'])
        avg_op = sum(p['op'] * p['vol'] for p in b) / vol
        cp = sum(p['cp'] * p['vol'] for p in b) / vol
        move = (cp - avg_op) / pt if b[0]['side'] == 'BUY' else (avg_op - cp) / pt
        bclose.append({'n': len(b), 'together': (max(cts) - min(cts)) <= 10, 'profit': prof, 'vol': vol,
                       'move_pts': move, 'reasons': Counter(p.get('reason') for p in b), 'first_vol': b[0]['vol']})
    bm = [x for x in bclose if x['n'] >= 2]
    bc = {}
    if bm:
        bc['multi_baskets'] = len(bm)
        bc['closed_together_pct'] = pct(sum(1 for x in bm if x['together']), len(bm))
        wins_b = [x for x in bm if x['profit'] > 0]
        bc['win_pct'] = pct(len(wins_b), len(bm))
        pw = [x['profit'] for x in wins_b]
        bc['profit_usd_median'] = r2(med(pw))
        bc['profit_usd_cv'] = r2(cv(pw))
        sp = sorted(pw)
        bc['profit_usd_p10'] = r2(sp[len(sp) // 10]) if sp else None
        per01 = [x['profit'] / x['first_vol'] * 0.01 for x in wins_b if x['first_vol']]
        bc['profit_per_001_first_lot_median'] = r2(med(per01))
        bc['profit_per_001_cv'] = r2(cv(per01))
        pv = [x['profit'] / x['vol'] * 0.01 for x in wins_b if x['vol']]
        bc['profit_per_001_total_lot_median'] = r2(med(pv))
        bc['profit_per_001_total_lot_cv'] = r2(cv(pv))
        mv = [x['move_pts'] for x in wins_b]
        bc['avg_price_to_close_pts_median'] = r2(med(mv), 0)
        bc['avg_price_to_close_cv'] = r2(cv(mv))
        bc['worst_basket_usd'] = r2(min(x['profit'] for x in bm))
        rs = Counter()
        for x in bm:
            rs.update(x['reasons'])
        bc['close_reasons'] = dict(rs.most_common())
    out['basket_close'] = bc

    # ---- singles / per-trade TP SL ----
    tpd, sld, real_tp, real_sl = [], [], [], []
    for p in P:
        pt = point_of(raw, p['sym'], p['op'])
        ref = p['oprice'] or p['op']
        if p['tp']:
            tpd.append(abs(p['tp'] - ref) / pt)
        if p['sl']:
            sld.append(abs(ref - p['sl']) / pt)
        if p['closed'] and p.get('reason') == 'TP':
            real_tp.append(abs(p['cp'] - p['op']) / pt)
        if p['closed'] and p.get('reason') == 'SL':
            real_sl.append(((p['cp'] - p['op']) if p['side'] == 'BUY' else (p['op'] - p['cp'])) / pt)
    ex = {'tp_set_pct': pct(len(tpd), n), 'sl_set_pct': pct(len(sld), n)}
    if tpd:
        ex['tp_points_median'] = r2(med(tpd), 0)
        ex['tp_points_cv'] = r2(cv(tpd))
    if sld:
        ex['sl_points_median'] = r2(med(sld), 0)
        ex['sl_points_cv'] = r2(cv(sld))
    if real_sl:
        prof_sl = [x for x in real_sl if x > 0]
        ex['sl_close_in_profit_pct'] = pct(len(prof_sl), len(real_sl))   # trailing / breakeven
        ex['sl_close_profit_pts_median'] = r2(med(prof_sl), 0) if prof_sl else None
    reasons = Counter(p.get('reason') for p in closed)
    ex['close_reasons'] = {k: v for k, v in reasons.most_common()}
    ea_close = [p['profit'] / p['vol'] * 0.01 for p in closed if p.get('reason') == 'EA' and p['profit'] > 0 and p['vol']]
    if ea_close:
        ex['ea_close_profit_per_001_median'] = r2(med(ea_close))
        ex['ea_close_profit_cv'] = r2(cv(ea_close))
    out['exit'] = ex

    # ---- auto lot (balance ke hisaab se?) ----
    bal_ev = sorted([(d['time'], (d.get('profit') or 0) + (d.get('commission') or 0) + (d.get('swap') or 0) + (d.get('fee') or 0))
                     for d in raw['deals']])
    bt = [t for t, _ in bal_ev]
    cum, s = [], 0
    for _, v in bal_ev:
        s += v
        cum.append(s)

    def bal_at(t):
        i = bisect.bisect_left(bt, t) - 1
        return cum[i] if i >= 0 else None
    lr = []
    for b in B:
        bb = bal_at(b[0]['ot'])
        if bb and bb > 0:
            lr.append(bb / b[0]['vol'] * 0.01)
    if len(set(first_lots)) >= 3 and lr and (cv(lr) or 9) < 0.3:
        out['auto_lot'] = {'balance_per_001': r2(med(lr), 0), 'cv': r2(cv(lr))}

    # ---- timing ----
    ent = []            # (decision time, side, price, sym, kind)
    for b in B:
        p = b[0]
        if p['otype'] in ('BUY', 'SELL'):
            ent.append((p['ot'], p['side'], p['op'], p['sym'], 'market'))
    po = [o for o in raw['orders'] if o.get('type') in (2, 3, 4, 5, 6, 7) and o.get('magic', 0) == P[0]['magic']
          and o.get('symbol') in sym_c]
    for o in po:
        ent.append((o['time_setup'], side_of(TYPES[o['type']]), o['price_open'], o['symbol'], 'pending'))
    ent.sort()
    tm = {}
    if ent:
        tl = [e[0] for e in ent]
        tm['server_hours'] = dict(sorted(Counter(datetime.fromtimestamp(t, timezone.utc).hour for t in tl).items()))
        if offset is not None:
            tm['ist_hours'] = dict(sorted(Counter(datetime.fromtimestamp(t - offset * 3600 + 19800, timezone.utc).hour for t in tl).items()))
        tm['weekdays'] = {WD[k]: v for k, v in sorted(Counter(datetime.fromtimestamp(t, timezone.utc).weekday() for t in tl).items())}
        al, best = alignment(tl)
        tm['bar_open_pct'] = al
        tm['entry_tf'] = best
        mins = Counter(datetime.fromtimestamp(t, timezone.utc).strftime('%M') for t in tl)
        tm['top_minutes'] = dict(mins.most_common(4))
        hrs = sorted(tm['server_hours'])
        tm['active_hours_server'] = hour_range(hrs)
        gaps_e = [b - a for a, b in zip(tl, tl[1:]) if b > a]
        tm['min_gap_between_entries_min'] = r2(min(gaps_e) / 60, 1) if gaps_e else None
    out['timing'] = tm

    # ---- pending orders ----
    pd = {}
    if po:
        pd['count'] = len(po)
        pd['types'] = dict(Counter(TYPES[o['type']] for o in po).most_common())
        st = Counter(OSTATE.get(o.get('state'), str(o.get('state'))) for o in po)
        pd['states'] = dict(st.most_common())
        pd['fill_pct'] = pct(st.get('FILLED', 0) + st.get('PARTIAL', 0), len(po))
        dist, life, tpp, slp = [], [], [], []
        for o in po:
            pt = point_of(raw, o['symbol'], o['price_open'])
            bs = bars.get(o['symbol'], {})
            src = bs.get('M1') or bs.get('M5')
            mk = src.price_at(o['time_setup']) if src else None
            if mk:
                dist.append(abs(o['price_open'] - mk) / pt)
            if o.get('state') in (2, 6) and o.get('time_done'):
                life.append((o['time_done'] - o['time_setup']) / 3600)
            if o.get('tp'):
                tpp.append(abs(o['tp'] - o['price_open']) / pt)
            if o.get('sl'):
                slp.append(abs(o['price_open'] - o['sl']) / pt)
        if dist:
            pd['dist_from_market_pts_median'] = r2(med(dist), 0)
            pd['dist_cv'] = r2(cv(dist))
        if life:
            pd['life_hours_median'] = r2(med(life), 1)
        if tpp:
            pd['tp_points_median'] = r2(med(tpp), 0)
        if slp:
            pd['sl_points_median'] = r2(med(slp), 0)
        pairs = 0
        for o in po:
            if any(abs(x['time_setup'] - o['time_setup']) <= 5 and side_of(TYPES[x['type']]) != side_of(TYPES[o['type']])
                   and x['symbol'] == o['symbol'] for x in po):
                pairs += 1
        pd['straddle_pct'] = pct(pairs, len(po))     # buy-stop + sell-stop saath = dono taraf breakout
        # pending price vs pichhli candle high/low
        best = None
        for tf in ('M5', 'M15', 'M30', 'H1', 'H4'):
            vals = []
            for o in po:
                bs = bars.get(o['symbol'], {}).get(tf)
                if not bs:
                    continue
                i = bs.last_closed(o['time_setup'])
                if i is None:
                    continue
                pt = point_of(raw, o['symbol'], o['price_open'])
                ref = bs.h[i] if TYPES[o['type']] in ('BUY_STOP', 'SELL_LIMIT') else bs.l[i]
                vals.append((o['price_open'] - ref) / pt * (1 if TYPES[o['type']] in ('BUY_STOP', 'SELL_LIMIT') else -1))
            if len(vals) >= 5:
                c = cv(vals)
                m = med(vals)
                if c is not None and (best is None or c < best[2]):
                    best = (tf, m, c)
        if best and best[2] < 0.5:
            pd['vs_prev_candle'] = {'tf': best[0], 'beyond_high_low_pts_median': r2(best[1], 0), 'cv': r2(best[2])}
    out['pending'] = pd

    # ---- hedge: dono side ek saath khule? ----
    hb = 0
    for b in B:
        s0, e0 = b[0]['ot'], max(p.get('ct', 10 ** 12) for p in b)
        if any(x[0]['side'] != b[0]['side'] and x[0]['sym'] == b[0]['sym'] and x[0]['ot'] < e0 and
               max(p.get('ct', 10 ** 12) for p in x) > s0 for x in B):
            hb += 1
    out['hedge_overlap_pct'] = pct(hb, len(B))
    pairs_mkt = sum(1 for a, b in zip(P, P[1:]) if abs(b['ot'] - a['ot']) <= 5 and a['side'] != b['side'] and a['sym'] == b['sym'])
    out['buy_sell_same_time'] = pairs_mkt

    # ---- max concurrent ----
    ev = []
    for p in P:
        ev.append((p['ot'], 1))
        if p['closed']:
            ev.append((p['ct'], -1))
    ev.sort()
    c = mx = 0
    for _, d in ev:
        c += d
        mx = max(mx, c)
    out['max_open_together'] = mx
    out['worst_trade_usd'] = r2(min([p['profit'] for p in closed] or [0]))
    # closed-trade drawdown
    s = peak = dd = 0
    for p in sorted(closed, key=lambda p: p['ct']):
        s += p['profit']
        peak = max(peak, s)
        dd = min(dd, s - peak)
    out['closed_dd_usd'] = r2(dd)

    # ---- entry trigger (indicator match) ----
    out['entry_rules'] = entry_rules(ent, bars, main_sym, pd.get('straddle_pct', 0))
    return out, B


def entry_rules(ent, bars, main_sym, straddle_pct):
    res = {'samples': len(ent), 'direction_rules': [], 'filters': [], 'rsi': {}}
    if len(ent) < 5:
        res['note'] = 'Entries bahut kam — indicator rule nikalna mushkil'
        return res
    nb = sum(1 for e in ent if e[1] == 'BUY')
    ns = len(ent) - nb
    for tf in ('M5', 'M15', 'H1'):
        bs = bars.get(main_sym, {}).get(tf)
        if not bs:
            continue
        rows = []
        for t, side, price, sym, kind in ent:
            if sym != main_sym:
                continue
            i = bs.last_closed(t)
            f = bs.feats(i, price)
            if f:
                rows.append((side, f, bs.filters(i, price), bs.rsi[i]))
        if len(rows) < 5:
            continue
        # direction rules (dono side ho tab)
        if nb >= 3 and ns >= 3 and straddle_pct < 50:
            keys = set(k for _, f, _, _ in rows for k in f)
            for k in keys:
                b = [f[k] for s, f, _, _ in rows if s == 'BUY' and k in f]
                se = [f[k] for s, f, _, _ in rows if s == 'SELL' and k in f]
                if len(b) < 3 or len(se) < 3:
                    continue
                tpr = sum(b) / len(b)
                tnr = 1 - sum(se) / len(se)
                acc = (tpr + tnr) / 2
                inv = acc < 0.5
                a = 1 - acc if inv else acc
                res['direction_rules'].append({
                    'tf': tf, 'cond': k, 'mode': 'ulta (reversal)' if inv else 'trend',
                    'rule': (f'{k} → SELL, warna BUY' if inv else f'{k} → BUY, warna SELL'),
                    'match_pct': round(100 * a, 1), 'n': len(b) + len(se)})
        # filters: baseline vs entries
        base = Counter()
        bn = 0
        t0, t1 = ent[0][0], ent[-1][0]
        i0 = bisect.bisect_left(bs.t, t0)
        i1 = bisect.bisect_right(bs.t, t1)
        for i in range(max(i0, 25), min(i1, len(bs.t))):
            fl = bs.filters(i, None)
            if fl:
                bn += 1
                base.update(k for k, v in fl.items() if v)
        if bn >= 30:
            for side in ('BUY', 'SELL'):
                L = [fl for s, _, fl, _ in rows if s == side and fl]
                if len(L) < 5:
                    continue
                for k in L[0]:
                    r = sum(1 for fl in L if fl.get(k)) / len(L)
                    b0 = base[k] / bn
                    if abs(r - b0) >= 0.2:
                        res['filters'].append({'tf': tf, 'side': side, 'cond': k, 'entries_pct': round(100 * r, 1),
                                               'normal_pct': round(100 * b0, 1), 'n': len(L)})
        for side in ('BUY', 'SELL'):
            rv = [x for s, _, _, x in rows if s == side and x is not None]
            if len(rv) >= 3:
                res['rsi'].setdefault(tf, {})[side] = {'median': round(med(rv), 1), 'min': round(min(rv), 1), 'max': round(max(rv), 1)}
    res['direction_rules'].sort(key=lambda r: (-r['match_pct'], -r['n']))
    res['direction_rules'] = res['direction_rules'][:6]
    res['filters'].sort(key=lambda r: -abs(r['entries_pct'] - r['normal_pct']))
    res['filters'] = res['filters'][:6]
    if straddle_pct >= 50:
        res['note'] = 'Dono taraf (buy stop + sell stop) order saath lagte hain — direction ka rule nahi, ye breakout/straddle hai'
    elif nb < 3 or ns < 3:
        res['note'] = f'Lagbhag ek hi side (BUY {nb} / SELL {ns}) — direction rule nahi, filters dekho'
    return res


# ---------------- summary (Hinglish) ----------------
def summarize(g, raw, magic):
    S, inputs = [], {}
    sym = next(iter(g['symbols']))
    gr, bc, ex, tm, pdg, er = g['grid'], g['basket_close'], g['exit'], g['timing'], g['pending'], g['entry_rules']
    is_pend = pdg.get('count', 0) >= max(3, 0.3 * g['trades'])
    regular = (gr.get('gap_cv') is not None and gr['gap_cv'] < 0.5) or gr.get('gap_common_pct', 0) >= 50
    is_grid = g['basket_pct'] >= 20 and gr.get('adverse_pct', 0) >= 60 and (regular or not is_pend)
    is_pyr = g['basket_pct'] >= 20 and gr.get('adverse_pct', 100) <= 40 and regular
    lot_step = gr.get('lot_add_pct', 0) >= 40 and (gr.get('lot_add_common') or 0) > 0
    is_marti = bool(gr.get('lot_ratio_median') and gr['lot_ratio_median'] >= 1.1) and \
        ((gr.get('lot_ratio_common') or 1) >= 1.1 or not lot_step)
    straddle = pdg.get('straddle_pct', 0) >= 50
    kind = []
    if is_pend:
        kind.append('Pending order (' + ', '.join(k.replace('_', ' ') for k in list(pdg['types'])[:2]) + ')')
        if pdg.get('straddle_pct', 0) >= 50:
            kind.append('dono taraf breakout (straddle)')
    if is_grid:
        kind.append('Grid / averaging')
    if is_pyr:
        kind.append('Profit me add (pyramiding)')
    if is_marti:
        kind.append('Martingale (lot × %s)' % gr['lot_ratio_median'])
    if g['hedge_overlap_pct'] >= 30 and not straddle:
        kind.append('Hedge (buy + sell ek saath)' if g['hedge_overlap_pct'] < 80 else 'Dono side alag grid (BUY basket + SELL basket saath chalte)')
    if not kind:
        kind.append('Single trade (ek signal = ek trade)')
    S.append(['EA type', ' + '.join(kind), conf(g['trades'], 0.9)])
    share = list(g['symbols'].values())[0] / g['trades']
    S.append(['Symbol', f"{sym} ({round(100 * share)}% trades)" + (f" + {len(g['symbols']) - 1} aur" if len(g['symbols']) > 1 else ''), 'pakka'])
    inputs['Symbol'] = sym
    inputs['Magic'] = magic
    S.append(['Direction', f"BUY {g['buy']} / SELL {g['sell']}", 'pakka'])

    if tm.get('entry_tf'):
        S.append(['Entry kab', f"{tm['entry_tf']} candle khulte hi ({tm['bar_open_pct'][tm['entry_tf']]}% entries candle ke pehle 10 sec me)",
                  conf(er['samples'], tm['bar_open_pct'][tm['entry_tf']] / 100)])
        inputs['Timeframe'] = tm['entry_tf']
    elif tm:
        S.append(['Entry kab', 'Candle open se nahi — tick par / beech me (price level ya condition par)', conf(er['samples'], 0.7)])
    if tm.get('ist_hours'):
        h = sorted(tm['ist_hours'])
        if len(h) <= 18:
            S.append(['Trading time (IST)', f"{hour_range(h)} (entry wale ghante: {', '.join(str(x) for x in h)})", conf(er['samples'], 0.7)])
        else:
            S.append(['Trading time', 'Lagbhag poore din (koi time filter nahi dikhta)', conf(er['samples'], 0.6)])
    elif tm.get('active_hours_server'):
        S.append(['Trading time (server)', tm['active_hours_server'], conf(er['samples'], 0.6)])

    if er.get('direction_rules'):
        r = er['direction_rules'][0]
        S.append(['Direction rule (andaaza)', f"{r['rule']} [{r['tf']}] — {r['match_pct']}% entries se match", conf(r['n'], r['match_pct'] / 100)])
        if r['match_pct'] >= 70:
            inputs['EntryRule'] = f"{r['tf']}: {r['rule']}"
    for f in er.get('filters', [])[:2]:
        S.append(['Filter (andaaza)', f"{f['side']} entries me '{f['cond']}' {f['entries_pct']}% (normal {f['normal_pct']}%) [{f['tf']}]", conf(f['n'], 0.7)])
    if er.get('note'):
        S.append(['Note', er['note'], ''])

    lots = g['lots']
    if g.get('auto_lot'):
        S.append(['Lot', f"Auto: har ${g['auto_lot']['balance_per_001']} balance par 0.01 lot", conf(g['baskets'], strength(g['auto_lot']['cv']))])
        inputs['RiskBalancePer001'] = g['auto_lot']['balance_per_001']
    else:
        S.append(['Lot', f"Shuru {lots['common']} (min {lots['min']}, max {lots['max']})", 'pakka'])
        inputs['StartLot'] = lots['common']
    if gr and (is_grid or is_pyr or is_marti or lot_step):
        if is_grid or is_pyr:
            gap = gr['gap_common'] if gr.get('gap_common_pct', 0) >= 40 else gr['gap_points_median']
            S.append(['Grid gap', f"≈ {gap} points ({'ghaate me' if is_grid else 'profit me'} add, {gr['adverse_pct']}% adverse) — har add ~{gr['add_minutes_median']} min baad",
                      conf(gr['adds'], strength(gr.get('gap_cv')))])
            inputs['GridGapPoints'] = gap
        if is_marti:
            S.append(['Lot badhna', f"× {gr['lot_ratio_common'] or gr['lot_ratio_median']} har level", conf(gr['adds'], 0.8)])
            inputs['LotMultiplier'] = gr['lot_ratio_common'] or gr['lot_ratio_median']
        elif lot_step:
            S.append(['Lot badhna', f"+{gr['lot_add_common']} har level ({gr['lot_add_pct']}% adds), kabhi same lot ({gr.get('lot_fixed_pct', 0)}%)", conf(gr['adds'], gr['lot_add_pct'] / 100)])
            inputs['LotStep'] = gr['lot_add_common']
        S.append(['Max levels', f"{g['levels_max']} (avg {g['levels_avg']})", 'pakka'])
        inputs['MaxLevels'] = g['levels_max']

    if bc:
        if bc['closed_together_pct'] >= 70:
            t = f"Basket ek saath band ({bc['closed_together_pct']}%)"
            tl = bc.get('profit_per_001_total_lot_cv')
            if tl is not None and tl < 0.35 and tl < (bc.get('profit_per_001_cv') or 9) and tl < (bc.get('avg_price_to_close_cv') or 9):
                t += f" — target ≈ ${bc['profit_per_001_total_lot_median']} har 0.01 total lot par (basket jitna bada, target utna bada)"
                inputs['BasketTargetUSD_perTotal001'] = bc['profit_per_001_total_lot_median']
            elif (bc.get('profit_per_001_cv') or 9) < (bc.get('avg_price_to_close_cv') or 9) and (bc.get('profit_per_001_cv') or 9) < 0.35:
                t += f" — target ≈ ${bc['profit_per_001_first_lot_median']} per 0.01 first lot (median ${bc['profit_usd_median']})"
                inputs['BasketTargetUSD_per001'] = bc['profit_per_001_first_lot_median']
            elif (bc.get('avg_price_to_close_cv') or 9) < 0.35:
                t += f" — avg price se {bc['avg_price_to_close_pts_median']} points profit par"
                inputs['BasketTPPointsFromAvg'] = bc['avg_price_to_close_pts_median']
            elif bc.get('profit_usd_p10') and bc['profit_usd_median'] and bc['profit_usd_p10'] / bc['profit_usd_median'] >= 0.6:
                t += f" — basket profit ≈ ${bc['profit_usd_p10']} hote hi band (median ${bc['profit_usd_median']})"
                inputs['BasketTargetUSD'] = bc['profit_usd_p10']
            else:
                t += f" — profit median ${bc['profit_usd_median']}"
            S.append(['Basket exit', t, conf(bc['multi_baskets'], bc['closed_together_pct'] / 100)])
    if ex.get('tp_points_median'):
        S.append(['TP', f"≈ {ex['tp_points_median']} points ({ex['tp_set_pct']}% trades par TP)", conf(g['trades'], strength(ex.get('tp_points_cv')))])
        inputs['TPPoints'] = ex['tp_points_median']
    if ex.get('sl_points_median'):
        S.append(['SL', f"≈ {ex['sl_points_median']} points ({ex['sl_set_pct']}% trades par SL)", conf(g['trades'], strength(ex.get('sl_points_cv')))])
        inputs['SLPoints'] = ex['sl_points_median']
    elif g['trades']:
        S.append(['SL', 'SL nahi lagta (0%) — risk zyada', 'pakka'])
    if ex.get('sl_close_in_profit_pct', 0) >= 25:
        S.append(['Trailing / BE', f"{ex['sl_close_in_profit_pct']}% SL-close profit me — trailing/breakeven lagta hai (median {ex['sl_close_profit_pts_median']} pts lock)", conf(g['trades'], 0.7)])
    if ex.get('ea_close_profit_per_001_median') and (ex.get('ea_close_profit_cv') or 9) < 0.4:
        S.append(['EA khud band', f"≈ ${ex['ea_close_profit_per_001_median']} per 0.01 lot profit par (fixed $ target)", conf(g['trades'], 0.7)])
    if pdg.get('dist_from_market_pts_median'):
        t = f"Market se ≈ {pdg['dist_from_market_pts_median']} points door"
        if pdg.get('vs_prev_candle'):
            v = pdg['vs_prev_candle']
            t += f"; {v['tf']} pichhli candle high/low se {v['beyond_high_low_pts_median']} points aage"
        if pdg.get('life_hours_median'):
            t += f"; na lage to ~{pdg['life_hours_median']} ghante me cancel/expire"
        S.append(['Pending order', t + ('' if raw.get('platform') == 'MT4' else f" (fill {pdg['fill_pct']}%)"), conf(pdg['count'], max(strength(pdg.get('dist_cv')), strength((pdg.get('vs_prev_candle') or {}).get('cv'))))])
        inputs['PendingDistancePoints'] = pdg['dist_from_market_pts_median']
        if pdg.get('life_hours_median'):
            inputs['PendingExpiryHours'] = pdg['life_hours_median']
    S.append(['Risk', f"Max {g['max_open_together']} trade ek saath · sabse bada loss ${g['worst_trade_usd']} · closed DD ${g['closed_dd_usd']}", 'pakka'])
    S.append(['Result', f"Net ${g['net']} · jeet {g['win_pct']}% · PF {g['pf']} · {g['trades_per_day']} trade/din", 'pakka'])
    return S, inputs


def md_report(st):
    L = [f"# Strategy Scan ({st.get('platform', 'MT5')}) — {st['account']['login']} ({st['account'].get('server', '')})",
         f"Scan: {st['scanned']} UTC · history {st['period']} · {st['total_trades']} trades · balance {st['account'].get('balance')} {st['account'].get('currency', '')}",
         '', '> Ye sab trade history se nikala andaaza hai (EA ka asli code nahi). "pakka" = data se saaf dikh raha, "kamzor" = kam data.', '']
    for G in st['eas']:
        L.append(f"## EA magic {G['magic']} — {G['trades']} trades")
        L.append('| Cheez | Kya mila | Bharosa |')
        L.append('|---|---|---|')
        for k, v, c in G['summary']:
            L.append(f'| {k} | {v} | {c} |')
        L.append('')
        if G['inputs']:
            L.append('**Clone EA ke liye inputs (andaaza):**')
            L.append('```')
            for k, v in G['inputs'].items():
                L.append(f'{k} = {v}')
            L.append('```')
        er = G['detail']['entry_rules']
        if er.get('direction_rules'):
            L.append('**Direction rules (top match):**')
            for r in er['direction_rules']:
                L.append(f"- [{r['tf']}] {r['rule']} — {r['match_pct']}% ({r['n']} entries, {r['mode']})")
        if er.get('filters'):
            L.append('**Filters (entries vs normal market):**')
            for f in er['filters']:
                L.append(f"- [{f['tf']}] {f['side']}: {f['cond']} — entries me {f['entries_pct']}%, normal {f['normal_pct']}%")
        if er.get('rsi'):
            L.append('**RSI14 entry par:** ' + '; '.join(f"{tf} " + ', '.join(f"{s} med {v['median']} ({v['min']}–{v['max']})" for s, v in d.items()) for tf, d in er['rsi'].items()))
        tm = G['detail']['timing']
        if tm.get('ist_hours'):
            L.append('**Entries ghante ke hisaab se (IST):** ' + ', '.join(f'{h}:00={n}' for h, n in tm['ist_hours'].items()))
        if tm.get('weekdays'):
            L.append('**Din:** ' + ', '.join(f'{d}={n}' for d, n in tm['weekdays'].items()))
        L.append('')
    if st.get('other_trades'):
        L.append(f"Baaki chhote groups / manual trades: {st['other_trades']}")
    L.append('')
    L.append('_Raw detail: strategy.json_')
    return '\n'.join(L)


def compat_files(raw, outdir, masked):
    """app ke Live / History / Behaviour tab ke liye (agar Reader EA ki file nahi hai)"""
    def own(path):
        if not os.path.exists(path):
            return True
        try:
            return json.load(open(path, encoding='utf-8')).get('src') == 'scan'
        except Exception:
            return False
    a = raw['acct']
    if own(os.path.join(outdir, 'live.json')):
        live = {'src': 'scan', 'login': masked, 'server': a.get('server'), 'company': a.get('company'), 'currency': a.get('currency'),
                'balance': a.get('balance'), 'equity': a.get('equity'), 'margin': a.get('margin'), 'floating': a.get('profit'),
                'updatedAt': ts(raw['fetched_at']) + ' (scan)',
                'positions': [{'ticket': x['ticket'], 'symbol': x['symbol'], 'type': 'BUY' if x['type'] == 0 else 'SELL', 'volume': x['volume'],
                               'open': x['price_open'], 'price': x['price_current'], 'sl': x['sl'], 'tp': x['tp'], 'profit': x['profit'],
                               'magic': x['magic'], 'comment': x['comment'], 'time': ts(x['time'])} for x in raw['positions']],
                'orders': [{'ticket': x['ticket'], 'symbol': x['symbol'], 'type': TYPES.get(x['type'], str(x['type'])), 'volume': x['volume_current'],
                            'price': x['price_open'], 'sl': x['sl'], 'tp': x['tp'], 'market': x['price_current'], 'magic': x['magic'],
                            'comment': x['comment'], 'time': ts(x['time_setup'])} for x in raw['pending']]}
        json.dump(live, open(os.path.join(outdir, 'live.json'), 'w', encoding='utf-8'), separators=(',', ':'))
    if own(os.path.join(outdir, 'history.json')):
        dl = [d for d in raw['deals'] if d.get('type') in (0, 1) and d.get('symbol')][-3000:]
        ol = [o for o in raw['orders'] if o.get('symbol')][-3000:]
        days = raw.get('days') or (round((raw['fetched_at'] - dl[0]['time']) / 86400) if dl else 0)
        hist = {'src': 'scan', 'days': days,
                'deals': [{'ticket': d['ticket'], 'time': ts(d['time']), 'symbol': d['symbol'], 'type': 'BUY' if d['type'] == 0 else 'SELL',
                           'entry': ENTRY.get(d['entry'], str(d['entry'])), 'volume': d['volume'], 'price': d['price'],
                           'profit': round((d.get('profit') or 0) + (d.get('commission') or 0) + (d.get('swap') or 0), 2),
                           'magic': d.get('magic', 0), 'comment': d.get('comment', ''), 'position': d.get('position_id'),
                           'reason': REASON.get(d.get('reason'), '')} for d in dl],
                'orders': [{'ticket': o['ticket'], 'symbol': o['symbol'], 'type': TYPES.get(o['type'], str(o['type'])),
                            'state': OSTATE.get(o.get('state'), str(o.get('state'))), 'volume': o.get('volume_initial'), 'price': o.get('price_open'),
                            'sl': o.get('sl'), 'tp': o.get('tp'), 'magic': o.get('magic', 0), 'comment': o.get('comment', ''),
                            'setup': ts(o['time_setup']), 'done': ts(o['time_done']) if o.get('time_done') else ''} for o in ol]}
        json.dump(hist, open(os.path.join(outdir, 'history.json'), 'w', encoding='utf-8'), separators=(',', ':'))


def main():
    rawp, outdir = sys.argv[1], sys.argv[2]
    stp = os.path.join(os.path.dirname(rawp), 'status.json')

    def status(stage, ok, msg=''):
        json.dump({'stage': stage, 'ok': ok, 'msg': msg, 'at': int(time.time())}, open(stp, 'w'))
        print(('OK ' if ok else 'ERROR ') + stage, msg)
    try:
        raw = json.load(open(rawp, encoding='utf-8'))
        os.makedirs(outdir, exist_ok=True)
        login = str(raw['acct'].get('login', ''))
        masked = '***' + login[-3:]
        offset = raw.get('server_offset_h')
        compat_files(raw, outdir, masked)
        bars = {}
        for s, d in raw.get('candles', {}).items():
            bars[s] = {tf: Bars(rows, tf) for tf, rows in d.items() if rows and len(rows) > 30}
        P = build_positions(raw)
        a = raw['acct']
        st = {'src': 'scan', 'ver': '1.09.3', 'platform': raw.get('platform', 'MT5'), 'scanned': ts(time.time()),
              'account': {'login': masked, 'server': a.get('server'), 'company': a.get('company'), 'currency': a.get('currency'),
                          'balance': a.get('balance'), 'equity': a.get('equity'), 'leverage': a.get('leverage'),
                          'type': {0: 'DEMO', 1: 'CONTEST', 2: 'REAL'}.get(a.get('trade_mode'), '?'),
                          'investor': not a.get('trade_allowed', True)},
              'server_offset_h': offset, 'total_trades': len(P),
              'period': (ts(P[0]['ot'])[:10] + ' → ' + ts(P[-1]['ot'])[:10]) if P else '-',
              'open_now': len(raw.get('positions', [])), 'pending_now': len(raw.get('pending', [])),
              'deposits': r2(sum(d.get('profit') or 0 for d in raw['deals'] if d.get('type') == 2 and (d.get('profit') or 0) > 0)),
              'withdrawals': r2(sum(d.get('profit') or 0 for d in raw['deals'] if d.get('type') == 2 and (d.get('profit') or 0) < 0)),
              'eas': []}
        if not P:
            st['note'] = 'Is account me koi trade history nahi mili'
        elif st['platform'] == 'MT4':
            st['note'] = 'MT4: lage hue pending orders history me BUY/SELL ban jaate hain (pending setup time nahi milta) — pending analysis sirf cancel/expire wale orders se.'
        mg = Counter(p['magic'] for p in P)
        other = 0
        for magic, n in mg.most_common():
            G = [p for p in P if p['magic'] == magic]
            if n < 3 or len(st['eas']) >= 4:
                other += n
                continue
            det, _ = analyse_group(raw, G, bars, offset)
            summ, inputs = summarize(det, raw, magic)
            cms = Counter(''.join('#' if ch.isdigit() else ch for ch in (p['cm'] or '')) for p in G).most_common(3)
            st['eas'].append({'magic': magic, 'manual': magic == 0, 'trades': n, 'comments': [c for c, _ in cms if c],
                              'summary': summ, 'inputs': inputs, 'detail': det})
        st['other_trades'] = other
        json.dump(st, open(os.path.join(outdir, 'strategy.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        open(os.path.join(outdir, 'STRATEGY.md'), 'w', encoding='utf-8').write(md_report(st))
        if os.path.exists(os.path.join(outdir, 'KEEP_RAW')):     # sirf jab Claude ko deep analysis chahiye (baad me hata dete hain)
            import gzip
            with gzip.open(os.path.join(outdir, 'raw.json.gz'), 'wt', encoding='utf-8') as gz:
                json.dump(raw, gz, separators=(',', ':'))
        status('done', True, f"{len(P)} trades, {len(st['eas'])} EA group")
    except Exception as e:
        import traceback
        traceback.print_exc()
        status('analyse', False, type(e).__name__ + ': ' + str(e)[:300])
        sys.exit(1)


if __name__ == '__main__':
    main()
