"""SAMUSIGNAL AI paper trades -> data/paper/paper.json (saare trades) + summary.json (hisaab).
Input: Firebase /samuai/paper.json ({id: row} ya null). Output me "abhi ka samay" nahi — taaki bina badlav commit na ho."""
import json, sys, os
src, out = sys.argv[1], sys.argv[2]
raw = json.load(open(src)) or {}
rows = sorted((r for r in raw.values() if isinstance(r, dict) and r.get('id')), key=lambda r: r.get('at') or 0)
os.makedirs(out, exist_ok=True)

def state(r): return ((r.get('res') or {}).get('state')) or 'PENDING'
def stats(rs):
    win = sum(1 for r in rs if state(r).startswith('TP')); loss = sum(1 for r in rs if state(r) == 'SL')
    exp = sum(1 for r in rs if state(r) == 'EXPIRED'); live = len(rs) - win - loss - exp
    pips = sum(((r.get('res') or {}).get('pips') or 0) for r in rs if state(r).startswith('TP') or state(r) == 'SL')
    fin = win + loss
    return {'signals': len(rs), 'win': win, 'loss': loss, 'expired': exp, 'open_or_pending': live,
            'win_rate': round(100 * win / fin, 1) if fin else None, 'net_pips': round(pips, 1)}
def group(key):
    g = {}
    for r in rows: g.setdefault(key(r), []).append(r)
    return {k: stats(v) for k, v in sorted(g.items(), key=lambda kv: str(kv[0]))}
def ai_key(r):
    a = r.get('ai')
    return 'none' if not a else ('agree' if a.get('agree') else 'disagree')
def mstate(r):
    m = r.get('mkt') or {}
    return ((m.get('res') or {}).get('state')) or 'OPEN'
def mstats(rs):
    rs = [r for r in rs if r.get('mkt')]
    win = sum(1 for r in rs if mstate(r).startswith('TP')); loss = sum(1 for r in rs if mstate(r) == 'SL')
    fin = win + loss
    usd = sum((((r.get('mkt') or {}).get('res') or {}).get('usd') or 0) for r in rs if mstate(r).startswith('TP') or mstate(r) == 'SL')
    return {'signals': len(rs), 'win': win, 'loss': loss, 'open': len(rs) - fin,
            'win_rate': round(100 * win / fin, 1) if fin else None, 'usd': round(usd, 2)}
def lusd(rs):
    return round(sum(((r.get('res') or {}).get('usd') or 0) for r in rs if state(r).startswith('TP') or state(r) == 'SL'), 2)
def tstate(r): return ((r.get('trail') or {}).get('state')) or 'PENDING'
def tstats(rs):
    rs = [r for r in rs if r.get('trail')]
    tp = sum(1 for r in rs if tstate(r).startswith('TP')); lk = sum(1 for r in rs if tstate(r) == 'LOCK'); loss = sum(1 for r in rs if tstate(r) == 'SL')
    fin = tp + lk + loss
    usd = sum(((r.get('trail') or {}).get('usd') or 0) for r in rs if tstate(r) in ('TP1', 'LOCK', 'SL'))
    return {'signals': len(rs), 'tp': tp, 'lock': lk, 'loss': loss, 'win_rate': round(100 * (tp + lk) / fin, 1) if fin else None, 'usd': round(usd, 2)}
# v1.9: 🧠 AI Council (6 bot + jaj) — apna paper hisaab + hamare signal ka nateeja Council ke faisle ke hisaab se
def cstate(r): return (((r.get('council') or {}).get('res') or {}).get('state')) or 'PENDING'
def cstats(rs):
    rs = [r for r in rs if r.get('council')]
    win = sum(1 for r in rs if cstate(r).startswith('TP')); loss = sum(1 for r in rs if cstate(r) == 'SL')
    fin = win + loss
    usd = sum((((r.get('council') or {}).get('res') or {}).get('usd') or 0) for r in rs if cstate(r).startswith('TP') or cstate(r) == 'SL')
    return {'signals': len(rs), 'win': win, 'loss': loss, 'open_or_pending': len(rs) - fin,
            'win_rate': round(100 * win / fin, 1) if fin else None, 'usd': round(usd, 2)}
def verdict(r):
    c = r.get('council')
    if not c: return 'none'
    d = r.get('dir') or ''; views = [x.split(':')[1] for x in (c.get('bots') or '').split() if ':' in x]
    v = sum(1 for x in views if x == d[:1]); w = sum(1 for x in views if x == 'W'); conf = c.get('conf') or 0
    if c.get('dir') != d: return 'no'          # Council ulta
    if w >= 3 or conf < 55: return 'wait'
    if v >= 4 and conf >= 65: return 'yes'
    return 'weak'
crows = [r for r in rows if r.get('council')]
rule_ok = [r for r in rows if (r.get('mkt') or {}).get('ok')]
rule_no = [r for r in rows if r.get('mkt') and not (r.get('mkt') or {}).get('ok')]
summary = {
    'last_signal_at': rows[-1]['at'] if rows else None,
    'total': stats(rows),
    'by_grade': group(lambda r: r.get('grade') or '?'),
    'by_ai': group(ai_key),
    'by_pair': group(lambda r: r.get('sym') or '?'),
    'by_dir': group(lambda r: r.get('dir') or '?'),
    'sent_to_mt5': group(lambda r: 'yes' if r.get('mt5') else 'no'),
    'limit_usd': lusd(rows),
    # v1.8.0: 🔒 Trail niyam ($0.50 pe $0.25 lock, har $0.10) — usi LIMIT trade pe alag hisaab
    'trail_vs_tp1': {'tp1': stats([r for r in rows if r.get('trail')]), 'tp1_usd': lusd([r for r in rows if r.get('trail')]), 'trail': tstats(rows)},
    'council': {
        'all': cstats(crows),
        'by_order': {k: cstats([r for r in crows if (r['council'].get('order') or 'LIMIT') == k]) for k in ('LIMIT', 'MARKET')},
        'agree': cstats([r for r in crows if r['council'].get('dir') == r.get('dir')]),
        'disagree': cstats([r for r in crows if r['council'].get('dir') != r.get('dir')]),
        # hamara LIMIT signal ka nateeja, Council ke aakhri faisle ke hisaab se (yes/weak/wait/no)
        'our_signal_by_verdict': {k: dict(stats([r for r in crows if verdict(r) == k]), usd=lusd([r for r in crows if verdict(r) == k])) for k in ('yes', 'weak', 'wait', 'no')},
    },
    # v1.7.0: LIMIT banaam MARKET (paper hisaab). rule_ok = niyam ne MARKET kaha tha
    'limit_vs_market': {
        'all': {'limit': stats([r for r in rows if r.get('mkt')]), 'limit_usd': lusd([r for r in rows if r.get('mkt')]), 'market': mstats(rows)},
        'rule_ok': {'limit': stats(rule_ok), 'limit_usd': lusd(rule_ok), 'market': mstats(rule_ok)},
        'rule_no': {'limit': stats(rule_no), 'limit_usd': lusd(rule_no), 'market': mstats(rule_no)},
    },
}
json.dump(rows, open(os.path.join(out, 'paper.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), ensure_ascii=False, indent=1)
print(f"{len(rows)} paper trades, win rate {summary['total']['win_rate']}")
