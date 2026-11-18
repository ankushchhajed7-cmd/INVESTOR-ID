# Investor Watch v1.09 — MT4 se data nikalna (GitHub Actions Windows runner par)
# MT4 ka Python connection nahi hota, isliye: MT4 portable copy -> IW_Export.mq4 compile ->
# start.ini (investor login + Script=IW_Export) se terminal start -> script MQL4\Files\IW_export.json likhta hai
# -> yahan MT5-jaisa raw.json banta hai -> wahi strategy_scan.py.  Kabhi trade NAHI karta.
#
# Usage: python scripts/mt4_run.py <terminal.exe path> <out_dir>
#   env: IW_LOGIN, IW_SERVER, IW_ENC, IW_KEY, IW_DAYS (0 = sab)
import json, os, shutil, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mt5_fetch import decrypt, status, fail, OUT          # same helpers (status.json, AES decrypt)

HERE = os.path.dirname(os.path.abspath(__file__))


def convert(j, days):
    """MT4 export -> MT5 jaisa raw.json (deals / orders / positions / pending)"""
    deals, orders, positions, pending = [], [], [], []
    nid = [10 ** 12]

    def new_id():
        nid[0] += 1
        return nid[0]
    now = j.get('now_server') or int(time.time())
    cut = now - days * 86400 if days > 0 else 0
    for o in j.get('history', []):
        ty, c = o['ty'], (o.get('c') or '')
        cl = c.lower()
        if (o.get('ct') or o['ot']) < cut:
            continue
        if ty in (6, 7):                                        # balance / credit
            deals.append(dict(ticket=new_id(), order=0, time=o['ot'], time_msc=o['ot'] * 1000, type=2 if ty == 6 else 3, entry=0,
                              magic=0, position_id=0, reason=0, volume=0, price=0, commission=0, swap=0, profit=o['pr'], fee=0,
                              symbol='', comment=c))
        elif ty in (0, 1):                                      # band hua trade = IN + OUT deal
            reason = 4 if '[sl]' in cl else 5 if '[tp]' in cl else 6 if (cl.startswith('so:') or '[so' in cl) else (3 if o['mg'] else 0)
            orders.append(dict(ticket=o['t'], time_setup=o['ot'], time_done=o['ot'], type=ty, state=4, magic=o['mg'], position_id=o['t'],
                               volume_initial=o['v'], volume_current=0, price_open=o['op'], sl=o['sl'], tp=o['tp'], price_current=o['cp'],
                               symbol=o['s'], comment=c))
            deals.append(dict(ticket=new_id(), order=o['t'], time=o['ot'], time_msc=o['ot'] * 1000, type=ty, entry=0, magic=o['mg'],
                              position_id=o['t'], reason=3 if o['mg'] else 0, volume=o['v'], price=o['op'], commission=0, swap=0,
                              profit=0, fee=0, symbol=o['s'], comment=c))
            deals.append(dict(ticket=new_id(), order=o['t'], time=o['ct'], time_msc=o['ct'] * 1000 + 1, type=1 - ty, entry=1, magic=o['mg'],
                              position_id=o['t'], reason=reason, volume=o['v'], price=o['cp'], commission=o.get('cm', 0), swap=o.get('sw', 0),
                              profit=o['pr'], fee=0, symbol=o['s'], comment=c))
        elif 2 <= ty <= 5:                                      # cancel / expire hua pending
            expired = (o.get('ex') and o['ct'] >= o['ex'] - 2) or 'expir' in cl
            orders.append(dict(ticket=o['t'], time_setup=o['ot'], time_done=o['ct'], type=ty, state=6 if expired else 2, magic=o['mg'],
                               position_id=0, volume_initial=o['v'], volume_current=o['v'], price_open=o['op'], sl=o['sl'], tp=o['tp'],
                               price_current=o['cp'], symbol=o['s'], comment=c))
    for o in j.get('trades', []):
        ty, c = o['ty'], (o.get('c') or '')
        if ty in (0, 1):
            positions.append(dict(ticket=o['t'], identifier=o['t'], time=o['ot'], time_msc=o['ot'] * 1000, type=ty, magic=o['mg'], reason=0,
                                  volume=o['v'], price_open=o['op'], sl=o['sl'], tp=o['tp'], price_current=o['cp'], swap=o.get('sw', 0),
                                  profit=o['pr'], symbol=o['s'], comment=c))
        elif 2 <= ty <= 5:
            p = dict(ticket=o['t'], time_setup=o['ot'], time_done=0, type=ty, state=1, magic=o['mg'], position_id=0, volume_initial=o['v'],
                     volume_current=o['v'], price_open=o['op'], sl=o['sl'], tp=o['tp'], price_current=o['cp'], symbol=o['s'], comment=c)
            pending.append(p)
            orders.append(p)
    deals.sort(key=lambda d: d['time_msc'])
    orders.sort(key=lambda o: o['time_setup'])
    a = j['acct']
    off = None
    if j.get('now_server') and j.get('now_gmt'):
        x = (j['now_server'] - j['now_gmt']) / 3600.0
        if -12.5 <= x <= 14.5 and abs(x * 2 - round(x * 2)) < 0.1:
            off = round(x * 2) / 2
    acct = dict(login=a['login'], server=a['server'], company=a['company'], currency=a['currency'], balance=a['balance'],
                equity=a['equity'], margin=a['margin'], profit=a['profit'], leverage=a['leverage'],
                trade_mode=0 if a.get('demo') else 2, trade_allowed=a.get('trade_allowed', False))
    return {'platform': 'MT4', 'acct': acct, 'server_offset_h': off, 'fetched_at': now, 'days': days,
            'deals': deals, 'orders': orders, 'positions': positions, 'pending': pending,
            'symbols': j.get('symbols', {}), 'candles': j.get('candles', {})}


def tail_logs(work):
    for d in (os.path.join(work, 'logs'), os.path.join(work, 'MQL4', 'Logs')):
        if not os.path.isdir(d):
            continue
        for f in sorted(x for x in os.listdir(d) if x.endswith('.log') and 'metaeditor' not in x)[-2:]:
            try:
                raw = open(os.path.join(d, f), 'rb').read()
                txt = raw.decode('utf-16', errors='ignore') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('latin-1')
                print('---', d, f, '---')
                print('\n'.join(l for l in txt.splitlines()[-40:] if 'Compiling' not in l), flush=True)
            except Exception:
                pass


def main():
    term = sys.argv[1]
    login = os.environ.get('IW_LOGIN', '').strip()
    server = os.environ.get('IW_SERVER', '').strip()
    enc = os.environ.get('IW_ENC', '').strip()
    key = os.environ.get('IW_KEY', '')
    days = int(os.environ.get('IW_DAYS', '0') or 0)
    rec_min = int(os.environ.get('IW_RECORD', '0') or 0)
    rec_sym = (os.environ.get('IW_RECSYM', '') or '').strip()
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

    # 1) MT4 ki portable copy (Program Files se bahar, likhne ki dikkat na ho)
    status('mt4-setup')
    work = os.path.join(os.environ.get('RUNNER_TEMP', os.getcwd()), 'mt4w')
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(os.path.dirname(term), work, dirs_exist_ok=True)
    exe = os.path.join(work, os.path.basename(term))
    for d in ('MQL4/Scripts', 'MQL4/Files', 'config'):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    src = open(os.path.join(HERE, 'IW_Export.mq4'), encoding='utf-8').read()
    plain, keep = [], True
    for line in src.splitlines():
        if line.startswith('//@@DLL_START'):
            keep = False
        elif line.startswith('//@@DLL_END'):
            keep = True
        elif keep:
            plain.append(line)
    scripts = {'IW_Export': src, 'IW_ExportP': '\n'.join(plain)}
    me = os.path.join(work, 'metaeditor.exe')
    for name, code in scripts.items():
        p = os.path.join(work, 'MQL4', 'Scripts', name + '.mq4')
        open(p, 'w', encoding='utf-8').write(code)
        if os.path.exists(me):
            try:
                subprocess.run([me, '/portable', '/compile:' + p, '/log:' + p[:-4] + '.log'], timeout=180)
            except Exception as e:
                print('compile', name, e)
            lg = p[:-4] + '.log'
            if os.path.exists(lg):
                raw = open(lg, 'rb').read()
                print(name, 'compile:', (raw.decode('utf-16', errors='ignore') if raw[:2] == b'\xff\xfe' else raw.decode('latin-1'))[-400:], flush=True)
        print(name, 'ex4:', os.path.exists(p[:-4] + '.ex4'), flush=True)

    files = os.path.join(work, 'MQL4', 'Files')
    os.makedirs(os.path.join(work, 'MQL4', 'Experts'), exist_ok=True)

    def ini_write(extra):
        ini = os.path.join(work, 'config', 'iw_start.ini')
        lines = [f'Login={login}', f'Password={pw}', f'Server={server}', 'AutoConfiguration=false', 'EnableNews=false',
                 'ExpertsEnable=true', 'ExpertsDllImport=true', 'ExpertsExpImport=false', 'ExpertsTrades=false',
                 'ExpertsConfirm=false'] + extra
        # newline='' zaroori: warna Windows par \r\r\n banta hai aur har value ke end me \r chipak jata hai
        open(ini, 'w', encoding='ascii', errors='ignore', newline='').write('\r\n'.join(lines) + '\r\n')
        return ini

    # ---- LIVE RECORD mode: EA chart par N minute tick + orders record karta hai ----
    if rec_min > 0:
        status('mt4-record', True, f'{rec_min} min record')
        ep = os.path.join(work, 'MQL4', 'Experts', 'IW_Recorder.mq4')
        shutil.copy(os.path.join(HERE, 'IW_Recorder.mq4'), ep)
        if os.path.exists(me):
            try:
                subprocess.run([me, '/portable', '/compile:' + ep, '/log:' + ep[:-4] + '.log'], timeout=180)
            except Exception as e:
                print('compile recorder', e)
        print('IW_Recorder ex4:', os.path.exists(ep[:-4] + '.ex4'), flush=True)
        open(os.path.join(files, 'IW_rec_cfg.txt'), 'w').write(str(rec_min))
        rd = os.path.join(files, 'IW_rec_done.txt')
        for sym_try in [x for x in (rec_sym, 'GOLD', 'XAUUSD') if x]:
            for f_ in (rd, os.path.join(files, 'IW_rec.csv')):
                if os.path.exists(f_):
                    os.remove(f_)
            ini = ini_write([f'Expert=IW_Recorder', f'Symbol={sym_try}', 'Period=M1'])
            print('record start:', sym_try, rec_min, 'min', flush=True)
            proc = subprocess.Popen([exe, '/portable', os.path.join('config', 'iw_start.ini')], cwd=work)
            t0 = time.time(); gone = False; started = False
            recp = os.path.join(files, 'IW_rec.csv')
            while time.time() - t0 < rec_min * 60 + 300:
                time.sleep(10)
                if not gone and time.time() - t0 > 45:
                    try:
                        os.remove(ini); gone = True
                    except Exception:
                        pass
                if os.path.exists(recp) and os.path.getsize(recp) > 200:
                    started = True
                if not started and time.time() - t0 > 240:
                    print('recorder 4 min me shuru nahi hua', flush=True)
                    break
                if os.path.exists(rd):
                    try:
                        if open(rd, encoding='latin-1').read().startswith('ok'):
                            break
                    except Exception:
                        pass
                if proc.poll() is not None:
                    print('terminal band ho gaya, code', proc.returncode, flush=True)
                    break
            subprocess.run(['taskkill', '/F', '/IM', os.path.basename(exe)], capture_output=True)
            try:
                os.remove(ini)
            except Exception:
                pass
            tail_logs(work)
            if started:
                shutil.copy(recp, os.path.join(OUT, 'rec.csv'))
                print('record saved', os.path.getsize(recp), 'bytes', open(rd).read() if os.path.exists(rd) else '(timeout)', flush=True)
                break
        else:
            print('record nahi hua — sirf normal scan', flush=True)
    done_p = os.path.join(files, 'IW_done.txt')
    exp_p = os.path.join(files, 'IW_export.json')
    msg = None
    attempts = [('IW_Export', 'EURUSD'), ('IW_ExportP', None)]
    for script, sym in attempts:
        status('mt4-login')
        for p in (done_p, exp_p):
            if os.path.exists(p):
                os.remove(p)
        ini = ini_write([f'Script={script}'] + ([f'Symbol={sym}', 'Period=H1'] if sym else []))
        print('start terminal:', script, sym or '(default chart)', flush=True)
        proc = subprocess.Popen([exe, '/portable', os.path.join('config', 'iw_start.ini')], cwd=work)
        t0 = time.time()
        ini_gone = False
        while time.time() - t0 < 420:
            time.sleep(5)
            if not ini_gone and time.time() - t0 > 45:       # password wali file hata do
                try:
                    os.remove(ini)
                    ini_gone = True
                except Exception:
                    pass
            if os.path.exists(done_p):
                time.sleep(2)
                msg = open(done_p, encoding='latin-1').read().strip()
                break
            if proc.poll() is not None:
                print('terminal band ho gaya, code', proc.returncode, flush=True)
                break
        subprocess.run(['taskkill', '/F', '/IM', os.path.basename(exe)], capture_output=True)
        try:
            os.remove(ini)
        except Exception:
            pass
        tail_logs(work)
        if msg:
            print('script:', msg, flush=True)
            break
        print('is try me script nahi chala, agla try…', flush=True)

    if not msg:
        fail('mt4-script', 'MT4 me export script nahi chala (login ya chart ki dikkat) — run log dekho')
    if not msg.startswith('ok'):
        fail('mt4-login', msg)
    status('convert')
    raw_txt = open(exp_p, 'rb').read().decode('cp1252', errors='replace')
    j = json.loads(raw_txt)
    raw = convert(j, days)
    json.dump(raw, open(os.path.join(OUT, 'raw.json'), 'w'))
    print('deals', len(raw['deals']), 'orders', len(raw['orders']), 'open', len(raw['positions']), 'pending', len(raw['pending']), flush=True)
    status('fetched', True, f"MT4: {len(raw['deals'])} deals, {len(raw['orders'])} orders")


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        fail('crash', type(e).__name__ + ': ' + str(e)[:300])
