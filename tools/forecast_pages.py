# 예측 중심 화면(2026-10-28 전면 개편) — 첫 화면(오늘 예보판)·품목별(/f/)·품목 예보(/f/갈래/품목/)·경보(/alerts/)·적중 기록(/track/)
# build_pages.py 가 import 해서 build(globals()) 로 부른다. 자료는 모두 site/data 와 private 의 생성물만 읽는다(여기서 새 숫자를 만들지 않음).
#
# 품목 하나를 「예보 항목」으로 통일한다:
#   sector(축산·수산·농산) · item · dir(오름/내림/보합) · strength(0~5) · score · price(현재 ㎏당) · unit · horizon(무엇을 언제 맞히나)
#   why[](근거 문장) · act(행동 제안) · series[(날짜, 값)](값 흐름) · where(싸게 거래된 곳) · subs(대체 품목) · note(관측 기관 메모) · hist(지난 예보와 결과)
import os, re, json, glob, datetime, collections, urllib.parse
from trend_lib import metrics as tmetrics, stock_svg, metrics_html, regime_badge, regime_text
import brand as BR

DIRW = {'오름 쪽': ('오름', 'up'), '내림 쪽': ('내림', 'dn'), '보합': ('보합', 'flat')}
SECT_H = {'축산': '앞으로 2주 · 경락가', '수산': '다음 달 · 산지 위판가', '농산': '앞으로 2주 · 도매시장가'}
MAXS = {'축산': 1.5, '수산': 2.5, '농산': 1.0}

def build(G):
    E = G['E']; J = G['J']; write = G['write']; shell = G['shell']; svg_line = G['svg_line']; man = G['man']
    BASE = G['BASE']; ROOT = G['ROOT']; PRIVATE = os.path.join(ROOT, 'private')
    FC = J('forecast.json', {}); BUYS = J('buysignal.json', {}); CROPS = J('cropsignal.json', {}); OPPS = J('opps.json', {})
    WPN = J('wipan.json', {}); RISK = J('risk.json', {}); SIG = J('signals.json', {'items': []}); PRICE = J('price/latest.json', {}); WORLD = J('world.json', {'events': []})
    try: IM = json.load(open(os.path.join(ROOT, 'tools', 'import_matrix.json'), encoding='utf-8'))
    except Exception: IM = {'items': []}
    EXPO = WORLD.get('exposure') or {}; OLV = WORLD.get('origin_level') or {}
    PX = J('pindex.json', {}) or {}   # 물가 지수(build_index.py 생성물)
    GL = J('global.json', {}) or {}   # 세계 공개 연동창구(collect_global.py)
    GAP = J('gap.json', {}) or {}   # 갭 기회(build_gap.py)
    SRC = J('source.json', {}) or {}   # 원산지 거래 정보(build_source.py)
    try: GCAND = json.load(open(os.path.join(ROOT, 'tools', 'gap_candidates.json'), encoding='utf-8')).get('items') or []
    except Exception: GCAND = []
    SRC_BY = collections.defaultdict(list)
    for r in SRC.get('items') or []:
        for sg in r.get('signals') or []: SRC_BY[(r['sector'], sg['item'])].append(r)
    GOK = [x for x in (GAP.get('pairs') or []) if x.get('ok')]; GHOT = [x for x in GOK if x['state'] != '평소 범위' and not x.get('stale') and x.get('kind') != 'fx']   # 환율만 맞댄 참고 짝은 「켜진 갭」에서 제외
    try: GAPI = json.load(open(os.path.join(ROOT, 'tools', 'global_apis.json'), encoding='utf-8'))
    except Exception: GAPI = {'sources': []}
    AK = {'한우 거세': '한우', '돼지 탕박': '돼지', '배합사료 원가': '사료'}   # 축산 품목 이름 → 규칙에서 쓰는 짧은 이름
    def akey(sector, item): return AK.get(item, item) if sector == '축산' else item
    def exposure_of(sector, item):
        item = akey(sector, item); out = []
        for k, v in EXPO.items():
            sec, pat = k.split('|', 1)
            if sec != sector: continue
            try: ok = pat == '.' or re.fullmatch('(?:' + pat + ')', item)
            except re.error: ok = False
            if ok: out += v
        return out
    TODAY = (FC.get('at') or BUYS.get('at') or datetime.date.today().isoformat())[:10]
    def _d(s): return datetime.date.fromisoformat(s[:10])

    def base(n):
        n = re.sub(r'\(.*?\)', '', n or '').strip(); n = re.sub(r'^기타', '', n); n = re.sub(r'류$', '', n)
        return {'우렁쉥이': '멍게', '살오징어': '오징어', '피뿔고둥': '소라', '참굴': '굴', '민대구': '대구', '코다리': '명태', '명태포': '명태', '오징어포': '오징어'}.get(n, n).strip()
    def slug(sector, item): return f'/f/{sector}/{re.sub(r"[/\\s]+", "·", item).strip("·")}/'
    def dirw(d): return DIRW.get(d, ('보합', 'flat'))
    def badge(d, big=False):
        w, c = dirw(d); return f'<span class="fx {c}{" big" if big else ""}">{E(w)}</span>'
    def dots(n): return '<span class="dots" aria-label="신호 세기 ' + str(n) + '/5">' + ''.join('<i class="on"></i>' if i < n else '<i></i>' for i in range(5)) + '</span>'
    def strength(sector, score):
        m = MAXS.get(sector, 1.0); return 0 if not score else max(1, min(5, round(abs(score) / m * 5)))
    def won(v): return f'{v:,.0f}원' if isinstance(v, (int, float)) and v else '–'
    def spark(vals, w=120, h=34, cls='up'):
        vs = [v for v in vals if isinstance(v, (int, float))]
        if len(vs) < 2: return ''
        lo, hi = min(vs), max(vs); rng = (hi - lo) or 1
        pts = ' '.join(f'{(w - 4) * i / (len(vs) - 1) + 2:.1f},{h - 3 - (h - 6) * (v - lo) / rng:.1f}' for i, v in enumerate(vs))
        return f'<svg class="spark {cls}" viewBox="0 0 {w} {h}" aria-hidden="true"><polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>'
    def chart(pts, color='var(--moss)', w=640, h=170, pad=28):
        if len(pts) < 2: return ''
        vs = [p[1] for p in pts]; lo, hi = min(vs), max(vs); rng = (hi - lo) or 1
        X = lambda i: pad + (w - 2 * pad) * i / (len(pts) - 1); Y = lambda v: h - pad - (h - 2 * pad) * (v - lo) / rng
        d = 'M' + ' L'.join(f'{X(i):.1f},{Y(v):.1f}' for i, v in enumerate(vs))
        ticks = sorted(set([0, len(pts) // 3, 2 * len(pts) // 3, len(pts) - 1]))
        long = (pts[-1][0][:7] != pts[0][0][:7]) and len(pts) > 60
        lab = ''.join(f'<text x="{X(i):.0f}" y="{h - 7}" font-size="11" text-anchor="{"start" if i == 0 else "end" if i == len(pts) - 1 else "middle"}" fill="var(--faint)">{(pts[i][0][2:7].replace("-", ".") if long else pts[i][0][5:10].replace("-", "."))}</text>' for i in ticks)
        yl = f'<text x="{w - 4}" y="{Y(hi) + 4:.0f}" font-size="11" text-anchor="end" fill="var(--faint)">{hi:,.0f}</text><text x="{w - 4}" y="{Y(lo) + 4:.0f}" font-size="11" text-anchor="end" fill="var(--faint)">{lo:,.0f}</text>'
        area = d + f' L{X(len(vs) - 1):.1f},{h - pad} L{X(0):.1f},{h - pad} Z'
        return f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="값 흐름 그래프"><path d="{area}" fill="{color}" opacity=".07"/><path d="{d}" fill="none" stroke="{color}" stroke-width="2"/><circle cx="{X(len(vs) - 1):.1f}" cy="{Y(vs[-1]):.1f}" r="3.5" fill="{color}"/>{lab}{yl}</svg>'
    def rate_of(sector):
        t = (FC.get('micro_track') or {}).get(sector) or {}
        return (t.get('n') or 0, t.get('hit') or 0, t.get('rate'))
    def conf_text(sector):
        n, h, r = rate_of(sector)
        return f'지난 적중 {r}% ({h}/{n}건)' if n else '첫 채점 대기'

    # ── 예보 항목 만들기 ─────────────────────────────────────────
    items = []
    notes_by = collections.defaultdict(list)
    for s in FC.get('sectors') or []:
        for n in s.get('notes') or []: notes_by[(s['sector'], n['item'])].append(n)
    risk_sp = {base(x['sp']): x for x in RISK.get('species', [])}
    # 수산
    fish_daily = {f['name']: f for f in WPN.get('fish', [])}
    sp_by = collections.defaultdict(list)
    for x in OPPS.get('spread', []): sp_by[base(x['fish'])].append(x)
    tight = {x['item']: x for x in OPPS.get('tight', [])}; glut = {x['item']: x for x in OPPS.get('glut', [])}
    hist_sea = collections.defaultdict(list)
    for m in (BUYS.get('score') or {}).get('months', []):
        for r in m.get('rows', []): hist_sea[r[0]].append((m['month'] + ' → ' + m['to'], r[1], r[2], r[3]))
    mo = WPN.get('month') or ''
    for i in BUYS.get('items') or []:
        f = fish_daily.get((i.get('names') or [''])[0]) or {}
        series = [(f'{mo[:4]}-{d}', v) for d, v in f.get('daily', []) if v] if mo else []
        kgm = {d: q for d, q in f.get('daily_kg', [])}; vols = [(f'{mo[:4]}-{d}', kgm.get(d) or 0) for d, v in f.get('daily', []) if v] if mo else []
        rk = risk_sp.get(i['item'])
        items.append({'sector': '수산', 'item': i['item'], 'names': i.get('names') or [], 'dir': i['dir'], 'score': i['score'], 'price': i['wonkg'], 'unit': '원/㎏',
                      'horizon': BUYS.get('horizon', '다음 달 수협 산지 위판 ㎏당 값'), 'why': i.get('why') or [], 'act': i.get('act', ''), 'series': series, 'vols': vols if any(q for _, q in vols) else None,
                      'where': [[c[0], c[1], c[3]] for x in sp_by.get(i['item'], [])[:1] for c in x['cheap']], 'where_src': '수협 산지 위판(조합별 ㎏당 값, ' + mo.replace('-', '년 ') + '월)' if mo else '',
                      'subs': (tight.get(i['item']) or {}).get('sub') or [], 'risk': rk, 'hist': hist_sea.get(i['item'], []), 'notes': notes_by.get(('수산', i['item']), []),
                      'opp': '공급 빠듯' if i['item'] in tight else '공급 넘침' if i['item'] in glut else '', 'amt': i.get('amt')})
    # 농산
    wd = {}
    for p in sorted(glob.glob(os.path.join(PRIVATE, 'wholesale', '*.json')))[-45:]:
        try: wd[os.path.basename(p)[:10]] = json.load(open(p, encoding='utf-8'))
        except Exception: pass
    csp = {x['item']: x for x in CROPS.get('spread', [])}
    hist_crop = collections.defaultdict(list)
    for r in (CROPS.get('score') or {}).get('rows', []): hist_crop[r[1]].append((r[0], r[2], r[3], r[4]))
    for i in CROPS.get('items') or []:
        series = [(d, v[i['item']][0]) for d, v in sorted(wd.items()) if v.get(i['item']) and v[i['item']][0]]
        vols = [(d, v[i['item']][1]) for d, v in sorted(wd.items()) if v.get(i['item']) and v[i['item']][0]]
        x = csp.get(i['item'])
        items.append({'sector': '농산', 'item': i['item'], 'names': [], 'dir': i['dir'], 'score': i['score'], 'price': i['wonkg'], 'unit': '원/㎏',
                      'horizon': CROPS.get('horizon', '앞으로 2주 공영도매시장 ㎏당 값'), 'why': i.get('why') or [], 'act': i.get('act', ''), 'series': series, 'vols': vols if any(q for _, q in vols) else None,
                      'where': [[c[0], c[1], c[2]] for c in (x['cheap'] if x else [])], 'where_src': f'공영도매시장 정산({CROPS.get("date", "")} 거래, ㎏ 단위 거래만)',
                      'subs': [], 'risk': None, 'hist': hist_crop.get(i['item'], []), 'notes': notes_by.get(('농산', i['item']), []), 'opp': '', 'amt': None})
    # 축산 — 판단(한우·돼지·사료) + 관측 기관 메모
    hist_dir = os.path.join(ROOT, 'site', 'data', 'price', 'history')
    hfiles = sorted(glob.glob(os.path.join(hist_dir, '*.json')))
    def ek_series(title, grades=('등외제외', '평균')):
        out = []
        for p in hfiles:
            try: h = json.load(open(p, encoding='utf-8'))
            except Exception: continue
            for s in h.get('ekape', []):
                if s.get('title') != title: continue
                for g in grades:
                    r = next((r for r in s['rows'] if r['g'] == g), None)
                    if r and r.get('p'): out.append((h.get('date') or os.path.basename(p)[:10], r['p'])); break
        return out
    dec = {d['id']: d for d in FC.get('decisions') or []}
    f2 = []
    for p in sorted(glob.glob(os.path.join(PRIVATE, 'forecast2', '2*.json')))[-21:]:
        try: f2.append((os.path.basename(p)[:10], json.load(open(p, encoding='utf-8'))))
        except Exception: pass
    def dec_dir(act):
        return '내림 쪽' if ('내림' in act or '서두르기' in act or '매도' in act) else '오름 쪽' if ('오름' in act or '선매' in act or '늦추기' in act or '앞당' in act) else '보합'
    def dec_hist(did):
        return [(d, next((x['act'] for x in v.get('items', []) if x['id'] == did), ''), next((x.get('base') for x in v.get('items', []) if x['id'] == did), None)) for d, v in f2]
    for did, nm, title, note_key in (('hanwoo', '한우 거세', '한우 거세', '한우'), ('pig', '돼지 탕박', '돼지 탕박', '돼지')):
        d = dec.get(did)
        if not d: continue
        items.append({'sector': '축산', 'item': nm, 'names': [], 'dir': dec_dir(d['act']), 'score': d.get('score') or 0, 'price': d.get('last'), 'unit': '원/㎏',
                      'horizon': d.get('horizon', '앞으로 2주') + ' · 축산물품질평가원 경락가', 'why': d.get('why') or [], 'act': d['act'], 'series': ek_series(title)[-60:],
                      'where': [], 'where_src': '', 'subs': [], 'risk': None, 'hist': [], 'dec_hist': dec_hist(did), 'notes': notes_by.get(('축산', note_key), []), 'opp': '', 'amt': None,
                      'who': d.get('who', ''), 'conf': d.get('conf', ''), 'live': d.get('live_track'), 'ndays': d.get('ndays')})
    d = dec.get('feed'); fd = FC.get('feed') or {}
    if d:
        items.append({'sector': '축산', 'item': '배합사료 원가', 'names': [], 'dir': dec_dir(d['act']), 'score': d.get('score') or 0, 'price': (fd.get('stats') or {}).get('last'), 'unit': '원/㎏(원가 지수)',
                      'horizon': d.get('horizon', '앞으로 1~4개월'), 'why': d.get('why') or [], 'act': d['act'], 'series': [tuple(x) for x in (fd.get('d') or [])[-130:]],
                      'where': [], 'where_src': '', 'subs': [], 'risk': None, 'hist': [], 'dec_hist': dec_hist('feed'), 'notes': notes_by.get(('축산', '배합사료'), []) + notes_by.get(('축산', '사료'), []), 'opp': '', 'amt': None,
                      'who': d.get('who', ''), 'conf': d.get('conf', ''), 'live': None, 'ndays': None, 'feed_note': ((d.get('expect') or {}).get('note') or ''), 'backtest': fd.get('backtest')})
    used = {(it['sector'], n['item']) for it in items for n in it['notes']}
    for (sec, nm), ns in notes_by.items():
        if (sec, nm) in used or any(it['sector'] == sec and it['item'] == nm for it in items): continue
        items.append({'sector': sec, 'item': nm, 'names': [], 'dir': ns[0]['dir'], 'score': 0, 'price': None, 'unit': '', 'horizon': '관측 기관 전망(' + (ns[0].get('until') or '') + '까지 유효)',
                      'why': [n['text'] for n in ns], 'act': '', 'series': [], 'where': [], 'where_src': '', 'subs': [], 'risk': None, 'hist': [], 'notes': ns, 'opp': '', 'amt': None, 'obs_only': True})
    for it in items:
        it['strength'] = strength(it['sector'], it['score']) if not it.get('obs_only') else 3
        it['url'] = slug(it['sector'], it['item']); it['w'], it['cls'] = dirw(it['dir'])
    by_url = {it['url']: it for it in items}
    SEC_ORDER = {'축산': 0, '수산': 1, '농산': 2}
    # ── 경향 계량(품목) + 날마다 기록 + 14일 뒤 채점 ─────────────
    for it in items:
        it['tm'] = tmetrics(it['series']) if len(it['series']) >= 5 else None
    TR_DIR = os.path.join(PRIVATE, 'trend'); os.makedirs(TR_DIR, exist_ok=True)
    idx_list = [('종합', PX.get('total') or {})] + [(k, v) for k, v in (PX.get('sectors') or {}).items()] + [('원가 압력', PX.get('cost') or {})]
    snap = {'date': TODAY, 'items': [[it['sector'], it['item'], it['tm']['last'], it['tm']['regime'], it['tm'].get('slope'), it['tm'].get('date')] for it in items if it.get('tm') and it['tm'].get('n', 0) >= 3],
            'index': {k: [v['metrics']['last'], v['metrics']['regime'], v['metrics'].get('slope'), v['metrics'].get('date')] for k, v in idx_list if v.get('metrics') and v['metrics'].get('n')}}
    try: json.dump(snap, open(os.path.join(TR_DIR, TODAY + '.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    except Exception: pass
    HOR = 14   # 달력일(≈10거래일)
    def price_at(series, d0):
        for d, v in series:
            if d >= d0: return d, v
        return None, None
    ser_by = {(it['sector'], it['item']): it['series'] for it in items}
    idx_ser = {k: (v.get('daily') or []) for k, v in idx_list}
    TSC = {'items': [], 'index': []}
    for p in sorted(glob.glob(os.path.join(TR_DIR, '2*.json'))):
        d0 = os.path.basename(p)[:10]
        if (_d(TODAY) - _d(d0)).days < HOR: continue
        try: sp = json.load(open(p, encoding='utf-8'))
        except Exception: continue
        due = (_d(d0) + datetime.timedelta(days=HOR)).isoformat()
        for row in sp.get('items', []):
            sec, item, last, regime = row[0], row[1], row[2], row[3]
            if regime not in ('상승 추세', '하락 추세', '횡보') or not last: continue
            dd, v = price_at(ser_by.get((sec, item)) or [], due)
            if v is None: continue
            chg = round((v / last - 1) * 100, 1)
            hit = (chg >= 2) if regime == '상승 추세' else (chg <= -2) if regime == '하락 추세' else abs(chg) < 3
            TSC['items'].append({'d': d0, 'sector': sec, 'item': item, 'regime': regime, 'chg': chg, 'hit': hit, 'to': dd})
        for k, row in (sp.get('index') or {}).items():
            last, regime = row[0], row[1]
            if regime not in ('상승 추세', '하락 추세', '횡보') or not last: continue
            dd, v = price_at(idx_ser.get(k) or [], due)
            if v is None: continue
            chg = round((v / last - 1) * 100, 1)
            hit = (chg >= 1) if regime == '상승 추세' else (chg <= -1) if regime == '하락 추세' else abs(chg) < 1.5
            TSC['index'].append({'d': d0, 'item': k, 'regime': regime, 'chg': chg, 'hit': hit, 'to': dd})
    def tsc_sum(rows):
        out = {}
        for r in rows: a = out.setdefault(r['regime'], [0, 0]); a[0] += 1; a[1] += int(r['hit'])
        n = len(rows); h = sum(int(r['hit']) for r in rows)
        base = round(sum(1 for r in rows if r['chg'] >= 2) / n * 100) if n else None   # 「무조건 오른다」고 했을 때 맞을 비율
        return {'n': n, 'hit': h, 'rate': round(h / n * 100) if n else None, 'by': {k: {'n': v[0], 'hit': v[1], 'rate': round(v[1] / v[0] * 100)} for k, v in out.items()}, 'base_up': base}
    TSC['sum_items'] = tsc_sum(TSC['items']); TSC['sum_index'] = tsc_sum(TSC['index']); TSC['n_days'] = len(glob.glob(os.path.join(TR_DIR, '2*.json')))
    try: json.dump(TSC, open(os.path.join(TR_DIR, 'score.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    except Exception: pass
    # 경향 순위(최근 7일 안에 값이 있는 품목만 — 지난달 자료뿐인 갈래는 제외)
    def fresh(it):
        """순위에 올릴 품목: 점 10개 이상, 7일 안 값, 변동성 20%/일 아래(들쭉날쭉한 규격 혼합 제외), 최근 5일 물량 중앙값 1톤 이상(철 끝물 제외)"""
        m = it.get('tm')
        if not (m and m.get('n', 0) >= 10 and m.get('slope') is not None and (_d(TODAY) - _d(m['date'])).days <= 7): return False
        if (m.get('vol') or 0) > 20: return False
        vq = [q for _, q in (it.get('vols') or [])[-5:] if q]
        if vq and sorted(vq)[len(vq) // 2] < 1000: return False
        return True
    TR_UP = sorted([it for it in items if fresh(it) and it['tm']['regime'] == '상승 추세'], key=lambda it: -it['tm']['slope'])
    TR_DN = sorted([it for it in items if fresh(it) and it['tm']['regime'] == '하락 추세'], key=lambda it: it['tm']['slope'])
    TR_X = sorted([it for it in items if fresh(it) and it['tm'].get('cross') and it['tm']['cross']['ago'] <= 3], key=lambda it: it['tm']['cross']['ago'])
    def ago_word(n): return '오늘' if n == 0 else '어제' if n == 1 else f'{n}일 전'
    def tr_row(it):
        m = it['tm']; c = m.get('cross')
        return (f'<tr><td><a href="{it["url"]}"><b>{E(it["item"])}</b></a> <small>{E(it["sector"])}</small></td><td class="num">{E(won(m["last"]))}</td><td>{regime_badge(m)}</td><td class="num">{(m["slope"] or 0):+.2f}</td>'
                f'<td class="num">{(m["chg_s"] if m.get("chg_s") is not None else 0):+}% · {(m["chg_l"] if m.get("chg_l") is not None else 0):+}%</td><td class="num">{m.get("vol") if m.get("vol") is not None else "–"}</td><td>{badge(it["dir"])}</td><td class="mini">{(ago_word(c["ago"]) + " " + c["kind"]) if c else ""}</td><td>{spark([v for _, v in it["series"][-30:]], w=90, h=26, cls="up" if m["regime"] == "상승 추세" else "dn" if m["regime"] == "하락 추세" else "flat")}</td></tr>')
    def tr_table(rows):
        return '<div class="tscroll"><table class="t"><tr><th>품목</th><th class="num">지금</th><th>추세</th><th class="num">20일선 기울기(%/일)</th><th class="num">5일 · 20일</th><th class="num">변동성</th><th>예보</th><th>교차</th><th>30일</th></tr>' + ''.join(tr_row(it) for it in rows) + '</table></div>' if rows else '<p class="mini">해당 품목 없음.</p>'
    def tsc_html(sm, what):
        th = '상승 추세 → +2% 넘게 오르면 적중, 하락 추세 → −2% 넘게 내리면 적중, 횡보 → ±3% 안이면 적중' if what == '품목' else '지수는 움직임이 작아 상승 +1%·하락 −1%·횡보 ±1.5%'
        if not sm.get('n'): return f'<p class="mini">{what} 경향 판정은 날마다 기록해 두고 14일 뒤 실제 값으로 채점합니다({th}, 전환 중은 채점 안 함). 기록 {TSC["n_days"]}일째, 첫 채점은 11월 11일쯤.</p>'
        by = ' · '.join(f'{k} {v["hit"]}/{v["n"]}({v["rate"]}%)' for k, v in sm['by'].items())
        return f'<p><b>{what} 경향 판정 채점</b>: {sm["n"]}건 중 {sm["hit"]}건 적중({sm["rate"]}%) — {by}. 기준선(무조건 「오른다」 했을 때) {sm["base_up"]}%. 틀린 판정도 지우지 않습니다.</p>'
    def rank(it): return (0 if it['dir'] != '보합' else 1, -it['strength'], -(it.get('amt') or 0), it['item'])
    items.sort(key=rank)
    counts = collections.Counter(it['w'] for it in items)

    # ── 공통 조각 ────────────────────────────────────────────────
    def row(it, show_sector=False):
        why = (it['why'] or [''])[0]
        return (f'<a class="frow {it["cls"]}" href="{it["url"]}"><span class="fi">{E(it["item"])}' + (f' <small>{E(it["sector"])}</small>' if show_sector else '') + '</span>'
                f'{badge(it["dir"])}{dots(it["strength"])}<span class="fp">{E(won(it["price"]))}</span><span class="fw mini">{E(why[:46])}</span></a>')
    def feature_card(it):
        return (f'<a class="fcard {it["cls"]}" href="{it["url"]}"><div class="fc-top"><span class="sec">{E(it["sector"])}</span><span class="mini">{E(SECT_H.get(it["sector"], ""))}</span></div>'
                f'<div class="fc-name">{E(it["item"])}</div><div class="fc-line">{badge(it["dir"], True)}{dots(it["strength"])}</div>'
                f'<div class="fc-price">{E(won(it["price"]))}<small> {E(it["unit"] or "")}</small>{spark([v for _, v in it["series"][-30:]], cls=it["cls"])}</div>'
                f'<div class="mini">{E((it["why"] or [""])[0][:60])}</div><div class="fc-act">{E(it["act"] or "")}</div></a>')
    def alerts_all():
        out = []
        for a in FC.get('alerts') or []: out.append({'level': a['level'], 'kind': a.get('kind', ''), 'title': a['title'], 'react': a.get('react', ''), 'date': a.get('date', ''), 'src': a.get('src', ''), 'url': '/signal/#macro'})
        for s in SIG.get('items') or []: out.append({'level': '경보' if s.get('level') in ('경보', '위험') else '주의', 'kind': s.get('kind', ''), 'title': s.get('title', ''), 'react': s.get('body', ''), 'date': s.get('date', ''), 'src': s.get('src', ''), 'url': '/price/'})
        for x in RISK.get('species', []):
            if x.get('lv') in ('위험', '주의'):
                u = slug('수산', x['sp']) if slug('수산', x['sp']) in by_url else '/risk/'
                out.append({'level': '경보' if x['lv'] == '위험' else '주의', 'kind': '폐사 위험', 'title': f'{x["sp"]} 고수온 {x["lv"]} — 양식 면허 {x.get("ha") or 0}㏊ ({", ".join(u2.split("|")[-1] for u2 in x.get("units", [])[:3])})', 'react': '공급이 줄 수 있음 — 미리 확보 또는 대체 품목 검토', 'date': RISK.get('at', '')[:10], 'src': '7일 바다 수온 예보 × 품종별 한계 수온', 'url': u})
        for k, v in (RISK.get('livestock') or {}).items():
            for lv in ('위험', '경고', '주의'):
                if v.get(lv): out.append({'level': '경보' if lv == '위험' else '주의', 'kind': '가축 더위', 'title': f'{k} 더위 {lv} 시군 {v[lv]}곳', 'react': '급수·환기 점검, 출하 일정 조정', 'date': RISK.get('at', '')[:10], 'src': '7일 기온·습도 예보(온습도지수)', 'url': '/risk/'})
        # 물가 지수: 지수선 교차(이틀 안)·±2σ 띠 이탈은 「주의」로 알림(품목 단위는 넣지 않음 — 잡음)
        for k, v in [('종합', PX.get('total') or {})] + [(k, (PX.get('sectors') or {}).get(k) or {}) for k in ('축산', '수산', '농산')] + [('원가 압력', PX.get('cost') or {})]:
            m = v.get('metrics') or {}
            if not m.get('n') or m.get('n', 0) < 10: continue
            c = m.get('cross')
            if c and c.get('ago', 9) <= 1 and (_d(TODAY) - _d(m['date'])).days <= 3:
                out.append({'level': '주의', 'kind': '물가 지수', 'title': f'{k} 지수 {"오늘" if c["ago"] == 0 else "어제"} {c["kind"]} 크로스 — 5일선이 20일선을 {"위로" if c["kind"] == "골든" else "아래로"} 뚫음({m["last"]:,.1f}, {m["regime"]})', 'react': '추세 전환의 초기 신호 — 품목별 경향 순위와 같이 볼 것', 'date': m['date'], 'src': '박씨팜 물가 지수(5일선·20일선)', 'url': '/index/#' + k})
            elif m.get('band_hi') and (m['last'] > m['band_hi'] or m['last'] < m['band_lo']) and (_d(TODAY) - _d(m['date'])).days <= 3:
                out.append({'level': '주의', 'kind': '물가 지수', 'title': f'{k} 지수 {m["last"]:,.1f} — 20일 ±2σ 띠 {"위로" if m["last"] > m["band_hi"] else "아래로"} 벗어남({m["band_lo"]:,.1f}~{m["band_hi"]:,.1f})', 'react': '평소 흐름을 벗어난 값 — 되돌림이 잦으니 하루 값에 끌려가지 말 것', 'date': m['date'], 'src': '박씨팜 물가 지수(20일 표준편차)', 'url': '/index/#' + k})
        out.sort(key=lambda a: (0 if a['level'] == '경보' else 1, a.get('date', ''))); return out
    AL = alerts_all()
    def alert_li(a):
        return f'<li><span class="lv {"hi" if a["level"] == "경보" else "mid"}">{E(a["level"])}</span><b>{E(a["kind"])}</b> <a href="{a["url"]}">{E(a["title"])}</a><div class="mini">{E(a["react"])}</div></li>'

    # ── 세계 요인 조각 ───────────────────────────────────────────
    WEV = WORLD.get('events') or []; WACT = sorted([e for e in WEV if e.get('level')], key=lambda e: (-e['level'], e['cat']))
    LVW = {2: ('경보', 'hi'), 1: ('주의', 'mid'), 0: ('조용', 'quiet')}
    def wlv(l): w, c = LVW.get(l, LVW[0]); return f'<span class="lv {c}">{w}</span>'
    def aff_links(affs):
        out = []
        for a in affs[:4]:
            names = [it['item'] for it in items if it['sector'] == a.get('sector') and (a.get('item') == '.' or re.fullmatch('(?:' + (a.get('item') or '.') + ')', akey(it['sector'], it['item'])))]
            arrow = '↑' if a.get('dir') == '오름 쪽' else '↓' if a.get('dir') == '내림 쪽' else ''
            if names: out.append(f'{E(a["sector"])} ' + ', '.join(f'<a href="{slug(a["sector"], n)}">{E(n)}</a>' for n in names[:6]) + (f' 외 {len(names) - 6}' if len(names) > 6 else '') + f' {arrow}')
            else: out.append(f'{E(a["sector"])} <span class="mini">{E((a.get("item") or "").replace("|", "·")[:40])}</span> {arrow} <span class="mini">(지금 수집 품목에 없음)</span>')
        return ' · '.join(out)
    def world_card(e):
        extra = ''
        if e.get('kind') == 'origin':
            extra = '<div class="mini">수입: ' + ', '.join(f'{E(n)} {int(s * 100)}%' for n, s in (e.get('imports') or [])[:6]) + (f' · 항로 {E(e["route"])}' if e.get('route') else '') + '</div>'
            if e.get('standing'): extra += f'<details class="mini"><summary>상시 배경 위험</summary>{E(e["standing"])}</details>'
        return (f'<li class="wli"><div class="wh">{wlv(e["level"])}<b>{E(e["name"])}</b> <span class="mini">{E(e["cat"])}</span>' + (' <span class="mini">(어제 값)</span>' if e.get('stale') else '') + '</div>' + extra +
                f'<div class="mini">{E(e.get("text", ""))}</div>' + (f'<div class="mini"><b>영향</b> {aff_links(e.get("affects") or [])}</div>' if e.get('affects') else '') +
                (f'<div class="mini"><b>미리 할 일</b> {E(e.get("react", ""))}</div>' if e.get('react') else '') +
                (('<ul class="titles">' + ''.join(f'<li><a href="{E(t["u"])}" target="_blank" rel="noopener nofollow">{E(t["t"])}</a> <span class="mini">{E(t["s"])} {E(t["d"][4:6])}.{E(t["d"][6:8])}</span></li>' for t in e.get('titles') or []) + '</ul>') if e.get('titles') else '') + '</li>')
    def px_sector(k):
        v = (PX.get('sectors') or {}).get(k) or {}
        return v
    def px_strip():
        """첫 화면: 물가 지수 띠(종합·축산·수산·농산) — 마지막 값, 추세, 20일 변화, 작은 그래프"""
        if not PX or not PX.get('sectors'): return ''
        cards = []
        for k, v in [('종합', PX.get('total') or {})] + [(k, px_sector(k)) for k in ('축산', '수산', '농산')]:
            m = v.get('metrics') or {}; ser = v.get('daily') or []
            if not ser: continue
            cls = 'up' if m.get('regime') == '상승 추세' else 'dn' if m.get('regime') == '하락 추세' else 'flat'
            ch = m.get('chg_l') if m.get('chg_l') is not None else m.get('chg_s')
            cards.append(f'<a class="card px {cls}" href="/index/#{E(k)}"><h3>{E(k)} 지수 {regime_badge(m)}</h3><div class="big">{(m.get("last") or ser[-1][1]):.1f}</div>'
                         f'<p class="mini">{("20일 " if m.get("chg_l") is not None else "5일 ") + f"{ch:+}%" if ch is not None else "변화 계산 전"} · {len(ser)}일 · 시작 = 100</p>{spark([x[1] for x in ser[-40:]], cls=cls)}</a>')
        if not cards: return ''
        rk = ''
        if TR_UP or TR_DN:
            f = lambda it: f'<a href="{it["url"]}">{E(it["item"])}</a> <span class="mini">{it["tm"]["slope"]:+.2f}%/일</span>'
            rk = '<p class="mini" style="margin-top:8px;">오르는 추세 가파른 순: ' + (' · '.join(f(it) for it in TR_UP[:4]) or '없음') + ' / 내리는 추세: ' + (' · '.join(f(it) for it in TR_DN[:4]) or '없음') + f' — <a href="/index/#rank">경향 순위 전체 →</a></p>'
        return '<h2 id="px">물가 지수 — 천천히 오르나, 내리나</h2><p class="mini">흩어진 경락가·위판가·도매가를 거래금액 가중으로 한 줄의 지수로 묶고, 주식 차트처럼 5일선·20일선·기울기로 경향을 잽니다. 하루 값이 아니라 흐름을 봅니다.</p><div class="grid4">' + ''.join(cards) + '</div><p class="mini"><a href="/index/">지수 차트·계량 요약·원가 압력 지수 전체 →</a></p>' + rk
    def index_page():
        if not PX or not PX.get('sectors'):
            write('/index/', shell('/index/', '물가 지수 — 준비 중 | 박씨팜', '박씨팜 물가 지수는 자료가 쌓이는 대로 열립니다.', '<p class="crumb"><a href="/">박씨팜</a> › 물가 지수</p><h1 class="title">물가 지수</h1><p class="note">지수를 만들 자료가 아직 쌓이지 않았습니다. 매일 아침 자동으로 다시 계산합니다.</p>', og='/og/index.png'), '0.5'); return
        T = PX.get('total') or {}; C = PX.get('cost') or {}; WS = PX.get('world') or {}
        def block(k, v, monthly=False, color='var(--moss)', unit='', note=''):
            ser = v.get('monthly' if monthly else 'daily') or []
            m = v.get('metrics_m' if monthly else 'metrics') or {}
            if len(ser) < 2: return f'<p class="mini">{E(k)}: 아직 2점이 안 되어 그릴 수 없습니다.</p>'
            vols = v.get('monthly_vol' if monthly else 'vol') or None
            b = f'<div class="pxhead"><div class="big">{(m.get("last") or ser[-1][1]):,.2f}</div><div>{regime_badge(m)}<p class="mini">{E(ser[0][0])} ~ {E(ser[-1][0])} · {len(ser)}{"개월" if monthly else "일"}' + (f' · 구성 {v["items"]}품목' if v.get('items') else '') + '</p></div></div>'
            b += stock_svg(ser, vols=vols, color=color, monthly=monthly, label=k)
            b += f'<p class="mini">{E(v.get("src", ""))}' + (f'. 아래 막대는 {"거래 금액(억 원)" if vols and k != "축산" else "두수" if vols else ""}' if vols else '') + '</p>'
            if m and m.get('n', 0) >= 3: b += metrics_html(m, unit=unit or '') + f'<p class="note"><b>경향 읽기</b> — {E(regime_text(m))}.</p>'
            else: b += '<p class="mini">점이 3개 넘게 쌓이면 추세·변동성·교차가 계산됩니다.</p>'
            if note: b += f'<p class="mini">{note}</p>'
            return b
        b = '<p class="crumb"><a href="/">박씨팜</a> › 물가 지수</p><h1 class="title">박씨팜 물가 지수 — 경향 분석</h1>'
        b += '<p class="lead">한우·돼지 경락가, 수협 위판가, 공영도매시장 정산가를 거래금액 가중으로 묶어 갈래 지수와 종합 지수를 날마다 다시 계산합니다. 농축수산물 값은 하루아침에 뒤집히기보다 천천히 오르고 천천히 내리므로, 주식 차트처럼 <b>5일선·20일선·기울기·±2σ 띠·교차</b>로 경향을 잽니다. 모든 숫자는 공개 자료에서 자동 계산되며 손으로 고치지 않습니다.</p>'
        # 요약 표
        def pc(x): return f'{x:+}%' if x is not None else '–'
        rows = []
        for k, v in [('종합', T)] + [(k, px_sector(k)) for k in ('축산', '수산', '농산')] + [('원가 압력', C)]:
            m = (v or {}).get('metrics') or {}
            if not m or not m.get('n'): continue
            c = m.get('cross'); ctxt = (str(c['ago']) + '일 전 ' + c['kind']) if c else '없음'
            rows.append(f'<tr><td><a href="#{E(k)}"><b>{E(k)}</b></a></td><td class="num">{m["last"]:,.2f}</td><td>{regime_badge(m)}</td><td class="num">{pc(m.get("chg_s"))}</td><td class="num">{pc(m.get("chg_l"))}</td><td class="num">{(m.get("slope") or 0):+.2f}</td><td class="num">{m.get("vol") if m.get("vol") is not None else "–"}</td><td class="num">{m.get("pos")}%</td><td class="mini">{E(ctxt)}</td></tr>')
        if rows: b += '<h2>한눈에</h2><div class="tscroll"><table class="t"><tr><th>지수</th><th class="num">지금</th><th>추세</th><th class="num">5일</th><th class="num">20일</th><th class="num">20일선 기울기(%/일)</th><th class="num">변동성(%/일)</th><th class="num">기간 내 위치</th><th>최근 교차</th></tr>' + ''.join(rows) + '</table></div>'
        b += f'<h2 id="종합">종합 지수</h2>' + block('종합', T, color='var(--ink)', note='종합은 세 갈래가 모두 있는 날부터 시작합니다. 축산 기록이 2026-09-28부터라 아직 한 달치입니다 — 날마다 한 점씩 길어집니다.')
        b += '<h2 id="축산">축산 지수</h2>' + block('축산', px_sector('축산'), color='var(--brick)')
        pm = (px_sector('축산').get('parts_metrics') or {})
        if pm: b += '<h3>구성 품목</h3><div class="tscroll"><table class="t"><tr><th>품목</th><th class="num">지금(원/㎏)</th><th>추세</th><th class="num">5일</th><th class="num">20일선 대비</th><th class="num">변동성</th></tr>' + ''.join(f'<tr><td><a href="{slug("축산", pk)}">{E(pk)}</a></td><td class="num">{m["last"]:,.0f}</td><td>{regime_badge(m)}</td><td class="num">{pc(m.get("chg_s"))}</td><td class="num">{(m["last"] / m["ma_l"] - 1) * 100:+.1f}%</td><td class="num">{m.get("vol") if m.get("vol") is not None else "–"}</td></tr>' for pk, m in pm.items() if m and m.get('n', 0) >= 3) + '</table></div>'
        sv = px_sector('수산')
        b += '<h2 id="수산">수산 지수</h2>' + block('수산', sv, color='#2f5f8a', note='일별은 수협 위판 자료가 올라오는 달의 거래일(금액 상위 어종, 하루 1톤 이상 거래만)로 만듭니다. 달이 바뀌면 그달 일별을 저장해 두고 이어 붙입니다.')
        if sv.get('monthly') and len(sv['monthly']) >= 4:
            b += '<h3>월별 수산 지수</h3>' + block('수산(월별)', sv, monthly=True, color='#2f5f8a')
        elif sv.get('monthly'):
            b += '<p class="mini">월별 수산 지수: ' + ' → '.join(f'{d[2:].replace(chr(45), ".")}월 {v:,.1f}' for d, v in sv['monthly']) + ' (달 집계가 4개 넘게 쌓이면 월별 차트를 그립니다)</p>'
        b += '<h2 id="농산">농산 지수</h2>' + block('농산', px_sector('농산'), color='var(--moss)', note='공영도매시장 26곳의 ㎏ 단위 정산 거래만 씁니다(도매시장 안 수산 부류·가공품은 뺌). 토요일 반쪽 장(거래 금액이 평소의 6할 아래)은 뺍니다. 가을에는 배추·무 같은 김장 채소 비중이 커져 지수가 그 품목의 계절 흐름을 많이 따릅니다.')
        gr = px_sector('농산').get('groups') or {}
        if gr:
            b += '<h3>부류별 — 어느 부류가 끌고 가나</h3><div class="tscroll"><table class="t"><tr><th>부류</th><th class="num">거래금액 비중</th><th class="num">품목</th><th class="num">지수</th><th>추세</th><th class="num">5일 · 20일</th><th class="num">20일선 기울기</th><th class="num">변동성</th><th>흐름</th></tr>'
            for g, v in sorted(gr.items(), key=lambda x: -x[1].get('share', 0)):
                m = v.get('metrics') or {}
                if not m.get('n'): continue
                cls = 'up' if m['regime'] == '상승 추세' else 'dn' if m['regime'] == '하락 추세' else 'flat'
                b += f'<tr><td><b>{E(g)}</b></td><td class="num">{v.get("share", 0)}%</td><td class="num">{v.get("items", 0)}</td><td class="num">{m["last"]:,.1f}</td><td>{regime_badge(m)}</td><td class="num">{pc(m.get("chg_s"))} · {pc(m.get("chg_l"))}</td><td class="num">{(m.get("slope") or 0):+.2f}</td><td class="num">{m.get("vol") if m.get("vol") is not None else "–"}</td><td>{spark([x[1] for x in v["daily"][-40:]], w=90, h=26, cls=cls)}</td></tr>'
            b += '</table></div><p class="mini">부류는 tools/crop_groups.json 의 표로 나눕니다(과일·채소·양념채소·서류·곡물·버섯). 비중은 그린 기간의 거래금액.</p>'
        # 품목별 경향 순위
        b += '<h2 id="rank">품목별 경향 순위 — 가장 가파르게 오르는·내리는 품목</h2><p class="mini">최근 7일 안에 값이 있고, 하루 1톤 넘게 거래되며, 변동성이 20%/일 아래인 품목만(20일선 기울기 순 — 규격이 섞여 값이 널뛰는 품목과 철 끝물은 뺌). 추세는 「지금까지의 흐름」이지 예보가 아니며, 예보 칸은 품목 화면의 예보와 같습니다. 두 칸이 어긋나는 품목(오르는 추세인데 내림 예보)이 바로 전환 후보입니다.</p>'
        b += f'<h3>오르는 추세 {len(TR_UP)}품목</h3>' + tr_table(TR_UP[:12]) + (f'<p class="mini">외 {len(TR_UP) - 12}품목은 <a href="/f/">품목별</a>에서.</p>' if len(TR_UP) > 12 else '')
        b += f'<h3>내리는 추세 {len(TR_DN)}품목</h3>' + tr_table(TR_DN[:12]) + (f'<p class="mini">외 {len(TR_DN) - 12}품목.</p>' if len(TR_DN) > 12 else '')
        if TR_X: b += f'<h3>최근 3일 안 교차 발생 {len(TR_X)}품목</h3><p class="mini">5일선이 20일선을 뚫은 품목. 골든(위로)은 오름 전환, 데드(아래로)는 내림 전환의 초기 신호로 읽되, 변동성이 높은 품목은 가짜 교차가 잦습니다.</p>' + tr_table(TR_X[:12])
        # 원가 압력
        b += '<h2 id="원가 압력">원가 압력 지수 — 사료·기름·환율·가스</h2><p class="mini">값을 밀어 올리는 쪽의 지수입니다. 2년치라 20일선·골든/데드 크로스가 제대로 보입니다. 원가가 산지 값에 옮겨 가는 데는 보통 1~4개월이 걸립니다(사료 → 돼지·닭 3~6개월).</p>'
        b += block('원가 압력', C, color='#8a5a2f')
        if C.get('metrics_1y'): b += f'<p class="mini">최근 1년만 보면: {regime_badge(C["metrics_1y"])} {E(regime_text(C["metrics_1y"]))}.</p>'
        cpm = C.get('parts_metrics') or {}
        NM = {'feed': '사료 원가 지수(원/㎏)', 'diesel': '경유 선물(달러/갤런)', 'usdkrw': '원/달러', 'natgas': '천연가스 선물(달러)'}
        if cpm:
            def ctx(m): c = m.get('cross'); return (str(c['ago']) + '일 전 ' + c['kind']) if c else '없음'
            b += '<h3>구성 지표</h3><div class="tscroll"><table class="t"><tr><th>지표</th><th class="num">지금</th><th>추세</th><th class="num">5일</th><th class="num">20일</th><th class="num">20일선 대비</th><th>최근 교차</th></tr>' + ''.join(f'<tr><td>{E(NM.get(pk, pk))} <small>무게 {PX.get("cost_weights", {}).get(pk, "")}</small></td><td class="num">{m["last"]:,.2f}</td><td>{regime_badge(m)}</td><td class="num">{pc(m.get("chg_s"))}</td><td class="num">{pc(m.get("chg_l"))}</td><td class="num">{(m["last"] / m["ma_l"] - 1) * 100:+.1f}%</td><td class="mini">{E(ctx(m))}</td></tr>' for pk, m in cpm.items() if m and m.get('n', 0) >= 3) + '</table></div>'
        # 세계 요인 활성 점수
        b += '<h2 id="세계">세계 요인 활성 점수</h2>'
        wd = WS.get('daily') or []
        if len(wd) >= 2:
            b += svg_line([(str(x[0]), x[1]) for x in wd], w=720, h=140) if svg_line else ''
            b += f'<p class="mini">{E(wd[0][0])} ~ {E(wd[-1][0])} · 오늘 {wd[-1][1]}점(경보 {(WS.get("alarms") or [[0, 0]])[-1][1]}건 · 켜진 요인 {(WS.get("n") or [[0, 0]])[-1][1]}건). {E(WS.get("src", ""))}. 이 점수가 오르는데 갈래 지수가 아직 안 움직였다면, 몇 주 뒤의 값 변화를 먼저 보고 있는 것일 수 있습니다.</p>'
        else:
            b += f'<p class="mini">세계 요인 감시는 2026-10-28부터 날마다 기록합니다(오늘 {wd[-1][1] if wd else 0}점, 경보 {(WS.get("alarms") or [[0, 0]])[-1][1]}건). 점이 쌓이면 여기에 선으로 그립니다. <a href="/world/">오늘 켜진 요인 →</a></p>'
        b += '<h2 id="score">경향 판정은 맞았나</h2>' + tsc_html(TSC['sum_items'], '품목') + tsc_html(TSC['sum_index'], '지수')
        # 읽는 법
        b += '<h2 id="how">읽는 법과 판정 기준</h2><table class="t"><tr><th>항목</th><th>뜻</th><th>기준</th></tr>'
        for a, bb, c in (('5일선 · 20일선', '최근 5일(단기)·20일(장기) 평균. 월별 지수는 1개월·3개월', '단기선이 장기선을 아래에서 위로 뚫으면 골든 크로스(오름 전환 신호), 위에서 아래로 뚫으면 데드 크로스'),
                         ('추세 판정', '20일선의 최근 10점 회귀 기울기(마지막 값 대비 %/일)와 값이 20일선 위·아래 어디인지', '기울기 +0.15%/일 넘고 값이 선 위 → 상승 추세 · −0.15%/일 아래이고 값이 선 아래 → 하락 추세 · ±0.15% 안 → 횡보 · 엇갈림 → 전환 중(월별은 ±2%/월)'),
                         ('±2σ 띠', '20일 표준편차의 2배 폭. 띠 밖은 평소 흐름에서 벗어난 값', '띠 위로 나가면 과열, 아래로 나가면 과매도 쪽 — 되돌림이 잦음'),
                         ('변동성', '일별 수익률(로그 변화)의 20일 표준편차', '1.5% 아래 낮음 · 3.5% 아래 보통 · 그 위 높음(높으면 하루 값에 끌려가지 말 것)'),
                         ('기간 내 위치', '그린 기간의 최저 0% ~ 최고 100% 사이 지금 위치', '90% 위·10% 아래는 추세가 늙었을 가능성'),
                         ('지수 만드는 법', '품목별 값 ÷ 그 품목 기준값(처음 보인 5일 평균)의 로그를 거래금액 비중으로 가중 평균 → 지수. 고정 가중 기하 지수(라스파이레스 계열)', '그날 없는 품목은 빼고 가중치를 다시 정규화 · 반쪽 장 제외 · 한 품목 변동은 ±120%로 자름')):
            b += f'<tr><td><b>{E(a)}</b></td><td class="mini">{E(bb)}</td><td class="mini">{E(c)}</td></tr>'
        b += '</table><p class="note"><b>한계</b> — 기록이 2026년 9월 중순부터라 20일선·교차는 이제 막 의미를 갖기 시작했고, 1년 전 같은 달과 비교하는 계절 조정은 내년 가을부터 가능합니다. 지수는 「무엇을 살지」가 아니라 「지금 어느 쪽으로 흐르는지」를 보여 줍니다. 품목별 예보는 <a href="/f/">품목별</a>에서, 지수가 왜 움직였는지는 <a href="/world/">세계 요인</a>과 <a href="/signal/">거시 근거</a>에서 봅니다.</p>'
        b += f'<h2 id="data">자료 내려받기·인용</h2><p>지수 원자료(날짜별 값·계량 요약)는 <a href="/data/pindex.json">pindex.json</a>으로 공개합니다(저작자 표시 4.0, 갱신 {E(PX.get("at", "")[:16])}). 인용은 「박씨팜 농축수산물 물가 지수, {E(TODAY)}, thecloudstay.github.io/bakssifarm/index/」로 적어 주세요. 산식·판정 기준은 위 표와 <a href="/method/">예측 기법</a> 5-1절에, 바뀐 내용은 개선 기록에 남깁니다.</p>'
        b += '<p class="mini">같이 보기: <a href="/">오늘 예보</a> · <a href="/method/">예측 기법</a> · <a href="/track/">적중 기록</a> · <a href="/data/">자료 대장</a></p>'
        ld = {'@context': 'https://schema.org', '@type': 'Dataset', 'name': '박씨팜 물가 지수', 'url': BASE + '/index/', 'description': '한우·돼지 경락가, 수협 위판가, 공영도매시장 정산가를 거래금액 가중으로 묶은 농축수산물 물가 지수와 원가 압력 지수. 5일선·20일선·기울기로 경향 판정.', 'dateModified': TODAY, 'license': 'https://creativecommons.org/licenses/by/4.0/', 'creator': {'@type': 'Organization', 'name': '박씨팜'}}
        tm = T.get('metrics') or {}
        write('/index/', shell('/index/', f'농축수산물 물가 지수 {TODAY} — 종합 {tm.get("last", "")} {tm.get("regime", "")} | 박씨팜', '경락가·위판가·도매가를 한 줄 지수로 묶어 주식 차트처럼 5일선·20일선·기울기·변동성으로 경향을 잽니다. 축산·수산·농산·종합·원가 압력 지수.', b, jsonld=ld, og='/og/index.png'), '0.9')
    def gauge(pct, state):
        cls = 'hi' if ('고평가' in state or '높음' in state) else 'lo' if ('저평가' in state or '낮음' in state) else ''
        return f'<span class="gauge {cls}" title="최근 1년 비율 백분위 {pct}"><i style="left:{max(2, min(98, pct))}%"></i></span>'
    def gstate(st):
        cls = 'up' if ('고평가' in st or '높음' in st) else 'dn' if ('저평가' in st or '낮음' in st) else 'flat'
        return f'<span class="fx {cls}">{E(st)}</span>'
    def gap_row(x):
        dc = x.get('decomp') or {}
        dec = (f'국산 {dc["dom"]:+}% · 현지 {dc["org_local"]:+}% · 환율 {dc["fx"]:+}%' if dc and dc.get('org_local') is not None and dc.get('fx') is not None else f'도매 {dc["dom"]:+}% · 환율 {dc["fx"]:+}%' if dc and dc.get('fx') is not None else '–')
        return (f'<tr><td><a href="#{E(x["id"])}"><b>{E(x["name"])}</b></a><div class="mini">{E(x["sector"])} · 기준 {x["n_base"]}일' + (f' · <b>{E(x["date"][5:])} 자료(새 위판 자료 대기)</b>' if x.get('stale') else '') + '</div></td><td class="num">{x["dom"]:,}</td><td class="num">{x["org_krw"]:,}</td><td class="num">{x["ratio"]:.2f}<div class="mini">평소 {x["median"]:.2f}</div></td>'
                f'<td class="num">{x["dev"]:+}%</td><td>{gauge(x["pct"], x["state"])}<div class="mini">백분위 {x["pct"]} · z {x["z"]:+}</div></td><td>{gstate(x["state"])}{" <b class=\"mini\">강함</b>" if x.get("strong") else ""}</td><td class="mini">{E(dec)}</td></tr>')
    def gap_strip():
        if not GOK: return ''
        pick = (GHOT + [x for x in sorted(GOK, key=lambda x: -abs(x['z'])) if x not in GHOT and not x.get('stale')])[:3]
        cards = ''.join(f'<a class="card px {"up" if ("고평가" in x["state"] or "높음" in x["state"]) else "dn" if ("저평가" in x["state"] or "낮음" in x["state"]) else "flat"}" href="/gap/#{E(x["id"])}"><h3>{E(x["name"].split(" ↔ ")[0])} <small>↔ {E(x["name"].split(" ↔ ")[1])}</small></h3><div class="big">{x["dev"]:+}%</div><p class="mini">평소 비율 대비 · 백분위 {x["pct"]} · {E(x["state"])}</p>{gauge(x["pct"], x["state"])}</a>' for x in pick)
        return f'<h2 id="gap">오늘의 갭 기회 — 해외와 국내 값 차이가 벌어진 곳 <small class="mini">{len(GHOT)}/{len(GOK)}짝</small></h2><p class="mini">국산 값 ÷ 현지 값(환율 환산)의 비율이 평소 범위(최근 1년 백분위 15~85)를 벗어나면 갭입니다. 갭은 평균으로 되돌아오는 경향이 있어 수입·유통·급식 업체의 매입 시점 참고가 됩니다.</p><div class="grid3">' + cards + '</div><p class="mini"><a href="/gap/">갭 기회 전체(9짝)·되돌림 채점·구독 →</a></p>'
    def gap_page():
        b = '<p class="crumb"><a href="/">박씨팜</a> › 갭 기회</p><h1 class="title">갭 기회 — 해외와 국내 값 차이가 벌어질 때</h1>'
        b += f'<p class="lead">같은 쓰임의 물건은 나라가 달라도 값이 운임·관세·품질 차이만큼만 떨어져 있고, 그 차이는 보통 좁은 띠 안에 머뭅니다. 띠를 벗어나면 — 국산이 현지보다 유난히 비싸거나 싸지면 — 누군가는 수입을 늘리고 누군가는 출하를 당기며 띠로 되돌아옵니다. 박씨팜은 원산지 현지 시세(세계 공개 연동창구)와 환율, 국산 경락가·위판가·도매가를 날마다 맞대어 <b>그 띠를 벗어난 순간</b>을 잡고, 되돌아왔는지까지 채점합니다. {E(GAP.get("date", TODAY))} 기준 짝 {len(GOK)}개 가운데 갭 {len(GHOT)}개.</p>'
        if not GOK:
            b += '<p class="note">아직 계산할 자료가 모이지 않았습니다. 매일 아침 자동으로 다시 계산합니다.</p>'
        else:
            b += '<h2>한눈에</h2><div class="tscroll"><table class="t"><tr><th>짝(국산 ↔ 현지)</th><th class="num">국산 원/㎏</th><th class="num">현지 환산 원/㎏</th><th class="num">비율</th><th class="num">평소 대비</th><th>1년 백분위</th><th>판정</th><th>4주 변화 분해</th></tr>' + ''.join(gap_row(x) for x in sorted(GOK, key=lambda x: -abs(x['z']))) + '</table></div>'
            b += '<p class="mini">비율의 절댓값은 품질·등급·관세가 다른 두 물건의 거리라 뜻이 없고, 「평소보다 벌어졌나」만 봅니다. 환율 갭(바나나·오렌지)은 현지 창구가 없어 도매가와 환율만 맞댑니다.</p>'
            for x in sorted(GOK, key=lambda x: -abs(x['z'])):
                col = 'var(--brick)' if ('고평가' in x['state'] or '높음' in x['state']) else '#2f5f8a' if ('저평가' in x['state'] or '낮음' in x['state']) else 'var(--moss)'
                b += f'<h2 id="{E(x["id"])}">{E(x["name"])} {gstate(x["state"])}{" <b class=\"mini\">강한 갭</b>" if x.get("strong") else ""}</h2>' + (f'<p class="note">국산 쪽 자료가 {E(x["date"])}까지라(수협 위판 자료는 달 단위로 올라옴) 오늘의 갭으로는 세지 않고 참고로만 둡니다.</p>' if x.get('stale') else '')
                b += f'<div class="grid3"><div class="card"><h3>국산</h3><div class="big">{x["dom"]:,}<i>원/㎏</i></div><p>{E(x["dom_desc"])} · {E(x["date"])}</p></div><div class="card"><h3>현지 환산</h3><div class="big">{x["org_krw"]:,}<i>원/㎏</i></div><p>{E(x["org_desc"])}' + (f' · 현지 {x["org_local"]:,} {E(x["org_unit"])}({E(x["org_date"])})' if x.get('org_local') is not None else '') + f' · 환율 {x["fx"]:,.2f}원/{E(x["ccy"])}</p></div><div class="card"><h3>비율 {x["ratio"]:.2f} <small>평소 {x["median"]:.2f}</small></h3><div class="big">{x["dev"]:+}<i>%</i></div><p>최근 1년 백분위 {x["pct"]} · z {x["z"]:+} · 기준 {x["n_base"]}일({E(x["base_from"])}~)</p>{gauge(x["pct"], x["state"])}</div></div>'
                b += stock_svg(x['series'], color=col, label=x['name'] + ' 비율')
                b += f'<p class="mini">비율(국산 ÷ 현지 환산)의 흐름 · 띠는 20일 ±2σ · {len(x["series"])}일</p>'
                dc = x.get('decomp')
                if dc:
                    parts = [('비율', dc['ratio']), ('국산', dc['dom'])] + ([('현지 값(현지 통화)', dc['org_local'])] if dc.get('org_local') is not None else []) + ([('환율(원/' + x['ccy'] + ')', dc['fx'])] if dc.get('fx') is not None else [])
                    b += '<h3>4주 동안 무엇이 움직였나</h3><dl class="kv tm">' + ''.join(f'<dt>{E(k)}</dt><dd class="{"up" if v > 0 else "dn" if v < 0 else ""}">{v:+}%</dd>' for k, v in parts) + f'</dl><p class="mini">{E(dc["from"])} → {E(x["date"])}. 비율 변화 ≈ 국산 변화 − 현지 변화 − 환율 변화.</p>'
                b += '<h3>참고 행동</h3><div class="grid3">' + ''.join(f'<div class="card"><h3>{E(k)}</h3><p>{E(v)}</p></div>' for k, v in x['acts'].items()) + '</div>'
                if x.get('note'): b += f'<p class="note">{E(x["note"])}</p>'
                if x.get('metrics') and x['metrics'].get('n', 0) >= 3: b += f'<p class="mini">비율의 경향: {regime_badge(x["metrics"])} {E(regime_text(x["metrics"]))}</p>'
        sc = GAP.get('score') or {}
        b += '<h2 id="score">갭은 정말 되돌아오나 — 채점</h2>'
        if sc.get('n'):
            b += f'<p>갭으로 판정한 날의 4주 뒤 |z|가 절반 아래로 줄어든 비율: <b>{sc["closed"]}/{sc["n"]}건({sc["rate"]}%)</b>. 되돌아오지 않은 갭도 그대로 둡니다.</p><div class="tscroll"><table class="t"><tr><th>판정일</th><th>짝</th><th>판정</th><th class="num">z 그때</th><th class="num">z 4주 뒤</th><th>되돌림</th></tr>' + ''.join(f'<tr><td>{E(r["d"])}</td><td>{E(r["pair"])}</td><td>{E(r["state"])}</td><td class="num">{r["z0"]:+}</td><td class="num">{r["z1"]:+}</td><td class="{"ok" if r["closed"] else "bad"}">{"됨" if r["closed"] else "아직"}</td></tr>' for r in reversed(sc.get('rows') or [])) + '</table></div>'
        else: b += f'<p class="mini">갭 판정을 날마다 기록해 두고(기록 {sc.get("n_days", 0)}일째) 4주 뒤 |z|가 절반 아래로 줄었는지 채점합니다. 첫 채점은 11월 말.</p>'
        b += '<p class="note"><b>갭이 벌어졌을 때 수입으로 메우려면</b> — <a href="/source/">원산지 거래 정보</a>에서 원산지 후보·오늘 상태·현지 시세·요건을 보고, <a href="/source/#demand">수입 공동 수요 예약</a>에 필요량을 적어 두면 등록 수입·유통업체 견적으로 이어집니다(돈·물건은 업체와 직접).</p>'
        b += '<h2 id="subscribe">갭 경보 구독</h2><div class="grid2"><div class="card on"><h3>업체 구독 — 우리 품목 갭 경보</h3><p>사는 품목을 등록하면 그 짝의 갭이 벌어지는 날 아침에 알려 드리고, 원산지 현지 시세 표·환율·되돌림 채점을 함께 드립니다. 시험 기간 무료, 유료 전환 전 미리 안내.</p><p style="margin-top:10px;"><a class="btn prime" href="/pro/#gap">업체 등록·구독 신청</a></p></div><div class="card"><h3>무료로 보는 것</h3><p>이 화면의 오늘 갭 표와 비율 그래프는 누구나 봅니다. 날마다 갱신되고 기록은 지우지 않습니다.</p><p class="mini" style="margin-top:8px;">관련: <a href="/world/#global">원산지 현지 시세 표</a> · <a href="/index/">물가 지수</a> · <a href="/f/">품목별 예보</a></p></div></div>'
        if GCAND:
            STC = {'운영': 'ok', '운영(참고)': 'ok', '준비': 'wait', '열쇠': 'wait', '자료 없음': 'bad', '원가 층': '', '범위 밖': ''}
            b += '<h2 id="candidates">짝 후보 대장 — 무엇을 왜 넣고, 무엇이 빠져 있나</h2><p class="mini">고르는 기준 넷: 연 수입액이 큰가 · 국산과 수입이 같은 자리를 두고 겨루나 · 소비자·언론 체감이 큰가 · 국산 일별 시세와 현지 시세를 날마다 받을 수 있나. 수입액은 공개 통계 근사(억 달러). 「열쇠」는 무료 등록 열쇠(농산물유통정보·관세청 수출입실적·미국 농무부 시장소식)만 있으면 붙는 것.</p>'
            b += '<div class="tscroll"><table class="t"><tr><th>품목</th><th class="num">수입액</th><th>원산지</th><th>국산 짝</th><th>체감</th><th>국산 창구</th><th>현지 창구</th><th>상태</th><th>다음 할 일</th></tr>'
            for c in GCAND: b += f'<tr><td><b>{E(c["품목"])}</b></td><td class="num">{c["수입액"]}</td><td class="mini">{E(c["원산지"])}</td><td class="mini">{E(c["국산"])}</td><td class="mini">{E(c["체감"])}</td><td class="mini">{E(c["국산창구"])}</td><td class="mini">{E(c["현지창구"])}</td><td class="{STC.get(c["상태"], "")}">{E(c["상태"])}</td><td class="mini">{E(c["할일"])}</td></tr>'
            b += '</table></div>'
        b += f'<h2 id="how">방법과 한계</h2><p class="mini">{E(GAP.get("method", ""))}</p><ul class="mini"><li>국산과 현지는 등급·품질·규격이 다른 물건이라 비율의 수준이 아니라 변화만 읽습니다. 관세·운임 계수를 억지로 정하지 않습니다.</li><li>한우·돼지 경락가는 2026년 9월 말부터 기록해 1년치 되채움이 끝나기 전까지 백분위의 바탕이 짧습니다(기준 일수를 함께 표시).</li><li>수산 위판 짝은 위판 자료가 올라오는 달까지만 이어집니다. 닭고기는 국산 일별 창구가 없어 아직 짝이 없습니다.</li><li>갭 기회는 참고 정보이며 거래·투자 권유가 아닙니다. 박씨팜은 사고팔지 않고 이 숫자에 이해관계가 없습니다.</li></ul>'
        ld = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': '박씨팜 갭 기회', 'url': BASE + '/gap/', 'dateModified': TODAY, 'description': '해외 원산지 시세(환율 환산)와 국산 경락가·위판가·도매가의 비율이 평소 범위를 벗어난 갭을 날마다 찾아 수입·유통·급식 업체의 매입 시점 참고로 제공.'}
        write('/gap/', shell('/gap/', f'갭 기회 {E(GAP.get("date", TODAY))} — 해외·국내 값 차이가 벌어진 짝 {len(GHOT)}/{len(GOK)} | 박씨팜', '원산지 현지 시세와 환율, 국산 경락가·위판가·도매가를 날마다 맞대어 값 차이가 평소 띠를 벗어난 순간을 잡고 되돌림까지 채점합니다. 한우↔미국 쇠고기, 돼지↔미국·유럽연합, 넙치·방어·참돔↔노르웨이 연어, 바나나·오렌지↔환율.', b, jsonld=ld, og='/og/gap.png'), '0.9')
    def olv_chip(o):
        c = 'hi' if o.get('level') == 2 else 'mid' if o.get('level') == 1 else ''
        return f'<span class="org {c}" title="{E(o.get("standing", ""))}">{E(o["ko"])} {int(o["share"] * 100)}%</span>'
    def src_block(r, compact=False):
        """수입 품목 한 줄: 원산지 후보·오늘 상태·현지 시세·관세청 단가·요건·수요 모집"""
        b = f'<div class="card src"><h3>{E(r["import"])} <small class="mini">전가 {r.get("pt")} · 시차 {E(r.get("lag", ""))}</small></h3>'
        b += '<p><b>원산지 후보</b>(수입 비중 근사 · 오늘 원산지 상태): ' + ' '.join(olv_chip(o) for o in r['origins']) + '</p>'
        if r.get('prices'): b += '<p class="mini">현지 시세: ' + ' · '.join(f'{E(x["name"])} {x["last"]:,.2f} {E(x["unit"])}({E(x["date"][:7])}' + (f', 4주 {x["w4"]:+}%' if x.get('w4') is not None else '') + ')' for x in r['prices']) + '</p>'
        if r.get('unit_price') and r['unit_price'].get('usd_kg'): b += f'<p class="mini">관세청 수입 단가: {E(r["unit_price"]["name"])} {r["unit_price"]["usd_kg"]:,.2f} 달러/㎏' + (f'(≈ {r["unit_price"]["krw_kg"]:,}원/㎏)' if r['unit_price'].get('krw_kg') else '') + f' · {E(str(r["unit_price"].get("ym", "")))}</p>'
        if r.get('note'): b += f'<p class="mini">{E(r["note"])}</p>'
        if not compact: b += f'<p class="mini"><b>요건</b> — {E(r.get("req", ""))}</p>'
        if r.get('open'): b += f'<p style="margin-top:8px;"><a class="btn prime" href="/source/#demand" data-item="{E(r["import"])}">이 품목 수입 공동 수요 예약</a></p>'
        return b + '</div>'
    def source_page():
        items = SRC.get('items') or []; hot = [r for r in items if r['signals']]
        b = '<p class="crumb"><a href="/">박씨팜</a> › 원산지 거래 정보</p><h1 class="title">원산지 거래 정보 — 국내가 부족할 때 어디서 들여오나</h1>'
        b += f'<p class="lead">동해안 오징어 어획이 줄면 페루·칠레·아르헨티나에서, 꽃게가 빠듯하면 중국·베트남에서 — 국내 공급이 부족해지는 품목마다 <b>어느 원산지에서, 지금 거기 상황은 어떤지, 현지 값과 수입 단가는 얼마인지, 무슨 요건이 붙는지</b>를 한 자리에 모읍니다. 수요가 모이면 영업등록을 가진 수입·유통업체가 견적을 냅니다. {E(SRC.get("date", TODAY))} 기준 부족 신호 품목 {len(hot)}개, 수요 예약 열린 품목 {SRC.get("n_open", 0)}개.</p>'
        b += f'<p class="note"><b>박씨팜의 자리</b> — {E(SRC.get("principle", ""))}</p>'
        if hot:
            b += '<h2>지금 부족 신호가 켜진 품목</h2><div class="tscroll"><table class="t"><tr><th>수입 품목</th><th>국내 신호</th><th>원산지 후보(비중 · 오늘 상태)</th><th class="num">신호 점수</th><th>수요 예약</th></tr>'
            for r in hot:
                sg = ' · '.join(f'<b>{E(x["item"])}</b> {E(x["kind"])}' + (f'({E(x["why"][:40])})' if x.get('why') else '') for x in r['signals'][:3])
                b += f'<tr><td><a href="#{E(r["import"])}"><b>{E(r["import"])}</b></a><div class="mini">{E(r["sector"])} · 전가 {r.get("pt")} · 시차 {E(r.get("lag", ""))}</div></td><td class="mini">{sg}</td><td>{" ".join(olv_chip(o) for o in r["origins"][:5])}</td><td class="num">{r["score"]}</td><td>{"<a href=\"#demand\">열림</a>" if r.get("open") else "<span class=\"mini\">–</span>"}</td></tr>'
            b += '</table></div><p class="mini">신호: 공급 빠듯(창고 재고·위판 물량·값), 어획 감소(앞달 대비 위판 물량 −25% 아래), 예보 오름(세기 3 이상), 갭 고평가(국산이 현지 환산보다 평소 대비 5% 넘게 비쌈), 축산 출하 판단. 원산지 상태는 세계·원산지 요인 감시의 오늘 단계(빨강 경보·노랑 주의).</p>'
            for r in hot: b += f'<div id="{E(r["import"])}"></div>' + src_block(r)
        b += '<h2 id="all">수입 품목 73개 전체 — 원산지와 요건</h2><p class="mini">신호가 없어도 「어디서 오나」는 언제나 봅니다. 비중은 공개 통계 근사치, 해마다 갱신.</p><div class="tscroll"><table class="t"><tr><th>수입 품목</th><th>갈래</th><th>원산지(비중)</th><th class="num">전가</th><th>시차</th><th>국내 경쟁·투입 품목</th></tr>'
        for r in items: b += f'<tr><td><b>{E(r["import"])}</b></td><td class="mini">{E(r["group"])}</td><td>{" ".join(olv_chip(o) for o in r["origins"][:6])}</td><td class="num">{r.get("pt")}</td><td class="mini">{E(r.get("lag", ""))}</td><td class="mini">{E(r["dom_pat"].replace("|", " · "))}</td></tr>'
        b += '</table></div>'
        b += '<h2>갈래별 수입 요건(요약)</h2><ul class="mini">' + ''.join(f'<li><b>{E(k)}</b> — {E(v)}</li>' for k, v in {'수산': '수산물 수입신고(식약처 수입식품정보마루) · 정밀검사 대상 여부 · 원산지 표시 · 일부 어종은 수입 금지·조정관세(냉동 오징어·명태 등은 품목번호별 확인)', '축산': '수입위생평가를 통과한 나라·작업장만 가능(검역본부 지정) · 검역 + 식약처 수입신고 · 자유무역협정 관세율은 나라·연도별 다름', '농산': '식물검역(수입 금지 식물·소독) + 식약처 수입신고 · 잔류농약 검사 · 계절관세·저율관세할당 품목 확인'}.items()) + '</ul><p class="mini">품목번호별 관세율·조정관세·할당은 관세법령정보포털에서, 수입 가능 작업장은 수입식품정보마루에서 확인합니다. 박씨팜은 요건을 안내할 뿐 대행하지 않습니다.</p>'
        # 수요 예약 양식(결제 없음, 확약 아님)
        opts = [r['import'] for r in items if r.get('open')] or [r['import'] for r in hot[:10]] or [r['import'] for r in items[:20]]
        b += '<h2 id="demand">수입 공동 수요 예약 — 돈도 물건도 오가지 않는 「필요량 적기」</h2><p>우리 업체가 다음 달 들여왔으면 하는 품목과 물량을 적습니다. 같은 품목 수요가 모이면 등록 수입·유통업체에 모인 물량을 알려 견적을 받게 하고, 그 결과(실제 수입 단가가 갭 신호 때 예상과 얼마나 맞았나)를 공개합니다. 박씨팜은 돈·물건·계약에 끼지 않습니다.</p>'
        b += G['form']('demand', [('row', [('sel', '품목', '수입 품목', True, opts + ['기타(직접 적기)']), ('text', '원산지희망', '희망 원산지(선택)', False, '예: 페루·칠레')]), ('row', [('text', '물량', '필요 물량(톤 또는 상자)', True, '예: 10톤'), ('text', '시기', '희망 시기', True, '예: 12월 초')]), ('row', [('sel', '업종', '업종', True, ['급식·식자재 유통', '수산물 가공·냉동·유통', '횟집·수산 외식 체인', '외식 프랜차이즈·대형마트·온라인몰', '육가공·정육 유통', '도매시장 중도매인·산지 유통인', '기타']), ('text', '상호', '상호', True, '')]), ('row', [('tel', '연락처', '연락처', True), ('text', '전자우편', '전자우편(선택)', False, '')]), ('area', '메모', '규격·등급·포장 등 조건(선택)', False, '')], '수요 예약 보내기', '/source/thanks/')
        b += '<h2>같이 보기</h2><p class="links"><a href="/gap/">갭 기회</a> · <a href="/world/#global">원산지 현지 시세 표</a> · <a href="/world/#imports">수입 품목 원산지 지도</a> · <a href="/opps/">수급 기회</a> · <a href="/pro/">업체 등록</a></p>'
        ld = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': '박씨팜 원산지 거래 정보', 'url': BASE + '/source/', 'dateModified': TODAY, 'description': '국내 공급이 부족한 농축수산물마다 수입 원산지 후보·오늘 원산지 상태·현지 시세·관세청 수입 단가·수입 요건을 정리하고 수입 공동 수요를 모읍니다.'}
        write('/source/', shell('/source/', f'원산지 거래 정보 — 국내가 부족할 때 어디서 들여오나 (신호 {len(hot)}품목) | 박씨팜', '동해안 오징어 어획 감소 → 페루·칠레처럼, 부족한 품목마다 수입 원산지 후보·오늘 상태·현지 시세·수입 단가·요건을 모으고 수입 공동 수요를 예약받습니다. 박씨팜은 거래에 끼지 않습니다.', b, jsonld=ld, og='/og/source.png'), '0.8')
        write('/source/thanks/', shell('/source/thanks/', '수요 예약이 접수되었습니다 | 박씨팜', '수요 예약 접수', '<h1 class="title">수요 예약이 접수되었습니다</h1><p class="lead">같은 품목 수요가 모이면 등록 수입·유통업체의 견적과 함께 연락드립니다. 박씨팜은 거래의 당사자가 아니며 돈·물건은 업체와 직접 주고받습니다. <a href="/source/">원산지 거래 정보로</a></p>', noindex=True))
    def world_home():
        if not WEV: return ''
        b = f'<h2>세계 요인 — 지금 값에 작용하는 것 <span class="mini">{WORLD.get("n_rules", len(WEV))}개 요인 감시 · 활성 {len(WACT)}</span></h2>'
        if WACT: b += '<ul class="alerts world">' + ''.join(world_card(e) for e in WACT[:5]) + '</ul>'
        else: b += '<p class="note">오늘은 기준을 넘은 세계 요인이 없습니다(달력 요인 포함).</p>'
        b += f'<p class="mini"><a href="/world/">기후·질병·지정학·정책·세계 상품·달력 요인 {WORLD.get("n_rules", len(WEV))}개의 오늘 상태 →</a></p>'
        return b
    def world_page():
        b = '<p class="crumb"><a href="/">박씨팜</a> › 세계 요인</p><h1 class="title">세계 요인 감시 — 값을 흔드는 바깥일</h1>'
        b += f'<p class="lead">브라질 조류인플루엔자, 후쿠시마 처리수, 엘니뇨, 호르무즈, 할당관세, 명절처럼 품목 밖에서 값을 흔드는 요인 {WORLD.get("n_rules", 0)}개를 매일 아침 재서 예보 점수에 더합니다. {E((WORLD.get("at") or "")[:16])} 기준 · 활성 {len(WACT)}(경보 {sum(1 for e in WACT if e["level"] == 2)}).</p>'
        CATS = ('기후·해양', '질병·방역', '지정학·에너지', '정책', '세계 상품', '원산지 시세', '사고·재해', '원가·경기', '수요·달력', '원산지', '국내 날씨', '국내 수급')
        b += '<div class="statusbar">' + ''.join(f'<span class="{"off" if any(e["level"] == 2 and e["cat"] == c for e in WACT) else "soon" if any(e["cat"] == c for e in WACT) else "on"}"><i></i>{E(c)} {sum(1 for e in WACT if e["cat"] == c)}/{sum(1 for e in WEV if e["cat"] == c)}</span>' for c in CATS if any(e['cat'] == c for e in WEV)) + '</div>'
        b += f'<p class="mini">감시 범위: 주제 요인 {WORLD.get("n_topic", 0)} · 원산지 나라 {WORLD.get("n_origin_all", 0)}(오늘 측정 {WORLD.get("n_origin", 0)}) · 수입 품목 {WORLD.get("n_import_items", 0)} · 국내 주산지 {WORLD.get("n_crop_points", 0)}곳 · 뉴스 자료 {E(WORLD.get("news_src", ""))} · 측정 {WORLD.get("elapsed_sec", 0)}초. 방법은 <a href="/method/">예측 기법</a>에.</p>'
        if WACT: b += '<h2>지금 활성</h2><ul class="alerts world">' + ''.join(world_card(e) for e in WACT) + '</ul>'
        # 수입 품목 원산지 지도
        if IM.get('items'):
            b += '<h2 id="imports">수입 품목 원산지 지도 — 어디서 오나, 오늘 거기는 어떤가</h2><p class="mini">주요 수입 농축수산물·투입재 ' + str(len(IM['items'])) + '개의 원산지 비중(근사치)과 그 나라의 오늘 단계. 원산지 사건은 비중 × 전가 무게로 국내 경쟁·하류 품목 점수에 들어갑니다. 비중은 공개 통계 기반 근사치이며 해마다 갱신합니다.</p>'
            for grp in IM.get('groups') or []:
                rows = [it for it in IM['items'] if it.get('group') == grp]
                if not rows: continue
                b += f'<h3>{E(grp)}</h3><table class="t imtab"><tr><th>수입 품목</th><th>원산지(비중)</th><th>국내 영향</th></tr>'
                for it in rows:
                    org = ' · '.join(f'<span class="org {("hi" if OLV.get(re.sub(r"\(.*?\)", "", c).strip()) == 2 else "mid" if OLV.get(re.sub(r"\(.*?\)", "", c).strip()) == 1 else "")}">{E(c)} {int(s * 100)}%</span>' for c, s in it.get('origins', []))
                    t = it.get('competes') or it.get('inputs_for') or {}
                    names = [x['item'] for x in items if x['sector'] == t.get('sector') and (t.get('item') == '.' or re.fullmatch('(?:' + (t.get('item') or '.') + ')', akey(x['sector'], x['item'])))] if t else []
                    dom = ('경쟁: ' if it.get('competes') else '투입: ') + (', '.join(f'<a href="{slug(t["sector"], n)}">{E(n)}</a>' for n in names[:6]) if names else f'<span class="mini">{E(t.get("sector", ""))} {E((t.get("item") or "").replace("|", "·")[:30])}</span>') + f' <span class="mini">전가 {it.get("pt", "")} · 시차 {E(it.get("lag", ""))}' + (' · 수출 품목' if it.get('export') else '') + '</span>'
                    b += f'<tr><td><b>{E(it["name"])}</b>' + (f'<div class="mini">{E(it.get("scale", ""))}</div>' if it.get('scale') else '') + (f'<div class="mini">{E(it.get("note", ""))}</div>' if it.get('note') else '') + f'</td><td>{org}</td><td class="mini">{dom}</td></tr>'
                b += '</table>'
            b += '<p class="mini">원산지 표시 색: 빨강 = 오늘 경보, 노랑 = 주의. 나라별 상세는 아래 「원산지별 판」에.</p>'
        # 원산지별 판
        oe = [e for e in WEV if e.get('kind') == 'origin']
        if oe:
            b += '<h2 id="origins">원산지별 판 — 오늘 측정한 나라</h2><p class="mini">나라마다 공급 충격 뉴스·정치/무역 뉴스·통화 3개월 변동·엘니뇨 영향권을 잽니다. 1군(' + str(sum(1 for e in oe if e.get("tier") == 1)) + '개 나라)은 매일, 2군은 돌아가며 측정합니다.</p><ul class="alerts world">' + ''.join(world_card(e) for e in sorted(oe, key=lambda e: (-e['level'], -(e.get('tier') == 1), e['name']))) + '</ul>'
        # 세계 공개 연동창구 — 원산지 시세 계열·재난·주산지 날씨·대장
        GS = GL.get('series') or {}
        if GS:
            b += '<h2 id="global">세계 공개 연동창구 — 원산지에서 직접 받는 값</h2><p class="mini">한국 밖 정부·통계청·국제기구·대학이 여는 열쇠 없는 창구에서 날마다 받습니다(뉴스가 아니라 측정값이라 경보까지 올라갈 수 있음). 갱신 ' + E(GL.get('at', '')) + ' · 창구 ' + E(str(GL.get('n_series', len(GS)))) + '계열.</p>'
            b += '<div class="tscroll"><table class="t"><tr><th>계열</th><th>나라</th><th class="num">지금</th><th>단위 · 기준일</th><th class="num">1주</th><th class="num">4주</th><th class="num">3개월</th><th class="num">1년</th><th>흐름</th></tr>'
            ORDER = ['eu_pig_s', 'us_hog_net', 'us_beef_choice', 'us_steer_live', 'br_chicken', 'br_hog', 'br_cattle', 'br_soy', 'br_corn', 'no_salmon_fresh', 'eu_broiler', 'fao_fpi_food', 'fao_fpi_meat', 'fao_fpi_cereals', 'fao_fpi_dairy', 'fao_fpi_oils', 'wb_urea', 'wb_dap', 'wb_soymeal', 'wb_fishmeal', 'wb_maize', 'wb_wheat', 'wb_palm', 'wb_crude', 'wb_beef', 'wb_chicken', 'wb_shrimp']
            def pcx(x): return f'<span class="{"up" if x > 0 else "dn" if x < 0 else ""}">{x:+.1f}%</span>' if x is not None else '–'
            for sid in [k for k in ORDER if k in GS] + [k for k in GS if k not in ORDER]:
                g = GS[sid]; c = g.get('chg') or {}; cls = 'up' if (c.get('w4') or 0) > 0 else 'dn' if (c.get('w4') or 0) < 0 else 'flat'
                b += f'<tr><td><b>{E(g["name"])}</b>' + (' <span class="mini">(어제 값)</span>' if g.get('stale') else '') + f'<div class="mini">{E(g.get("src", ""))}</div></td><td class="mini">{E(g.get("country", ""))}</td><td class="num">{g["last"]:,.2f}</td><td class="mini">{E(g.get("unit", ""))} · {E(g.get("date", ""))}</td><td class="num">{pcx(c.get("w1"))}</td><td class="num">{pcx(c.get("w4"))}</td><td class="num">{pcx(c.get("m3"))}</td><td class="num">{pcx(c.get("y1"))}</td><td>{spark([x[1] for x in (g.get("points") or [])[-40:]], w=90, h=26, cls=cls)}</td></tr>'
            b += '</table></div><p class="mini">주간·월별 계열의 「1주·4주·3개월」은 각각 1점·4점·13점(월별은 1·3·6점) 전 대비. 변화가 규칙의 기준(예: 유럽 돼지 4주 ±6%)을 넘으면 「원산지 시세」 요인이 켜져 해당 국내 품목 점수에 들어갑니다.</p>'
            gd = GL.get('gdacs') or []
            if gd: b += '<h3>세계 재난 경보(주황·빨강, 14일 안)</h3><ul class="mini">' + ''.join(f'<li><b>{E(x["type"])}</b> {E(x["country"])} — {E(x["title"])} <span class="mini">({E(x["date"])}' + (', 원산지 ' + E('·'.join(x['ko'])) if x.get('ko') else '') + ')</span></li>' for x in gd[:12]) + '</ul>'
            wx = GL.get('weather') or []
            if wx: b += '<h3>원산지 주산지 날씨(30일 평년 대비)</h3><div class="tscroll"><table class="t"><tr><th>나라</th><th>주산지(품목)</th><th class="num">기온 차</th><th class="num">강수 비율</th><th>판정</th></tr>' + ''.join(f'<tr><td>{E(w["ko"])}</td><td class="mini">{E(w["name"])}</td><td class="num">{(w["t_anom"] if w.get("t_anom") is not None else 0):+.1f}℃</td><td class="num">{(f"{int(w["p_ratio"] * 100)}%" if w.get("p_ratio") is not None else "–")}</td><td>{wlv(w.get("level") or 0)} <span class="mini">{E(w.get("why", ""))}</span></td></tr>' for w in sorted(wx, key=lambda w: -(w.get('level') or 0))) + '</table></div>'
        srcs = GAPI.get('sources') or []
        if srcs:
            RS = GL.get('reg_status') or {}
            b += '<h3 id="apis">세계 연동창구 대장</h3><p class="mini">어디에 무엇이 열려 있고 우리가 무엇을 받는지. 「열쇠 대기」는 무료 등록 열쇠만 있으면 바로 붙는 창구(깃허브 비밀 저장소에만 둠), 「계획」은 공개 창구가 없어 날씨·뉴스·국제기구 값으로 대신하는 곳.</p><div class="tscroll"><table class="t"><tr><th>나라·기관</th><th>내용</th><th>열쇠</th><th>주기</th><th>닿는 곳</th><th>상태</th></tr>'
            for x in srcs:
                st = x.get('상태', ''); live = RS.get(x['id'])
                cls = 'ok' if st.startswith('연동') and (live is None or '정상' in str(live)) else 'bad' if ('불통' in st or (live and '실패' in str(live))) else 'wait'
                b += f'<tr><td><b>{E(x["나라"])}</b><div class="mini">{E(x["기관"])}</div></td><td class="mini">{E(x["내용"])}</td><td class="mini">{E(x["열쇠"])}</td><td class="mini">{E(x["주기"])}</td><td class="mini">{E(x["닿는 곳"])}</td><td class="{cls}">{E(st)}' + (f'<div class="mini">오늘 {E(str(live))}</div>' if live else '') + '</td></tr>'
            b += '</table></div>'
        b += '<h2>감시하는 요인 전부</h2><p class="mini">조용한 요인도 매일 잽니다. 단계가 오르면 그날 예보 점수에 들어가고, 이 화면과 첫 화면에 올라옵니다.</p>'
        for c in ('기후·해양', '질병·방역', '지정학·에너지', '정책', '세계 상품', '사고·재해', '원가·경기', '국내 날씨', '국내 수급', '수요·달력', '확인 메모'):
            es = [e for e in WEV if e['cat'] == c]
            if not es: continue
            b += f'<h3>{E(c)}</h3><table class="t wtab"><tr><th>요인</th><th>오늘</th><th>재는 법 · 시차</th><th>영향 품목</th></tr>'
            for e in es:
                b += f'<tr><td><b>{E(e["name"])}</b><div class="mini">{E(e.get("why", "")[:90])}</div></td><td>{wlv(e["level"])}<div class="mini">{E(e.get("text", "")[:80])}</div></td><td class="mini">{E(e.get("src", ""))}<br>시차 {E(e.get("lag", ""))}</td><td class="mini">{aff_links(e.get("affects") or e.get("affects_all") or [])}</td></tr>'
            b += '</table>'
        caps = WORLD.get('caps') or {}
        b += '<h2>점수에 넣는 법</h2><ul><li>요인마다 「주의」면 정해진 무게를, 「경보」면 두 배를 영향 품목 점수에 더합니다. 품목 하나에 더하는 합은 갈래별 상한' + E(f'(수산 ±{caps.get("수산", 1)}, 농산 ±{caps.get("농산", 0.5)}, 축산 ±{caps.get("축산", 0.6)})') + '을 넘지 않습니다. 상한이 신호 문턱(1)의 절반 아래라 세계 요인만으로는 방향이 뒤집히지 않고, 국내 자료와 같은 쪽일 때 세기가 커집니다. 요인별 적중이 20건 넘게 쌓이면 상한을 넓힙니다.</li>'
        b += '<li>뉴스 흐름은 「그 이야기가 평소보다 많이 나온다」는 뜻이지 사실 확인이 아닙니다. 그래서 뉴스만으로는 「주의」까지만 내고, 「경보」는 측정값(엘니뇨 지수·위성 수온·상품값·지진·태풍 경보·달력)이 있을 때만 냅니다. 세계 뉴스 자료(GDELT)가 막히는 날은 구글 뉴스 2주 비교(기사 6건 이상일 때만)로 대신합니다. 기사 제목을 같이 보여 드리니 사람이 확인하세요.</li>'
        b += '<li>엘니뇨 지수는 ±0.5 넘으면 해당 국면, ±1.0 넘으면 강함. 위성 수온 이상은 7개 해역 평균 평년 대비 +1.0℃(주의)·+1.5℃(경보), −1.0℃는 냉수 주의. 세계 상품값은 3개월 변동 ±8~10% 주의·±15~20% 경보. 지진은 일본·한반도 근해 규모 6.0 주의·7.0 경보.</li>'
        b += '<li>달력 요인(설·추석 45일 전부터, 김장철, 휴가철, 개학)은 해마다 되풀이되는 수요라 자료 없이도 켜집니다. 명절·김장 뒤에는 반대 방향(되돌림)으로 켜집니다.</li>'
        b += '<li>세계 요인을 더한 뒤의 예보도 똑같이 채점합니다. 요인별로 맞힌 비율이 쌓이면 무게를 월요일마다 조정하고 <a href="/track/">적중 기록</a>에 남깁니다.</li></ul>'
        b += f'<p class="mini">자료: {E(WORLD.get("basis", ""))}. 모두 열쇠 없는 공개 자료이며, 품목에 없는 영향(고추냉이·천일염 등)은 수집 품목이 늘면 자동으로 이어집니다.</p>'
        write('/world/', shell('/world/', f'세계 요인 감시 — 기후·질병·지정학·정책이 농축수산물 값에 미치는 영향 ({TODAY}) | 박씨팜', '엘니뇨·수온 이상·조류인플루엔자·후쿠시마·호르무즈·할당관세·명절 수요 등 36개 바깥 요인의 오늘 상태와 영향 품목, 예보 점수 반영 방법.', b, og='/og/world.png'), '0.8')

    # ── 1. 첫 화면 ───────────────────────────────────────────────
    def sig_bg(vals, w=1200, h=320):
        """시그니처 블록 배경: 종합 지수(없으면 한우 경락가) 흐름을 흐린 면·선으로"""
        vs = [v for v in vals if isinstance(v, (int, float))]
        if len(vs) < 4: return ''
        lo, hi = min(vs), max(vs); rng = (hi - lo) or 1
        pts = [(w * i / (len(vs) - 1), h * 0.86 - (h * 0.62) * (v - lo) / rng) for i, v in enumerate(vs)]
        d = 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        return (f'<svg class="sig-bg" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="sigg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
                f'<path d="{d} L{w},{h} L0,{h} Z" fill="url(#sigg)"/><path d="{d}" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="2.5" vector-effect="non-scaling-stroke"/></svg>')
    def savings_calc():
        """「얼마 아꼈나」 계산기 — 매입량 × 국산 값 × 갭 % (브라우저 안에서만 계산, 저장 없음)"""
        opts = ''.join(f'<option value="{x["dev"]}|{x["dom"]}">{E(x["name"])} — 평소 대비 {x["dev"]:+}%</option>' for x in sorted(GOK, key=lambda x: -abs(x['dev'])) if not x.get('stale'))
        return ('<div class="card calc"><h3>이 갭이 우리 회사엔 얼마인가</h3><p class="mini">한 달 매입량을 넣으면 오늘 갭(평소 비율 대비 %)이 국산 값 기준으로 얼마에 해당하는지 셈합니다. 관세·운임이 빠진 비율이라 크기의 감만 잡는 용도.</p>'
                f'<div class="row"><label>짝<select id="cp">{opts}</select></label><label>한 달 매입량(톤)<input id="ct" type="number" min="0" step="0.5" value="10"></label></div>'
                '<p class="big" id="co">–</p><p class="mini" id="cn"></p>'
                '<script>(function(){var s=document.getElementById("cp"),t=document.getElementById("ct"),o=document.getElementById("co"),n=document.getElementById("cn");function f(){if(!s.value)return;var a=s.value.split("|"),dev=parseFloat(a[0]),dom=parseFloat(a[1]),ton=parseFloat(t.value)||0;var won=Math.abs(dev)/100*dom*ton*1000;o.textContent=(won>=1e8?(won/1e8).toFixed(1)+"억 원":Math.round(won/1e4).toLocaleString()+"만 원");n.textContent="국산 "+dom.toLocaleString()+"원/㎏ × "+ton+"톤 × "+Math.abs(dev)+"% — 갭이 평소로 되돌아올 때 "+(dev>0?"수입으로 바꾸면 아낄":"국산을 담으면 아낄")+" 수 있는 크기의 감";}s.addEventListener("change",f);t.addEventListener("input",f);f();})();</script></div>')
    def gap_card(x):
        hi = '고평가' in x['state'] or '높음' in x['state']; lo = '저평가' in x['state'] or '낮음' in x['state']
        cls = 'up' if hi else 'dn' if lo else 'flat'
        act = x['acts'].get('수입·유통', '')
        return (f'<a class="card px gapc {cls}{" stale" if x.get("stale") else ""}" href="/gap/#{E(x["id"])}"><h3>{E(x["name"].split(" ↔ ")[0])} <small>↔ {E(x["name"].split(" ↔ ")[1])}</small></h3>'
                f'<div class="big">{x["dev"]:+}%</div><p class="mini">평소 비율 대비 · 1년 백분위 {x["pct"]} · 기준 {x["n_base"]}일' + (f' · <b>{E(x["date"][5:])} 자료</b>' if x.get('stale') else '') + f'</p>{gauge(x["pct"], x["state"])}<p class="gs">{gstate(x["state"])}</p><p class="mini act">{E(act[:60])}</p></a>')
    def home():
        sc = GAP.get('score') or {}
        hot = [x for x in GHOT]; calm = [x for x in GOK if x not in GHOT and x.get('kind') != 'fx']; fxp = [x for x in GOK if x.get('kind') == 'fx']
        bgv = [v for _, v in (next((x['series'] for x in GOK if x['id'] == 'pig_ushog'), []))[-60:]] or [x[1] for x in ((PX.get('total') or {}).get('daily') or [])[-60:]]
        b = '<section class="sig" aria-label="박씨팜 갭 신호">' + sig_bg(bgv)
        b += f'<div class="sig-in"><p class="sig-strap">{E(BR.PRODUCT)} · {E(BR.SYSTEM)}</p><h1 class="sig-h">{E(BR.PITCH_LINES[0])}<br>{E(BR.PITCH_LINES[1])}</h1>'
        b += f'<p class="sig-sub">{E(BR.PITCH_DESC)}</p><p class="sig-today"><b>{E(GAP.get("date", TODAY))} 아침</b> — 짝 {len(GOK)}개 가운데 갭 {len(hot)}개' + (f' · 되돌림 채점 {sc["closed"]}/{sc["n"]}건({sc["rate"]}%)' if sc.get('n') else ' · 되돌림 채점은 11월 말부터') + '</p>'
        b += '<div class="sig-cta"><a class="btn light" href="#board">오늘의 갭 판</a><a class="btn ghost" href="/pro/#gap">우리 품목으로 받기</a><a class="btn ghost" href="/gap/#how">어떻게 재나</a></div></div>'
        b += '<div class="sig-stats">'
        b += f'<a href="#board"><b>{len(hot)}</b><span>오늘 켜진 갭 · 짝 {len(GOK)}개</span></a>'
        b += (f'<a href="/track/"><b>{sc["rate"]}%</b><span>갭 되돌림 채점 {sc["closed"]}/{sc["n"]}</span></a>' if sc.get('n') else f'<a href="/track/"><b>{sc.get("n_days", 0)}일</b><span>되돌림 기록 중 · 첫 채점 11월 말</span></a>')
        b += f'<a href="/source/"><b>{SRC.get("n_signal", 0)}</b><span>국내 부족 신호 품목 · 수입 원산지</span></a>'
        b += f'<a href="/world/#global"><b>{(GL.get("n_series") or 0)}</b><span>원산지 현지 시세 계열 · 매일</span></a>'
        b += '</div></section>'
        b += '<div class="sig-promise">' + ''.join(f'<span>{E(x)}</span>' for x in BR.PROMISE) + f'<span>{E(BR.SLOGAN)}</span></div>'
        # 갭 판
        b += f'<h2 id="board">오늘의 갭 판 <small class="mini">{E(GAP.get("date", TODAY))} · 국산 값 ÷ 현지 값(환율 환산)이 평소 띠(최근 1년 백분위 15~85)를 벗어나면 갭</small></h2>'
        if not GOK: b += '<p class="note">아직 계산할 자료가 모이지 않았습니다. 매일 아침 자동으로 다시 계산합니다.</p>'
        else:
            if hot: b += '<h3>켜진 갭</h3><div class="grid3">' + ''.join(gap_card(x) for x in sorted(hot, key=lambda x: -abs(x['z']))) + '</div>'
            else: b += '<p class="note">오늘은 평소 띠를 벗어난 짝이 없습니다 — 그 자체가 신호입니다(통상 비율대로 사면 됨).</p>'
            if calm: b += f'<h3>평소 범위 안 {len(calm)}짝</h3><div class="grid3">' + ''.join(gap_card(x) for x in sorted(calm, key=lambda x: -abs(x['z']))) + '</div>'
            if fxp: b += f'<details class="flat"><summary>환율만 맞댄 참고 짝 {len(fxp)}개(바나나·오렌지 — 현지 창구 없음)</summary><div class="grid3" style="margin-top:10px">' + ''.join(gap_card(x) for x in fxp) + '</div></details>'
            b += '<p class="mini">게이지: 왼쪽 파랑 = 국산이 상대적으로 쌈(백분위 15 아래), 오른쪽 벽돌 = 국산이 상대적으로 비쌈(85 위). 자세한 그래프·4주 변화 분해·참고 행동은 <a href="/gap/">갭 상세</a>에.</p>'
            b += '<div class="grid2">' + savings_calc() + '<div class="card"><h3>준비 중인 짝</h3><p><b>계란 ↔ 미국·스페인(조류인플루엔자 때 급증)</b> · 닭고기 ↔ 브라질 육계 · 새우 ↔ 베트남·에콰도르 · 오징어 ↔ 페루·칠레 · 고등어 ↔ 노르웨이 · 게 ↔ 러시아 · 마늘·고추·김치 ↔ 중국. 국산 일별 시세(농산물유통정보 열쇠)와 원산지별 수입 단가(관세청 열쇠)가 붙는 대로 엽니다. <a href="/gap/#candidates">짝 후보 대장 26개 →</a> 한우·돼지 기준 기간은 경락가 1년 되채움이 끝나면 365일이 됩니다.</p><p class="mini" style="margin-top:8px">짝을 고를 기준: 수입 금액이 크고, 국산과 수입이 같은 자리를 두고 겨루며, 현지 값을 날마다 받을 수 있는 것.</p></div></div>'
        # 되돌림 채점
        b += '<h2>갭은 정말 되돌아오나</h2>'
        if sc.get('n'): b += f'<p>갭으로 판정한 날의 4주 뒤 |z|가 절반 아래로 줄어든 비율 <b>{sc["closed"]}/{sc["n"]}건({sc["rate"]}%)</b>. 되돌아오지 않은 갭도 그대로 둡니다. <a href="/gap/#score">채점 표 →</a></p>'
        else: b += f'<p class="mini">갭 판정을 날마다 기록해 두고(기록 {sc.get("n_days", 0)}일째) 4주 뒤 되돌아왔는지 채점합니다. 첫 채점은 11월 말. 그때까지는 시범(무료)입니다.</p>'
        # 국내 부족 → 수입 원산지
        hot_src = [r for r in (SRC.get('items') or []) if r['signals']][:6]
        if hot_src:
            b += '<h2>국내가 부족한 품목 — 어디서 들여오나</h2><div class="tscroll"><table class="t"><tr><th>수입 품목</th><th>국내 신호</th><th>원산지 후보 · 오늘 상태</th><th>수요 예약</th></tr>'
            for r in hot_src: b += f'<tr><td><a href="/source/#{E(r["import"])}"><b>{E(r["import"])}</b></a></td><td class="mini">{" · ".join(E(x["item"]) + " " + E(x["kind"]) for x in r["signals"][:2])}</td><td>{" ".join(olv_chip(o) for o in r["origins"][:4])}</td><td class="mini">{"열림" if r.get("open") else "–"}</td></tr>'
            b += '</table></div><p class="mini"><a href="/source/">원산지 거래 정보 전체 · 수입 공동 수요 예약 →</a></p>'
        # 왜 그런가 — 둘째 층(간단히)
        n_alarm = sum(1 for a in AL if a['level'] == '경보'); n_warn = sum(1 for a in AL if a['level'] == '주의'); tm0 = ((PX.get('total') or {}).get('metrics') or {})
        b += '<h2>왜 그런가 — 갭 신호를 만드는 엔진</h2><div class="grid4">'
        b += f'<a class="card px flat" href="/f/"><h3>품목별 가격 예보</h3><div class="big">{len(items)}</div><p class="mini">오름 {counts["오름"]} · 내림 {counts["내림"]} · 보합 {counts["보합"]} — 근거·적중 기록</p></a>'
        b += f'<a class="card px flat" href="/world/"><h3>세계·원산지 요인</h3><div class="big">{len(WACT)}</div><p class="mini">오늘 켜진 요인(경보 {sum(1 for e in WACT if e.get("level") == 2)}) · 원산지 57개 나라</p></a>'
        b += (f'<a class="card px flat" href="/index/"><h3>물가 지수</h3><div class="big">{tm0["last"]:.1f}</div><p class="mini">종합 · {E(tm0["regime"])} · 5일선·20일선</p></a>' if tm0.get('n') else '<a class="card px flat" href="/index/"><h3>물가 지수</h3><div class="big">–</div><p class="mini">계산 중</p></a>')
        b += f'<a class="card px flat" href="/alerts/"><h3>오늘의 경보</h3><div class="big">{n_alarm + n_warn}</div><p class="mini">경보 {n_alarm} · 주의 {n_warn} — 해외 시세 급변·폐사 위험·세계 요인</p></a>'
        b += '</div>'
        if AL: b += '<ul class="alerts compact">' + ''.join(alert_li(a) for a in AL[:3]) + '</ul>'
        b += '<h2>갭 신호 받아 보기</h2><div class="grid2"><div class="card on"><h3>업체 구독 — 우리 품목 갭 경보</h3><p>급식·식자재 유통, 수입육·수산 냉동 유통, 외식 체인 구매 담당께. 사는 품목을 등록하면 갭이 벌어지는 날 아침에 알려 드리고 원산지 현지 시세·환율·되돌림 채점을 함께 드립니다. 시범 기간 무료, 유료 전환 전 미리 안내.</p><p style="margin-top:10px;"><a class="btn prime" href="/pro/#gap">구독 신청</a></p></div><div class="card"><h3>농가·어가</h3><p>갭은 양쪽에 신호입니다 — 국산이 상대적으로 비쌀 때는 출하를 서두르고, 쌀 때는 늦출 여지. 품목별 예보와 시세 한 장은 무료입니다.</p><p style="margin-top:10px;"><a class="btn" href="/sheet/">시세 한 장</a> <a class="btn" href="/f/">품목별 예보</a></p></div></div>'
        b += f'<p class="mini" style="margin-top:22px;">갭 신호는 공개 자료로 만든 참고 정보이며 거래·투자 권유가 아닙니다. 박씨팜은 사고팔지 않고 이 숫자에 이해관계가 없습니다. 자료: 원산지 현지 창구(노르웨이 통계청·유럽연합 집행위·미국 농무부·브라질 세페아·식량농업기구·세계은행), 유럽중앙은행 기준환율, 축산물품질평가원·수협 위판·공영도매시장.</p>'
        ld = {'@context': 'https://schema.org', '@type': 'WebSite', 'name': BR.NAME, 'alternateName': [BR.PRODUCT, BR.TAGLINE], 'slogan': BR.PITCH, 'url': BASE + '/', 'description': BR.PITCH_DESC}
        write('/', shell('/', f'{BR.PRODUCT} — {BR.PITCH} 오늘 갭 {len(hot)}/{len(GOK)} ({TODAY}) | {BR.SYSTEM}', BR.PITCH + ' ' + BR.PITCH_DESC, b, jsonld=ld), '1.0')

    # ── 2. 품목별 ────────────────────────────────────────────────
    def list_page():
        b = '<p class="crumb"><a href="/">박씨팜</a> › 품목별 예보</p><h1 class="title">품목별 가격 예보</h1>'
        b += f'<p class="lead">{len(items)}개 품목의 값 방향을 한 표에. 갈래·방향으로 거르고, 이름으로 찾으세요. 누르면 근거와 값 흐름, 지난 예보 결과가 나옵니다.</p>'
        b += '<div class="filters" id="ff"><div class="chips">' + ''.join(f'<button type="button" class="chip" data-s="{E(s)}">{E(s)}</button>' for s in ('전체', '축산', '수산', '농산')) + '</div>'
        b += '<div class="chips">' + ''.join(f'<button type="button" class="chip" data-d="{d}">{t}</button>' for d, t in (('all', '모든 방향'), ('up', '오름'), ('dn', '내림'), ('flat', '보합'))) + '</div>'
        b += '<input type="search" id="fq" placeholder="품목 이름" aria-label="품목 이름으로 찾기"></div>'
        b += '<table class="t flist" id="ft"><thead><tr><th>품목</th><th class="c-x">갈래</th><th>방향</th><th class="c-x">세기</th><th class="num">현재</th><th class="c-x">무엇을 언제</th><th>근거</th></tr></thead><tbody>'
        for it in items:
            b += (f'<tr data-s="{E(it["sector"])}" data-d="{it["cls"]}" data-n="{E(it["item"])}"><td><a href="{it["url"]}"><b>{E(it["item"])}</b></a><span class="c-m mini"> {E(it["sector"])}</span>' + (f'<div class="mini c-x">{E(", ".join(it["names"][:2]))}</div>' if it['names'] else '') + '</td>'
                  f'<td class="c-x">{E(it["sector"])}</td><td>{badge(it["dir"])}</td><td class="c-x">{dots(it["strength"])}</td><td class="num nw">{E(won(it["price"]))}</td><td class="mini c-x">{E(SECT_H.get(it["sector"], ""))}</td><td class="mini">{E(" · ".join(it["why"][:2])[:90])}</td></tr>')
        b += '</tbody></table><p class="mini" id="fn"></p>'
        b += '''<script>(function(){var S='전체',D='all',Q='';var rows=[].slice.call(document.querySelectorAll('#ft tbody tr'));var fn=document.getElementById('fn');
function ap(){var n=0;rows.forEach(function(r){var ok=(S==='전체'||r.dataset.s===S)&&(D==='all'||r.dataset.d===D)&&(!Q||r.dataset.n.indexOf(Q)>=0);r.style.display=ok?'':'none';if(ok)n++;});fn.textContent=n+'개 품목';
document.querySelectorAll('#ff .chip').forEach(function(c){c.classList.toggle('on',(c.dataset.s&&c.dataset.s===S)||(c.dataset.d&&c.dataset.d===D));});}
document.querySelectorAll('#ff .chip').forEach(function(c){c.addEventListener('click',function(){if(c.dataset.s)S=c.dataset.s;else D=c.dataset.d;ap();});});
document.getElementById('fq').addEventListener('input',function(e){Q=e.target.value.trim();ap();});
var h=decodeURIComponent(location.hash.slice(1));if(['축산','수산','농산'].indexOf(h)>=0)S=h;ap();})();</script>'''
        write('/f/', shell('/f/', f'품목별 가격 예보 — {len(items)}개 품목 값 방향 | 박씨팜', '축산·수산·농산 품목마다 앞으로 값이 오를지 내릴지, 신호 세기와 근거, 지난 예보의 적중을 한 표에.', b, og='/og/f.png'), '0.9')

    # ── 3. 품목 예보 화면 ────────────────────────────────────────
    def item_page(it):
        s = it['sector']; w = it['w']
        crumb = f'<p class="crumb"><a href="/">박씨팜</a> › <a href="/f/">품목별</a> › <a href="/f/#{E(s)}">{E(s)}</a> › {E(it["item"])}</p>'
        b = crumb + f'<div class="ihead {it["cls"]}"><h1 class="title">{E(it["item"])} 가격 예보 {badge(it["dir"], True)}</h1>'
        if it.get('obs_only'):
            b += f'<p class="lead">관측 기관의 전망입니다. {E(it["horizon"])}</p></div>'
        else:
            verb = {'오름': '오를 쪽으로', '내림': '내릴 쪽으로', '보합': '크게 움직이지 않을 것으로'}[w]
            b += f'<p class="lead">{E(it["horizon"])}이 <b>{verb}</b> 봅니다. 신호 세기 {dots(it["strength"])} · {E(conf_text(s))} · {E(TODAY)} 아침 기준</p>'
            if it['price']: b += f'<p class="iprice">{E(won(it["price"]))}<small> {E(it["unit"])} · 지금</small></p>'
            b += '</div>'
            acts = {'오름': ('필요 물량을 앞당겨 확보하거나 재고를 늘리는 쪽으로 검토', '출하를 늦출 수 있으면 늦추는 쪽으로 검토'), '내림': ('구매를 미루거나 소량으로 나눠 사는 쪽으로 검토', '출하를 서두르는 쪽으로 검토'), '보합': ('평소대로', '평소대로')}[w]
            if s == '축산' and it['item'] == '배합사료 원가': acts = ('—', '사료 선매 ' + ('검토' if w == '오름' else '보류, 평소대로' if w == '보합' else '미루기'))
            b += f'<div class="grid2 acts"><div class="card"><h3>유통·가공·급식</h3><p>{E(acts[0])}</p></div><div class="card"><h3>농가·어가</h3><p>{E(acts[1])}</p></div></div>'
        if it['series'] and len(it['series']) >= 2:
            vs = [v for _, v in it['series']]; c1 = round((vs[-1] / vs[0] - 1) * 100, 1) if vs[0] else None
            tm = tmetrics(it['series']); col = "var(--brick)" if w == "오름" else "#2f5f8a" if w == "내림" else "var(--moss)"
            b += f'<h2>값 흐름과 경향 {regime_badge(tm) if tm and tm.get("n", 0) >= 3 else ""}</h2>'
            b += stock_svg(it['series'], vols=it.get('vols') or None, color=col, label=it['item']) if len(vs) >= 5 else chart([(d, v) for d, v in it['series']], color=col)
            b += f'<p class="mini">{E(it["series"][0][0])} ~ {E(it["series"][-1][0])} · {len(vs)}개 점 · 기간 변동 {c1:+}% · ' + E({'수산': '수협 산지 위판 ㎏당 값(금액÷중량, 가장 많이 팔린 상태 기준)', '농산': '공영도매시장 26곳 정산 ㎏당 값(㎏ 단위 거래만)', '축산': '축산물품질평가원 등급별 경락가(등외 제외 평균)' if it['item'] != '배합사료 원가' else '사료 원가 지수(시카고 곡물 선물 × 원/달러, 원/㎏)'}[s]) + '</p>'
            if tm and tm.get('n', 0) >= 3:
                b += metrics_html(tm, unit=it['unit']) + (f'<p class="note"><b>경향 읽기</b> — {E(regime_text(tm))}. 하루 값이 아니라 {tm["long"]}{tm["unit_word"]}선의 기울기와 값이 그 선 위·아래 어디에 있는지로 판단합니다. <a href="/index/#how">판정 기준 →</a></p>')
        b += '<h2>왜 그렇게 보나</h2>'
        if it['why']: b += '<ul class="why">' + ''.join(f'<li>{E(x)}</li>' for x in it['why']) + '</ul>'
        else: b += '<p class="mini">근거 없음(뚜렷한 신호가 없어 보합).</p>'
        if it.get('feed_note'): b += f'<p class="note">{E(it["feed_note"])}</p>'
        if it.get('backtest'):
            bt = it['backtest']; b += f'<p class="mini">검증: 「{E(bt["rule"])}」 규칙은 지난 3년 {bt["n"]}번 중 {bt["hit"]}번({bt["rate"]}%) 맞아 기준선({bt["base_rate"]}%)과 차이가 없습니다. 그래서 원가의 앞날을 맞히려 하지 않고, 이미 오른 원가가 몇 달 뒤 사료값에 얼마나 옮겨 갈지(전가)만 계산합니다.</p>'
        for n in it['notes']:
            b += f'<div class="note"><b>{E(n["item"])} {E(n.get("dir", ""))}</b> — {E(n["text"])} <span class="mini">({E(n["src"])}, {E(n.get("date", ""))}{(" · " + E(n["until"]) + "까지 유효") if n.get("until") else ""})</span></div>'
        if it.get('risk'):
            r = it['risk']; b += f'<div class="note"><b>폐사 위험 {E(r["lv"])}</b> — 7일 수온 예보가 {E(it["item"])} 한계 수온에 닿는 해역이 있습니다(양식 면허 {r.get("ha") or 0}㏊, {E(", ".join(u.split("|")[-1] for u in r.get("units", [])[:4]))}). 공급이 줄 수 있습니다. <a href="/risk/">위험 예보 →</a></div>'
        if it.get('opp'): b += f'<p class="mini">수급 기회에서 「{E(it["opp"])}」 품목으로 잡혀 있습니다. <a href="/opps/">수급 기회 →</a></p>'
        ex = exposure_of(s, it['item'])
        if ex:
            b += '<h2>수입·원산지 노출</h2><p class="mini">이 품목 값에 닿는 수입 품목과 그 원산지. 원산지에서 공급 충격·정치·무역·통화·엘니뇨 사건이 나면 비중 × 전가 무게로 이 품목 점수에 들어갑니다(갈래 상한 안). 비중은 근사치.</p><table class="t"><tr><th>수입 품목</th><th>관계</th><th>원산지(비중 · 오늘)</th><th>집중도</th></tr>'
            for x in ex[:6]:
                org = ' · '.join(f'<span class="org {("hi" if OLV.get(re.sub(r"\(.*?\)", "", c).strip()) == 2 else "mid" if OLV.get(re.sub(r"\(.*?\)", "", c).strip()) == 1 else "")}">{E(c)} {int(sh * 100)}%</span>' for c, sh in x.get('origins', []))
                b += f'<tr><td><b>{E(x["import"])}</b>' + (f'<div class="mini">{E(x.get("note", ""))}</div>' if x.get('note') else '') + f'</td><td class="mini">{E(x["role"])}' + (' · 수출' if x.get('export') else '') + f'<br>전가 {x.get("pt")} · 시차 {E(x.get("lag", ""))}</td><td>{org}</td><td class="num">{x.get("hhi")}</td></tr>'
            b += '</table><p class="mini">집중도는 원산지 비중 제곱의 합(1에 가까울수록 한 나라 의존). <a href="/world/#imports">수입 품목 원산지 지도 →</a></p>'
        srcs = SRC_BY.get((s, it['item'])) or []
        if srcs:
            b += '<h2>국내가 부족하면 — 수입으로 메우기</h2><p class="mini">이 품목에 부족 신호가 켜져 있어 수입 원산지 후보와 오늘 원산지 상태, 현지 시세, 수입 단가를 함께 둡니다. 수요가 모이면 등록 수입·유통업체가 견적을 냅니다(박씨팜은 거래에 끼지 않음).</p>' + ''.join(src_block(r, compact=True) for r in srcs[:2]) + '<p class="mini"><a href="/source/">원산지 거래 정보 전체 →</a></p>'
        if it['where']:
            b += f'<h2>어디서 싸게 거래되나</h2><table class="t"><tr><th>{"조합" if s == "수산" else "도매시장"}</th><th class="num">㎏당</th><th class="num">평균보다</th></tr>' + ''.join(f'<tr><td>{E(str(c[0]).replace("수산업협동조합", "수협"))}</td><td class="num">{c[1]:,}원</td><td class="num ok">−{c[2]}%</td></tr>' for c in it['where'][:5]) + f'</table><p class="mini">{E(it["where_src"])} · 규격·선도가 섞인 평균이니 매입 전 규격을 맞춰 보세요.</p>'
        subs = [(x, slug('수산', x)) for x in it['subs']]
        if subs: b += '<h2>대체 품목</h2><p>' + ' · '.join((f'<a href="{u}">{E(x)}</a>' if u in by_url else E(x)) for x, u in subs) + '</p>'
        # 지난 예보와 결과
        b += '<h2>지난 예보와 결과</h2>'
        if it['hist']:
            hit = sum(1 for h in it['hist'] if h[3]); b += f'<p class="mini">{len(it["hist"])}건 중 {hit}건 적중</p><table class="t"><tr><th>예보 시점</th><th>예보</th><th class="num">실제 변동</th><th>결과</th></tr>' + ''.join(f'<tr><td>{E(h[0])}</td><td>{badge(h[1])}</td><td class="num">{h[2]:+}%</td><td class="{"ok" if h[3] else "bad"}">{"맞음" if h[3] else "틀림"}</td></tr>' for h in it['hist']) + '</table>'
        elif it.get('dec_hist'):
            dh = [x for x in it['dec_hist'] if x[1]]
            b += f'<p class="mini">날마다 판단을 기록해 두고 10거래일 뒤 실제 경락가로 채점합니다(사료는 60거래일). 지금 {len(dh)}일째 기록 중, 첫 채점 전.</p><details><summary>기록 {len(dh)}건 보기</summary><table class="t"><tr><th>날짜</th><th>판단</th><th class="num">기준값</th></tr>' + ''.join(f'<tr><td>{E(d)}</td><td>{badge(dec_dir(a))} <span class="mini">{E(a)}</span></td><td class="num">{E(won(bse))}</td></tr>' for d, a, bse in reversed(dh)) + '</table></details>'
        else:
            b += '<p class="mini">' + E({'수산': '달마다 예보를 남기고 다음 달 위판 값으로 채점합니다. 이 품목은 아직 채점된 예보가 없습니다.', '농산': '월요일마다 예보를 남기고 2주 뒤 도매시장 값으로 채점합니다. 첫 채점은 11월 초입니다.', '축산': '첫 채점 전입니다.'}[s]) + '</p>'
        wl = [w for w in it['why'] if w.startswith('세계 요인')]
        if wl: b += '<p class="mini">세계 요인이 이 품목 점수에 들어가 있습니다(갈래 상한 안에서). <a href="/world/">세계 요인 감시 →</a></p>'
        b += '<h2>같이 보기</h2><p class="links">' + ' · '.join(f'<a href="{u}">{t}</a>' for u, t in (('/f/#' + s, f'{s} 품목 전체'), ('/world/', '세계 요인'), ('/track/', '적중 기록'), ('/alerts/', '오늘의 경보'), ('/price/', '오늘 시세'), ('/opps/', '수급 기회'), ('/map/', '지도'))) + '</p>'
        b += f'<p class="mini"><b>{E(BR.TAGLINE)}</b> — {E(BR.SLOGAN)} 예보는 공개 자료로 만든 참고 정보이며 거래를 권하는 것이 아닙니다. 박씨팜은 물건을 사고팔지 않으며, 이 숫자에 이해관계가 없습니다.</p>'
        desc = f'{it["item"]} {it["horizon"]} {w} 예보. ' + ' · '.join(it['why'][:2])[:120]
        ld = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': f'{it["item"]} 가격 예보', 'url': BASE + it['url'], 'dateModified': TODAY, 'description': desc, 'isPartOf': {'@type': 'WebSite', 'name': '박씨팜', 'url': BASE + '/'}}
        write(it['url'], shell(it['url'], f'{it["item"]} 가격 예보 — {w} ({s}, {TODAY}) | 박씨팜', desc, b, jsonld=ld, og='/og' + it['url'].rstrip('/') + '.png'), '0.7')

    # ── 4. 경보 ──────────────────────────────────────────────────
    def alerts_page():
        hi = [a for a in AL if a['level'] == '경보']; mid = [a for a in AL if a['level'] == '주의']
        b = f'<p class="crumb"><a href="/">박씨팜</a> › 경보</p><h1 class="title">오늘의 경보</h1><p class="lead">해외 선물·환율 급변, 국내 경락가 급등락, 양식 고수온·가축 더위 위험을 한곳에 모았습니다. 경보는 「미리 할 일」과 함께 냅니다. {E(TODAY)} 아침 기준.</p>'
        b += f'<div class="statusbar"><span class="{"off" if hi else "on"}"><i></i>경보 {len(hi)}</span><span class="{"soon" if mid else "on"}"><i></i>주의 {len(mid)}</span></div>'
        if hi: b += '<h2>경보</h2><ul class="alerts">' + ''.join(alert_li(a) + '' for a in hi) + '</ul>'
        if mid: b += '<h2>주의</h2><ul class="alerts">' + ''.join(alert_li(a) for a in mid) + '</ul>'
        if not AL: b += '<p class="note">오늘은 기준을 넘은 급변이 없습니다.</p>'
        pa = (FC.get('params') or {}).get('alert') or {}
        b += '<h2>경보 기준</h2><ul class="mini">'
        b += f'<li>해외 시세: 하루 변동이 평소(1년 표준편차)의 {pa.get("day_z_warn", 2.5)}배면 주의, {pa.get("day_z_alarm", 3.5)}배면 경보. 1개월 변동 ±{pa.get("m20_warn", 8)}% 주의, ±{pa.get("m20_alarm", 15)}% 경보.</li>'
        b += f'<li>환율: 5거래일 ±{pa.get("fx5_warn", 2)}% 주의, ±{pa.get("fx5_alarm", 3.5)}% 경보.</li>'
        b += f'<li>경락가: 직전 5거래일 중위값 대비 ±{pa.get("price_dev_warn", 7)}% 주의, ±{pa.get("price_dev_alarm", 12)}% 경보(두수 {pa.get("price_min_heads", 20)}두 넘는 날만).</li>'
        b += '<li>양식 폐사: 7일 바다 수온 예보가 품종별 한계 수온에 2일 넘게 닿으면 위험, 1일이면 주의. 가축 더위: 온습도지수 2일 넘게 72 이상 주의, 79 이상 경고, 한낮 89 이상 위험.</li></ul>'
        b += '<p class="mini">기준은 채점 결과에 따라 월요일마다 정해진 범위 안에서 스스로 조정하며, 바뀐 내용은 <a href="/track/">적중 기록</a>에 남깁니다. 해역·시군별 위험 지도는 <a href="/risk/">위험 예보</a>에.</p>'
        write('/alerts/', shell('/alerts/', f'오늘의 경보 {TODAY} — 급변·폐사·더위 위험과 미리 할 일 | 박씨팜', '해외 선물·환율 급변, 경락가 급등락, 양식 고수온·가축 더위 위험을 경보·주의로 나눠 미리 할 일과 함께 알립니다.', b, og='/og/alerts.png'), '0.8')

    # ── 5. 적중 기록 ─────────────────────────────────────────────
    def track_page():
        b = '<p class="crumb"><a href="/">박씨팜</a> › 적중 기록</p><h1 class="title">적중 기록 — 숨기지 않고 공개</h1><p class="lead">모든 예보는 그날 기록해 두고 기한이 오면 실제 값으로 자동 채점합니다. 틀린 것도 그대로 둡니다. 적중 기록이 곧 이 예보의 신용입니다.</p>'
        n1, h1, r1 = rate_of('수산'); n2, h2, r2 = rate_of('농산')
        b += '<h2>갈래별 성적</h2><table class="t"><tr><th>갈래</th><th>예보 단위 · 채점 시점</th><th class="num">채점</th><th class="num">적중</th><th class="num">적중률</th><th>기준선</th></tr>'
        b += f'<tr><td>수산</td><td class="mini">달마다 · 다음 달 위판 값(±3%)</td><td class="num">{n1}</td><td class="num">{h1}</td><td class="num {"bad" if n1 and r1 < 50 else "ok" if n1 else ""}">{f"{r1}%" if n1 else "–"}</td><td class="mini">보합 예측 적중률과 비교(산출 중)</td></tr>'
        b += f'<tr><td>농산</td><td class="mini">월요일마다 · 2주 뒤 도매시장 값(±3%)</td><td class="num">{n2}</td><td class="num">{h2}</td><td class="num">{f"{r2}%" if n2 else "대기"}</td><td class="mini">첫 채점 11월 초</td></tr>'
        for did, nm in (('hanwoo', '축산 · 한우 거세 출하'), ('pig', '축산 · 돼지 탕박 출하')):
            d = dec.get(did) or {}; lt = d.get('live_track') or {}
            b += f'<tr><td>{E(nm)}</td><td class="mini">날마다 · 10거래일 뒤 경락가</td><td class="num">{lt.get("n", 0)}</td><td class="num">{lt.get("hit", "–") if lt else "–"}</td><td class="num">{f"{lt["rate"]}%" if lt.get("n") else f"대기({d.get("ndays") or 0}일째 기록)"}</td><td class="mini">{f"{lt["base_rate"]}%" if lt.get("n") else "–"}</td></tr>'
        ts = TSC['sum_items']
        ts_rate = f'{ts["rate"]}%' if ts['n'] else f'대기({TSC["n_days"]}일째 기록)'; ts_note = f'무조건 오른다 {ts["base_up"]}%' if ts['n'] else '첫 채점 11월 11일쯤 · '
        b += f'<tr><td>경향 판정(품목)</td><td class="mini">날마다 · 14일 뒤 값(상승 +2%·하락 −2%·횡보 ±3%)</td><td class="num">{ts["n"]}</td><td class="num">{ts["hit"] if ts["n"] else "–"}</td><td class="num">{E(ts_rate)}</td><td class="mini">{E(ts_note)}<a href="/index/#score">물가 지수</a></td></tr>'
        bt = (FC.get('feed') or {}).get('backtest') or {}
        b += f'<tr><td>축산 · 배합사료 원가</td><td class="mini">60거래일 · 과거 3년 되돌려 검증</td><td class="num">{bt.get("n", "–")}</td><td class="num">{bt.get("hit", "–")}</td><td class="num">{f"{bt["rate"]}%" if bt.get("n") else "–"}</td><td class="mini">{f"{bt["base_rate"]}% — 기준선과 같아 방향 예측 대신 전가 계산만" if bt.get("n") else "–"}</td></tr></table>'
        tr = (BUYS.get('score') or {}).get('trial') or {}
        ms = (BUYS.get('score') or {}).get('months') or []
        if n1 and r1 is not None and r1 < 50 and ms:
            m0 = ms[-1]; flat = sum(1 for r in m0['rows'] if r[1] == '보합'); moved = sum(1 for r in m0['rows'] if abs(r[2]) >= 10)
            b += f'<div class="note"><b>수산 {r1}%는 낮습니다.</b> {E(m0["month"][5:].lstrip("0"))}월 예보 {m0["n"]}건을 {E(m0["to"][5:].lstrip("0"))}월 위판 값으로 채점한 첫 결과입니다. {flat}건을 보합으로 냈는데 실제로는 {moved}개 품목이 10% 넘게 움직였습니다 — 보합을 너무 쉽게 낸 것이 가장 큰 원인입니다. 근거별로 따져 보니 「달 후반 값 흐름」은 73% 맞았고 「창고 재고」는 29%에 그쳐, 10월 26일부터 달 후반 흐름의 무게를 두 배로 올렸습니다. 이미 공개한 예보는 고치지 않고, 새 기준은 따로 채점합니다' + (f'(「{E(tr.get("rule", ""))}」 시험 채점 {tr.get("hit", 0)}/{tr.get("n", 0)})' if tr.get('rule') else '') + '.</div>'
        # 수산 월별 상세
        for m in (BUYS.get('score') or {}).get('months', []):
            rows = sorted(m['rows'], key=lambda r: (r[3], -abs(r[2])))
            b += f'<h2>수산 {E(m["month"])} 예보 → {E(m["to"])} 결과 <span class="mini">{m["hit"]}/{m["n"]}</span></h2><table class="t"><tr><th>품목</th><th>예보</th><th class="num">실제 변동</th><th>결과</th></tr>'
            def nm(x): u = slug('수산', x); return f'<a href="{u}">{E(x)}</a>' if u in by_url else E(x)
            b += ''.join(f'<tr><td>{nm(r[0])}</td><td>{badge(r[1])}</td><td class="num">{r[2]:+}%</td><td class="{"ok" if r[3] else "bad"}">{"맞음" if r[3] else "틀림"}</td></tr>' for r in rows) + '</table>'
        cr = (CROPS.get('score') or {}).get('rows') or []
        if cr:
            b += '<h2>농산 채점</h2><table class="t"><tr><th>예보일</th><th>품목</th><th>예보</th><th class="num">실제 변동</th><th>결과</th></tr>' + ''.join(f'<tr><td>{E(r[0])}</td><td>{E(r[1])}</td><td>{badge(r[2])}</td><td class="num">{r[3]:+}%</td><td class="{"ok" if r[4] else "bad"}">{"맞음" if r[4] else "틀림"}</td></tr>' for r in cr) + '</table>'
        else:
            cf = sorted(glob.glob(os.path.join(PRIVATE, 'forecast', 'crop-*.json')))
            if cf: b += '<h2>농산 — 채점 대기 중인 예보</h2><p class="mini">' + ' · '.join(f'{os.path.basename(p)[5:15]} ({len((json.load(open(p, encoding="utf-8")) or {}).get("items", []))}품목)' for p in cf) + ' — 각 예보일로부터 14일 뒤 자동 채점</p>'
        # 축산 판단 일지
        if f2:
            b += '<h2>축산 판단 일지(최근 3주)</h2><table class="t"><tr><th>날짜</th><th>한우 거세</th><th>돼지 탕박</th><th>배합사료</th></tr>'
            for d, v in reversed(f2):
                g = {x['id']: x for x in v.get('items', [])}
                b += f'<tr><td>{E(d)}</td>' + ''.join(f'<td>{badge(dec_dir(g[k]["act"]))} <span class="mini">{E(won(g[k].get("base")))}</span></td>' if k in g else '<td>–</td>' for k in ('hanwoo', 'pig', 'feed')) + '</tr>'
            b += '</table>'
        cal = (FC.get('params') or {}).get('calib') or []
        b += '<h2>자가 조정 기록</h2>' + ('<ul class="mini">' + ''.join(f'<li>{E(c["date"])} — {E(", ".join(c["changes"]))}</li>' for c in cal[-10:]) + '</ul>' if cal else '<p class="mini">채점이 20건 넘게 쌓인 갈래부터 월요일마다 가중치·기준을 정해진 범위 안에서 조정하고 여기에 남깁니다. 아직 자동 조정은 없고, 10월 26일 수산 근거 무게 조정(사람 검토) 1건이 있습니다.</p>')
        b += '<h2>채점 방법</h2><ul><li>방향은 「오름·내림·보합」 셋 중 하나로 적고, 실제 값이 ±3% 넘게 움직인 방향과 같으면 맞음으로 셉니다(보합 예보는 ±5% 안이면 맞음).</li><li>기준선은 「값이 그대로」라고만 찍었을 때의 적중률입니다. 20건 넘게 채점됐는데 기준선보다 못한 갈래는 「참고용」으로 내립니다.</li><li>예보를 낸 뒤에는 고치지 않습니다. 기준을 바꾸면 그 뒤 예보부터 적용하고 따로 채점합니다.</li></ul>'
        write('/track/', shell('/track/', '적중 기록 — 예보가 실제로 맞았나 | 박씨팜', '수산·농산·축산 가격 예보의 채점 결과를 품목별로 공개합니다. 틀린 예보도 그대로. 채점 방법과 자가 조정 기록.', b, og='/og/track.png'), '0.8')

    def method_page():
        mdp = os.path.join(ROOT, 'docs', '예측기법_박씨팜.md')
        if not os.path.exists(mdp): return
        md = open(mdp, encoding='utf-8').read()
        def inline(t):
            t = E(t); t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t); t = re.sub(r'`(.+?)`', r'<code>\1</code>', t); return t
        out = []; lines = md.splitlines(); i = 0; first = True
        while i < len(lines):
            l = lines[i]
            if l.startswith('# '):
                if first: first = False; i += 1; continue   # 제목은 shell 이 그림
                out.append(f'<h2>{inline(l[2:])}</h2>')
            elif l.startswith('## '): out.append(f'<h2>{inline(l[3:])}</h2>')
            elif l.startswith('### '): out.append(f'<h3>{inline(l[4:])}</h3>')
            elif l.startswith('|'):
                rows = []
                while i < len(lines) and lines[i].startswith('|'):
                    if not re.match(r'^\|[\s\-:|]+\|$', lines[i]): rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                    i += 1
                if rows: out.append('<table class="t"><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in rows[0]) + '</tr>' + ''.join('<tr>' + ''.join(f'<td class="mini">{inline(c)}</td>' for c in r) + '</tr>' for r in rows[1:]) + '</table>')
                continue
            elif l.startswith('- '):
                its = []
                while i < len(lines) and lines[i].startswith('- '): its.append(lines[i][2:]); i += 1
                out.append('<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in its) + '</ul>'); continue
            elif l.strip(): out.append(f'<p>{inline(l)}</p>')
            i += 1
        b = '<p class="crumb"><a href="/">박씨팜</a> › 예측 기법</p><h1 class="title">박씨팜 수급·가격 예측 기법</h1><p class="lead">학계·기관이 검증한 이론과 실증을 우리가 가진 공개 자료에 맞게 조립한 틀. 모든 판단은 기록·채점되어 기준이 스스로 고쳐집니다.</p>' + '\n'.join(out)
        b += '<p class="mini">관련 화면: <a href="/world/">세계·원산지 요인</a> · <a href="/track/">적중 기록</a> · <a href="/signal/">거시 근거</a></p>'
        write('/method/', shell('/method/', '박씨팜 예측 기법 — 거미집·전가·아밍턴·엘니뇨·브라이어 점수를 우리 자료에 맞게 | 박씨팜', '국내 미시 신호, 원산지 노출, 세계 요인, 수요 달력을 갈래 상한 안에서 더하고 실제 값으로 채점하는 박씨팜의 예측 틀과 근거 문헌.', b, og='/og/method.png'), '0.7')
    try:
        json.dump({'at': TODAY, 'counts': counts, 'alerts': len(AL), 'items': [{'url': it['url'], 'sector': it['sector'], 'item': it['item'], 'dir': it['dir'], 'w': it['w'], 'price': it['price'], 'unit': it['unit'], 'horizon': it['horizon'], 'why': (it['why'] or [''])[0], 'strength': it['strength'], 'hist': [len(it['hist']), sum(1 for h in it['hist'] if h[3])]} for it in items],
                   'index': {k: [v['metrics']['last'], v['metrics']['regime'], v['metrics'].get('chg_l')] for k, v in idx_list if v.get('metrics') and v['metrics'].get('n')}, 'rate': {s: rate_of(s) for s in ('수산', '농산')}, 'world': {'n': WORLD.get('n_rules') or len(WEV), 'active': len(WACT), 'alarm': sum(1 for e in WACT if e.get('level') == 2)}, 'gap': {'n': len(GOK), 'hot': [[x['name'], x['state'], x['dev']] for x in GHOT[:3]]}, 'source': {'n': len(SRC.get('items') or []), 'hot': [[r['import'], [sg['kind'] for sg in r['signals']][:2], [o['ko'] for o in r['origins'][:3]]] for r in (SRC.get('items') or []) if r['signals']][:4]}},
                  open(os.path.join(ROOT, 'site', 'data', 'cards.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    except Exception as e: print('cards.json 실패', e)
    home(); list_page()
    for it in items: item_page(it)
    alerts_page(); track_page(); world_page(); method_page(); index_page(); gap_page(); source_page()
    return {'items': len(items), 'up': counts['오름'], 'dn': counts['내림'], 'alerts': len(AL), 'pindex': bool(PX.get('sectors'))}
