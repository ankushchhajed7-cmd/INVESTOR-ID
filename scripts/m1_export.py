# Investor Watch v1.13.3 — M1 DATA EXPORT (Backtest Lab ke liye)
# GitHub Actions Windows runner par: investor login -> ek symbol ka M1 history (default 6 mahine)
# -> MT5 "Export Bars" jaisi CSV (tab, <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>)
# -> data/m1/<SYMBOL>_M1.csv.gz + <SYMBOL>_M1.json (meta). Kabhi trade NAHI karta.
# Password sirf ENCRYPTED aata hai (AES-GCM, key = repo secret IW_KEY) — mt5_fetch.py jaisa.
#
# Usage: python scripts/m1_export.py <terminal64.exe path> <out_dir>
#   env: IW_LOGIN, IW_SERVER, IW_ENC, IW_KEY, IW_SYMBOL (XAUUSDm), IW_MONTHS (6)
import glob, gzip, io, json, os, re, sys, time
from datetime import datetime, timedelta, timezone

OUT = sys.argv[2] if len(sys.argv) > 2 else 'm1_tmp'
os.makedirs(OUT, exist_ok=True)


def status(stage, ok=True, msg='', **extra):
    d = {'stage': stage, 'ok': ok, 'msg': msg, 'at': int(time.time())}
    d.update(extra)
    json.dump(d, open(os.path.join(OUT, 'status.json'), 'w', encoding='utf-8'))
    print(('OK ' if ok else 'ERROR ') + stage + (': ' + msg if msg else ''), flush=True)


def fail(stage, msg):
    status(stage, False, msg)
    sys.exit(1)


def decrypt(enc_b64, passphrase):
    import base64
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    raw = base64.b64decode(enc_b64.strip())
    salt, iv, ct = raw[:16], raw[16:28], raw[28:]
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=150000).derive(passphrase.encode())
    return AESGCM(key).decrypt(iv, ct, None).decode()


def raise_maxbars(n=5000000, extra=None):
    """MT5 sirf 'Max bars in chart' jitne bars deta hai (default 100000 ≈ 3 mahine M1).
    Terminal ki config (terminal.ini [Charts] MaxBars) badha do — initialize se pehle."""
    roots = [os.path.join(os.environ.get('APPDATA', ''), 'MetaQuotes', 'Terminal', '*', 'config', 'terminal.ini')]
    term = sys.argv[1]
    roots.append(os.path.join(os.path.dirname(term), 'config', 'terminal.ini'))
    roots += list(extra or [])
    done = 0
    for pat in roots:
        for p in glob.glob(pat):
            try:
                b = open(p, 'rb').read()
                enc = 'utf-16' if b[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
                t = b.decode(enc, errors='ignore')
                if re.search(r'(?im)^MaxBars=', t):
                    t = re.sub(r'(?im)^MaxBars=.*$', 'MaxBars=%d' % n, t)
                elif re.search(r'(?im)^\[Charts\]', t):
                    t = re.sub(r'(?im)^\[Charts\]\s*$', '[Charts]\r\nMaxBars=%d' % n, t, count=1)
                else:
                    t = t.rstrip() + '\r\n[Charts]\r\nMaxBars=%d\r\n' % n
                open(p, 'wb').write(t.encode('utf-16') if enc == 'utf-16' else t.encode('utf-8'))
                done += 1
                print('MaxBars set:', p, flush=True)
            except Exception as e:
                print('MaxBars skip', p, type(e).__name__, flush=True)
    if not done:
        print('MaxBars: terminal.ini nahi mili (default limit lagegi)', flush=True)


def main():
    term = sys.argv[1]
    login = os.environ.get('IW_LOGIN', '').strip()
    server = os.environ.get('IW_SERVER', '').strip()
    enc = os.environ.get('IW_ENC', '').strip()
    key = os.environ.get('IW_KEY', '')
    want = (os.environ.get('IW_SYMBOL', '') or 'XAUUSDm').strip()
    months = max(1, min(24, int(os.environ.get('IW_MONTHS', '6') or 6)))
    if not login.isdigit():
        fail('input', 'Login sirf number hona chahiye')
    if not server:
        fail('input', 'Server naam khaali hai')
    if not re.fullmatch(r'[A-Za-z0-9._#\-]{2,30}', want):
        fail('input', 'Symbol naam galat')
    if not key:
        fail('input', 'Repo secret IW_KEY set nahi hai (Settings > Secrets > Actions)')
    try:
        pw = decrypt(enc, key)
    except Exception:
        fail('password', 'Password decrypt nahi hua — app me Secret key wahi daalo jo repo secret IW_KEY me hai')
    print('::add-mask::' + pw, flush=True)

    raise_maxbars()
    import MetaTrader5 as mt5
    status('login')

    def connect(tries):
        err = None
        for i in range(tries):
            if mt5.initialize(path=term, login=int(login), password=pw, server=server, timeout=150000):
                return True, None
            err = mt5.last_error()
            print('initialize try', i + 1, 'failed:', err, flush=True)
            mt5.shutdown()
            time.sleep(10)
        return False, err

    ok, err = connect(2)
    if not ok:
        if err and err[0] == -10005:
            fail('login', 'MT5 terminal se baat nahi hui (IPC timeout) — aksar broker ka server generic MT5 me nahi milta. '
                          'Scan form > Aur options me broker ka MT5 installer link do (Exness apne aap lagta hai).')
        hint = ' — password galat/badal gaya, ya server naam galat.' if err and err[0] in (-6, -10003, -10004) else ''
        fail('login', 'MT5 login nahi hua ' + str(err) + hint)
    # MaxBars: data folder ab bana hai -> config badlo aur dobara connect (ek hi baar)
    ti = mt5.terminal_info()
    mb = getattr(ti, 'maxbars', None) if ti is not None else None
    print('terminal maxbars:', mb, flush=True)
    if ti is not None and mb is not None and mb < 1000000 and getattr(ti, 'data_path', None):
        mt5.shutdown()
        if os.name == 'nt':                    # terminal band (force) — warna wo apni purani config wapas likh deta
            os.system('taskkill /IM terminal64.exe /F >NUL 2>&1')
        time.sleep(4)
        raise_maxbars(extra=[os.path.join(ti.data_path, 'config', 'terminal.ini')])
        ok, err = connect(2)
        if not ok:
            fail('login', 'MaxBars ke baad dobara login nahi hua ' + str(err))
        ti = mt5.terminal_info()
        print('terminal maxbars (naya):', getattr(ti, 'maxbars', '?') if ti else '?', flush=True)
    pw = None

    # symbol (broker par naam alag ho sakta hai: XAUUSD / XAUUSDm / XAUUSD.e)
    sym = want
    if mt5.symbol_info(sym) is None:
        base = re.sub(r'[^A-Z]', '', want.upper())[:6]
        cands = [x.name for x in (mt5.symbols_get('*' + base[:3] + '*') or []) if x.name.upper().startswith(base)]
        print('symbol khoj:', want, '->', cands[:6], flush=True)
        if not cands:
            fail('symbol', want + ' is account par nahi mila')
        sym = sorted(cands, key=len)[0]
    mt5.symbol_select(sym, True)
    si = mt5.symbol_info(sym)
    time.sleep(3)

    # server time offset (server - UTC), tick se
    offset = None
    tk = mt5.symbol_info_tick(sym)
    if tk and tk.time:
        off = (tk.time - time.time()) / 3600.0
        if -12.5 <= off <= 14.5 and abs(off * 2 - round(off * 2)) < 0.15:
            offset = round(off * 2) / 2

    status('download')
    now = datetime.now(timezone.utc) + timedelta(days=2)       # server time UTC se aage ho sakta hai
    start = now - timedelta(days=months * 31 + 2)
    rows = {}
    chunk = timedelta(days=10)
    f = start
    while f < now:
        t = min(f + chunk, now)
        got = None
        for i in range(4):
            got = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M1, f, t)
            if got is not None and len(got):
                break
            time.sleep(4)
        n = 0 if got is None else len(got)
        if n:
            for r in got:
                rows[int(r['time'])] = (float(r['open']), float(r['high']), float(r['low']), float(r['close']),
                                        int(r['tick_volume']), int(r['real_volume']), int(r['spread']))
        print('chunk', f.strftime('%Y-%m-%d'), '->', t.strftime('%Y-%m-%d'), n, 'bars', flush=True)
        f = t
    mt5.shutdown()
    if not rows:
        fail('download', sym + ' ka M1 data nahi mila (' + str(mt5.last_error()) + ')')

    ts = sorted(rows)
    digits = si.digits if si else 3
    fmt = '%.' + str(digits) + 'f'
    buf = io.StringIO()
    buf.write('<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n')
    for t in ts:
        o, h, l, c, tv, rv, sp = rows[t]
        d = datetime.fromtimestamp(t, timezone.utc)
        buf.write(d.strftime('%Y.%m.%d\t%H:%M:%S') + '\t' + '\t'.join(fmt % x for x in (o, h, l, c)) + '\t%d\t%d\t%d\n' % (tv, rv, sp))
    dest = os.path.join('data', 'm1')
    os.makedirs(dest, exist_ok=True)
    safe = re.sub(r'[^A-Za-z0-9._\-]', '_', sym)
    with gzip.open(os.path.join(dest, safe + '_M1.csv.gz'), 'wb', compresslevel=9) as g:
        g.write(buf.getvalue().encode('utf-8'))
    first, last = ts[0], ts[-1]
    days_got = (last - first) / 86400.0
    meta = {
        'symbol': sym, 'requested': want, 'server': server, 'bars': len(ts),
        'from': datetime.fromtimestamp(first, timezone.utc).strftime('%Y-%m-%d %H:%M'),
        'to': datetime.fromtimestamp(last, timezone.utc).strftime('%Y-%m-%d %H:%M'),
        'days': round(days_got, 1), 'months_requested': months, 'server_offset_h': offset,
        'point': si.point if si else None, 'digits': digits, 'contract': si.trade_contract_size if si else None,
        'file': safe + '_M1.csv.gz', 'fetched_at': int(time.time())
    }
    json.dump(meta, open(os.path.join(dest, safe + '_M1.json'), 'w', encoding='utf-8'), indent=1)
    short = days_got < months * 30 * 0.8
    status('done', True, '%s: %d M1 bars, %s → %s (%.0f din)%s' % (sym, len(ts), meta['from'][:10], meta['to'][:10], days_got,
           ' — broker ne kam history di' if short else ''), symbol=sym, file=meta['file'])


if __name__ == '__main__':
    main()
