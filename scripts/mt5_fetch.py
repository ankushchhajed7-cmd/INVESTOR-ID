# Investor Watch v1.08 — MT5 se data nikalna (GitHub Actions Windows runner par chalta hai)
# Investor (read-only) login se: account info, poori deal + order history, open trades,
# pending orders, symbol info, candles (M1/M5/M15/H1).  Kabhi trade NAHI karta.
#
# Password: workflow input me sirf ENCRYPTED aata hai (AES-GCM, key = repo secret IW_KEY).
# Yahin decrypt hota hai, kahin print / save nahi hota.
#
# Usage: python scripts/mt5_fetch.py <terminal64.exe path> <out_dir>
#   env: IW_LOGIN, IW_SERVER, IW_ENC, IW_KEY, IW_DAYS (0 = sab)
import base64, json, os, sys, time
from datetime import datetime, timedelta, timezone

OUT = sys.argv[2] if len(sys.argv) > 2 else 'scan_tmp'
os.makedirs(OUT, exist_ok=True)


def status(stage, ok=True, msg=''):
    json.dump({'stage': stage, 'ok': ok, 'msg': msg, 'at': int(time.time())},
              open(os.path.join(OUT, 'status.json'), 'w'))
    print(('OK ' if ok else 'ERROR ') + stage + (': ' + msg if msg else ''), flush=True)


def fail(stage, msg):
    status(stage, False, msg)
    sys.exit(1)


def decrypt(enc_b64, passphrase):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    raw = base64.b64decode(enc_b64.strip())
    salt, iv, ct = raw[:16], raw[16:28], raw[28:]
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=150000).derive(passphrase.encode())
    return AESGCM(key).decrypt(iv, ct, None).decode()


def nt(x):
    """MT5 namedtuple -> plain dict (json-safe)."""
    d = x._asdict()
    for k, v in list(d.items()):
        if isinstance(v, bytes):
            d[k] = v.decode(errors='ignore')
        elif not isinstance(v, (int, float, str, bool, type(None))):
            d[k] = str(v)
    return d


def main():
    term = sys.argv[1]
    login = os.environ.get('IW_LOGIN', '').strip()
    server = os.environ.get('IW_SERVER', '').strip()
    enc = os.environ.get('IW_ENC', '').strip()
    key = os.environ.get('IW_KEY', '')
    days = int(os.environ.get('IW_DAYS', '0') or 0)
    if not login.isdigit():
        fail('input', 'Login sirf number hona chahiye')
    if not server:
        fail('input', 'Server naam khaali hai')
    if not key:
        fail('input', 'Repo secret IW_KEY set nahi hai (Settings > Secrets > Actions)')
    try:
        pw = decrypt(enc, key)
    except Exception:
        fail('password', 'Password decrypt nahi hua — app me Secret key wahi daalo jo repo secret IW_KEY me hai')
    print('::add-mask::' + pw, flush=True)

    import MetaTrader5 as mt5
    status('login')
    ok = False
    err = None
    for i in range(4):
        if mt5.initialize(path=term, login=int(login), password=pw, server=server, timeout=180000):
            ok = True
            break
        err = mt5.last_error()
        print('initialize try', i + 1, 'failed:', err, flush=True)
        mt5.shutdown()
        time.sleep(15)
    if not ok:
        hint = ''
        if err and err[0] in (-6, -10003, -10004, -10005):
            hint = ' — password galat/badal gaya, ya server naam galat. Agar server sahi hai to broker ka apna MT5 installer link do.'
        fail('login', 'MT5 login nahi hua ' + str(err) + hint)

    ai = mt5.account_info()
    if ai is None:
        fail('login', 'account_info nahi mila ' + str(mt5.last_error()))
    acct = nt(ai)
    for k in ('name', 'password'):
        acct.pop(k, None)                      # naam / koi secret save nahi
    # ---- v1.12 MT5 LIVE RECORD (pehle record, phir history - taaki record ke trade bhi history me aayen) ----
    rec_min = int(os.environ.get('IW_RECORD', '0') or 0)
    if rec_min > 0:
        rs = (os.environ.get('IW_RECSYM', '') or '').strip()
        # v1.12.1: login ke turant baad history khaali aati hai -> 'XAUUSD' (broker par .e) = 0 tick. Ab intezaar + asli symbol khojo
        from collections import Counter
        cnt = Counter()
        for _ in range(8):
            d0 = mt5.history_deals_get(datetime(2010, 1, 1, tzinfo=timezone.utc), datetime.now(timezone.utc) + timedelta(days=2)) or []
            cnt = Counter(x.symbol for x in d0 if x.symbol)
            if cnt:
                break
            time.sleep(10)
        if not rs and cnt:
            rs = cnt.most_common(1)[0][0]
        if not rs or mt5.symbol_info(rs) is None:                  # naam broker par nahi mila -> milta-julta khojo
            base = (rs or 'XAUUSD').upper().split('.')[0][:6]
            cands = [x.name for x in (mt5.symbols_get('*' + base[:3] + '*') or []) if x.name.upper().startswith(base)]
            print('record symbol khoj:', rs, '->', cands[:5], flush=True)
            if cands:
                rs = sorted(cands, key=len)[0]
        print('record symbol:', rs, 'deals mile:', sum(cnt.values()), flush=True)
        try:
            mt5_record(mt5, rec_min, rs)
        except Exception as e:
            print('record error:', type(e).__name__, str(e)[:200], flush=True)
    status('history')

    now = datetime.now(timezone.utc) + timedelta(days=2)
    start = datetime(2010, 1, 1, tzinfo=timezone.utc) if days <= 0 else now - timedelta(days=days + 2)
    deals, orders = [], []
    for i in range(3):                         # history sync me thoda time lagta hai
        d = mt5.history_deals_get(start, now) or []
        o = mt5.history_orders_get(start, now) or []
        if len(d) >= len(deals):
            deals, orders = d, o
        time.sleep(4)
    deals = [nt(x) for x in deals]
    orders = [nt(x) for x in orders]
    positions = [nt(x) for x in (mt5.positions_get() or [])]
    pending = [nt(x) for x in (mt5.orders_get() or [])]
    print('deals', len(deals), 'orders', len(orders), 'open', len(positions), 'pending', len(pending), flush=True)

    syms = sorted({x['symbol'] for x in deals + orders + positions + pending if x.get('symbol')})
    symbols, candles = {}, {}
    offset = None
    status('candles')
    first_t = min([x['time'] for x in deals if x.get('symbol')] + [x['time_setup'] for x in orders if x.get('symbol')] + [int(time.time())])
    for s in syms[:12]:
        mt5.symbol_select(s, True)
        si = mt5.symbol_info(s)
        if si is None:
            continue
        symbols[s] = {'point': si.point, 'digits': si.digits, 'contract': si.trade_contract_size,
                      'tick_value': si.trade_tick_value, 'tick_size': si.trade_tick_size,
                      'vol_min': si.volume_min, 'vol_step': si.volume_step, 'spread': si.spread}
        tk = mt5.symbol_info_tick(s)
        if tk and tk.time and offset is None:      # server time - UTC (market band ho to tick purana = skip)
            off = (tk.time - time.time()) / 3600.0
            if -12.5 <= off <= 14.5 and abs(off * 2 - round(off * 2)) < 0.1:
                offset = round(off * 2) / 2
        c = {}
        frm = datetime.fromtimestamp(max(first_t - 5 * 86400, 0), timezone.utc)
        for name, tf, cap_days in (('M1', mt5.TIMEFRAME_M1, 60), ('M5', mt5.TIMEFRAME_M5, 3650),
                                   ('M15', mt5.TIMEFRAME_M15, 3650), ('H1', mt5.TIMEFRAME_H1, 3650)):
            f = max(frm, now - timedelta(days=cap_days))
            rates = None
            for i in range(3):
                rates = mt5.copy_rates_range(s, tf, f, now)
                if rates is not None and len(rates):
                    break
                time.sleep(3)
            if rates is None:
                continue
            c[name] = [[int(r['time']), float(r['open']), float(r['high']), float(r['low']), float(r['close'])] for r in rates]
        candles[s] = c
        print('candles', s, {k: len(v) for k, v in c.items()}, flush=True)

    mt5.shutdown()
    raw = {'acct': acct, 'server_offset_h': offset, 'fetched_at': int(time.time()), 'days': days,
           'deals': deals, 'orders': orders, 'positions': positions, 'pending': pending,
           'symbols': symbols, 'candles': candles}
    json.dump(raw, open(os.path.join(OUT, 'raw.json'), 'w'))
    status('fetched', True, f'{len(deals)} deals, {len(orders)} orders')


def mt5_record(mt5, minutes, sym):
    """v1.12: MT5 LIVE RECORD - MT4 ke IW_Recorder jaisa hi rec.csv (T = tick, S = orders snapshot)."""
    import math
    mt5.symbol_select(sym, True)
    time.sleep(2)
    si = mt5.symbol_info(sym)
    dg = si.digits if si else 5
    ai = mt5.account_info()
    tk = mt5.symbol_info_tick(sym)
    srv = int(tk.time) if tk else int(time.time())
    path = os.path.join(OUT, 'rec.csv')
    f = open(path, 'w', newline='')
    f.write(f"I,{srv},{int(time.time())},{sym},{ai.login if ai else 0},{minutes}\n")
    f.flush()
    print('MT5 record start', sym, minutes, 'min', flush=True)
    status('mt5-record', True, f'{minutes} min record ({sym})')
    t_end = time.time() + minutes * 60
    lb = la = None
    last = ''
    nt = 0
    lastflush = time.time()
    lastping = time.time()
    fmt = lambda v: f"{v:.{dg}f}"
    while time.time() < t_end:
        ms = int(time.monotonic() * 1000)
        tk = mt5.symbol_info_tick(sym)
        if tk is None:
            time.sleep(1)
            if mt5.terminal_info() is None:
                print('terminal gaya - record band', flush=True)
                break
            continue
        b, a = tk.bid, tk.ask
        if b != lb or a != la:
            f.write(f"T,{ms},{int(tk.time)},{fmt(b)},{fmt(a)}\n")
            lb, la = b, a
            nt += 1
        parts = []
        for p_ in (mt5.positions_get() or []):
            parts.append(f"{p_.ticket}:{p_.type}:{p_.symbol}:{p_.volume:.2f}:{p_.price_open:.5f}:{p_.sl:.5f}:{p_.tp:.5f}:{p_.magic}:{int(p_.time)};")
        for o_ in (mt5.orders_get() or []):
            parts.append(f"{o_.ticket}:{o_.type}:{o_.symbol}:{o_.volume_current:.2f}:{o_.price_open:.5f}:{o_.sl:.5f}:{o_.tp:.5f}:{o_.magic}:{int(o_.time_setup)};")
        snap = ''.join(parts)
        if snap != last:
            f.write(f"S,{ms},{int(tk.time)},{fmt(b)},{fmt(a)},{snap}\n")
            last = snap
            f.flush()
        if time.time() - lastflush > 10:
            f.flush()
            lastflush = time.time()
        if nt == 0 and time.time() - (t_end - minutes * 60) > 120 and not getattr(mt5_record, 'warned', False):
            mt5_record.warned = True
            print('CHETAVNI: 2 min me 0 tick - symbol', sym, 'galat ho sakta hai', flush=True)
            status('mt5-record', True, f'0 tick - symbol {sym} check')
        if time.time() - lastping > 600:
            left = int((t_end - time.time()) / 60)
            print(f'record chalu: {nt} ticks, {left} min baaki', flush=True)
            status('mt5-record', True, f'{nt} ticks, {left} min baaki')
            lastping = time.time()
        time.sleep(0.2)
    f.close()
    print('MT5 record done', nt, 'ticks', os.path.getsize(path), 'bytes', flush=True)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        fail('crash', type(e).__name__ + ': ' + str(e)[:300])
