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
summary = {
    'last_signal_at': rows[-1]['at'] if rows else None,
    'total': stats(rows),
    'by_grade': group(lambda r: r.get('grade') or '?'),
    'by_ai': group(ai_key),
    'by_pair': group(lambda r: r.get('sym') or '?'),
    'by_dir': group(lambda r: r.get('dir') or '?'),
    'sent_to_mt5': group(lambda r: 'yes' if r.get('mt5') else 'no'),
}
json.dump(rows, open(os.path.join(out, 'paper.json'), 'w'), ensure_ascii=False, indent=1)
json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), ensure_ascii=False, indent=1)
print(f"{len(rows)} paper trades, win rate {summary['total']['win_rate']}")
