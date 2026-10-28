# 예측 중심 화면(2026-10-28 전면 개편) — 첫 화면(오늘 예보판)·품목별(/f/)·품목 예보(/f/갈래/품목/)·경보(/alerts/)·적중 기록(/track/)
# build_pages.py 가 import 해서 build(globals()) 로 부른다. 자료는 모두 site/data 와 private 의 생성물만 읽는다(여기서 새 숫자를 만들지 않음).
#
# 품목 하나를 「예보 항목」으로 통일한다:
#   sector(축산·수산·농산) · item · dir(오름/내림/보합) · strength(0~5) · score · price(현재 ㎏당) · unit · horizon(무엇을 언제 맞히나)
#   why[](근거 문장) · act(행동 제안) · series[(날짜, 값)](값 흐름) · where(싸게 거래된 곳) · subs(대체 품목) · note(관측 기관 메모) · hist(지난 예보와 결과)
import os, re, json, glob, datetime, collections, urllib.parse

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
        rk = risk_sp.get(i['item'])
        items.append({'sector': '수산', 'item': i['item'], 'names': i.get('names') or [], 'dir': i['dir'], 'score': i['score'], 'price': i['wonkg'], 'unit': '원/㎏',
                      'horizon': BUYS.get('horizon', '다음 달 수협 산지 위판 ㎏당 값'), 'why': i.get('why') or [], 'act': i.get('act', ''), 'series': series,
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
        x = csp.get(i['item'])
        items.append({'sector': '농산', 'item': i['item'], 'names': [], 'dir': i['dir'], 'score': i['score'], 'price': i['wonkg'], 'unit': '원/㎏',
                      'horizon': CROPS.get('horizon', '앞으로 2주 공영도매시장 ㎏당 값'), 'why': i.get('why') or [], 'act': i.get('act', ''), 'series': series,
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
        CATS = ('기후·해양', '질병·방역', '지정학·에너지', '정책', '세계 상품', '사고·재해', '원가·경기', '수요·달력', '원산지', '국내 날씨', '국내 수급')
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
        write('/world/', shell('/world/', f'세계 요인 감시 — 기후·질병·지정학·정책이 농축수산물 값에 미치는 영향 ({TODAY}) | 박씨팜', '엘니뇨·수온 이상·조류인플루엔자·후쿠시마·호르무즈·할당관세·명절 수요 등 36개 바깥 요인의 오늘 상태와 영향 품목, 예보 점수 반영 방법.', b), '0.8')

    # ── 1. 첫 화면 ───────────────────────────────────────────────
    def home():
        nf = [it for it in items if it['dir'] != '보합' and not it.get('obs_only')]
        b = f'<div class="hero"><p class="crumb">{E(TODAY)} 아침 예보 · 매일 아침 자동 갱신</p><h1 class="title">오늘의 농축수산물 가격 예보</h1>'
        b += f'<p class="lead">{len(items)}개 품목 가운데 <b class="up">오름 {counts["오름"]}</b> · <b class="dn">내림 {counts["내림"]}</b> · 보합 {counts["보합"]}. 품목을 누르면 근거와 값 흐름, 지난 예보의 결과까지 보입니다.</p>'
        b += '<div class="chips">' + ''.join(f'<a class="chip" href="/f/#{E(s)}">{E(s)} <b>{sum(1 for it in nf if it["sector"] == s)}</b></a>' for s in ('축산', '수산', '농산')) + f'<a class="chip" href="/alerts/">경보 <b>{sum(1 for a in AL if a["level"] == "경보")}</b> · 주의 <b>{sum(1 for a in AL if a["level"] == "주의")}</b></a></div></div>'
        if AL:
            b += '<ul class="alerts compact">' + ''.join(alert_li(a) for a in AL[:3]) + '</ul>' + (f'<p class="mini"><a href="/alerts/">경보 {len(AL)}건 모두 보기 →</a></p>' if len(AL) > 3 else '')
        # 주목 예보: 갈래마다 2개씩 먼저, 남는 자리는 세기 순
        pick, seen = [], set()
        for s in ('축산', '수산', '농산'):
            for it in [x for x in nf if x['sector'] == s][:2]: pick.append(it); seen.add(it['url'])
        for it in nf:
            if len(pick) >= 6: break
            if it['url'] not in seen: pick.append(it); seen.add(it['url'])
        pick.sort(key=rank)
        b += '<h2>오늘 주목할 예보</h2><div class="fgrid">' + ''.join(feature_card(it) for it in pick) + '</div>' if pick else '<h2>오늘 주목할 예보</h2><p class="note">오늘은 뚜렷한 방향이 잡힌 품목이 없습니다.</p>'
        b += '<h2>갈래별 예보</h2><div class="cols3">'
        for s in ('축산', '수산', '농산'):
            li = [it for it in items if it['sector'] == s and it['dir'] != '보합']; fl = [it for it in items if it['sector'] == s and it['dir'] == '보합']
            b += f'<section class="col"><h3>{E(s)} <small>{E(SECT_H[s])} · {E(conf_text(s))}</small></h3>'
            b += ''.join(row(it) for it in li[:9]) if li else '<p class="mini">뚜렷한 방향 없음(전 품목 보합)</p>'
            if len(li) > 9: b += f'<a class="more-link" href="/f/#{E(s)}">{E(s)} 예보 {len(li)}개 모두 →</a>'
            if fl: b += f'<details class="flat"><summary>보합 {len(fl)}품목</summary><p class="mini">' + ' · '.join(f'<a href="{x["url"]}">{E(x["item"])}</a>' for x in fl) + '</p></details>'
            b += '</section>'
        b += '</div>'
        # 적중 기록 띠
        n1, h1, r1 = rate_of('수산'); n2, h2, r2 = rate_of('농산')
        b += '<h2>지난 예보는 맞았나</h2><div class="grid3">'
        ms = (BUYS.get('score') or {}).get('months') or []; mtxt = f'{ms[-1]["month"][5:].lstrip("0")}월 예보를 {ms[-1]["to"][5:].lstrip("0")}월 값으로 채점' if ms else ''
        b += f'<div class="card"><h3>수산</h3><div class="big">{r1 if n1 else "–"}<i>%</i></div><p>{h1}/{n1}건 · {E(mtxt)}</p></div>' if n1 else '<div class="card"><h3>수산</h3><div class="big">대기</div><p>첫 채점 전</p></div>'
        b += f'<div class="card"><h3>농산</h3><div class="big">{r2 if n2 else "대기"}{"<i>%</i>" if n2 else ""}</div><p>{f"{h2}/{n2}건" if n2 else "월요일 예보를 2주 뒤 채점 — 11월 초 첫 결과"}</p></div>'
        hd = dec.get('hanwoo') or {}
        b += f'<div class="card"><h3>축산</h3><div class="big">대기</div><p>한우·돼지 판단 {hd.get("ndays") or 0}거래일째 기록 중 — 10거래일 뒤부터 채점</p></div></div>'
        b += '<p class="mini">틀린 예보도 지우지 않고 그대로 둡니다. <a href="/track/">적중 기록 전체와 채점 방법 →</a></p>'
        b += world_home()
        # 원가 압력
        secs = FC.get('sectors') or []
        if secs:
            b += '<h2>원가 압력 — 기름값·환율·원료가</h2><div class="grid3">' + ''.join(f'<div class="card"><h3>{E(x["sector"])} {badge((x.get("cost") or {}).get("dir"))}</h3><div class="big">{(x.get("cost") or {}).get("v", 0):+}<i>%</i></div><p>{E(" · ".join(((x.get("cost") or {}).get("why") or [])[:3]))}</p></div>' for x in secs) + '</div>'
        tl = FC.get('tiles') or []
        if tl:
            b += '<h2>세계 시세 흐름</h2><div class="tiles">' + ''.join(f'<a class="tile" href="/signal/#macro"><span class="mini">{E(t["name"].replace(" 선물", "").replace("(시카고)", ""))}</span><b>{t["last"]:,}</b><span class="{"up" if (t.get("c20") or 0) > 0 else "dn" if (t.get("c20") or 0) < 0 else ""}">{(t.get("c20") or 0):+}%<small> 1개월</small></span></a>' for t in tl[:8]) + '</div><p class="mini"><a href="/signal/#macro">선물·환율 13개 지표와 사료 원가 지수 →</a></p>'
        b += '<h2>예보 받아 보기</h2><div class="grid2"><div class="card"><h3>유통·가공·급식 업체</h3><p>우리 회사가 사는 품목만 골라 매주 예보와 경보를 받는 구독을 준비하고 있습니다.</p><p style="margin-top:10px;"><a class="btn prime" href="/pro/">업체 등록·구독 신청</a></p></div><div class="card"><h3>농가·어가</h3><p>오늘 시세와 예보를 한 장에 담은 「시세 한 장」을 무료로 받아 보세요.</p><p style="margin-top:10px;"><a class="btn" href="/sheet/">시세 한 장 보기</a></p></div></div>'
        b += f'<p class="mini" style="margin-top:22px;">자료: {E(FC.get("basis", ""))}. 예보는 공개 자료로 만든 참고 정보이며 거래를 권하는 것이 아닙니다. 박씨팜은 물건을 사고팔지 않습니다. 시군별 사육·양식·대표 품목은 <a href="/map/">지도</a>에서.</p>'
        ld = {'@context': 'https://schema.org', '@type': 'WebSite', 'name': '박씨팜', 'url': BASE + '/', 'description': '농축수산물 가격 예보 — 품목별 값 방향·근거·적중 기록, 경보'}
        write('/', shell('/', f'박씨팜 — 오늘의 농축수산물 가격 예보 {TODAY} | 오름 {counts["오름"]}·내림 {counts["내림"]}', '한우·돼지 경락가, 수협 위판가, 공영도매시장 값이 앞으로 오를지 내릴지를 품목별로 근거·적중률과 함께 매일 아침 예보합니다. 경보, 원가 압력, 세계 시세까지.', b, jsonld=ld), '1.0')

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
        write('/f/', shell('/f/', f'품목별 가격 예보 — {len(items)}개 품목 값 방향 | 박씨팜', '축산·수산·농산 품목마다 앞으로 값이 오를지 내릴지, 신호 세기와 근거, 지난 예보의 적중을 한 표에.', b), '0.9')

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
            b += f'<h2>값 흐름</h2>{chart([(d, v) for d, v in it["series"]], color="var(--brick)" if w == "오름" else "#2f5f8a" if w == "내림" else "var(--moss)")}'
            b += f'<p class="mini">{E(it["series"][0][0])} ~ {E(it["series"][-1][0])} · {len(vs)}개 점 · 기간 변동 {c1:+}% · ' + E({'수산': '수협 산지 위판 ㎏당 값(금액÷중량, 가장 많이 팔린 상태 기준)', '농산': '공영도매시장 26곳 정산 ㎏당 값(㎏ 단위 거래만)', '축산': '축산물품질평가원 등급별 경락가(등외 제외 평균)' if it['item'] != '배합사료 원가' else '사료 원가 지수(시카고 곡물 선물 × 원/달러, 원/㎏)'}[s]) + '</p>'
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
        b += '<p class="mini">예보는 공개 자료로 만든 참고 정보이며 거래를 권하는 것이 아닙니다. 박씨팜은 물건을 사고팔지 않으며, 이 숫자에 이해관계가 없습니다.</p>'
        desc = f'{it["item"]} {it["horizon"]} {w} 예보. ' + ' · '.join(it['why'][:2])[:120]
        ld = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': f'{it["item"]} 가격 예보', 'url': BASE + it['url'], 'dateModified': TODAY, 'description': desc, 'isPartOf': {'@type': 'WebSite', 'name': '박씨팜', 'url': BASE + '/'}}
        write(it['url'], shell(it['url'], f'{it["item"]} 가격 예보 — {w} ({s}, {TODAY}) | 박씨팜', desc, b, jsonld=ld), '0.7')

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
        write('/alerts/', shell('/alerts/', f'오늘의 경보 {TODAY} — 급변·폐사·더위 위험과 미리 할 일 | 박씨팜', '해외 선물·환율 급변, 경락가 급등락, 양식 고수온·가축 더위 위험을 경보·주의로 나눠 미리 할 일과 함께 알립니다.', b), '0.8')

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
        write('/track/', shell('/track/', '적중 기록 — 예보가 실제로 맞았나 | 박씨팜', '수산·농산·축산 가격 예보의 채점 결과를 품목별로 공개합니다. 틀린 예보도 그대로. 채점 방법과 자가 조정 기록.', b), '0.8')

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
        write('/method/', shell('/method/', '박씨팜 예측 기법 — 거미집·전가·아밍턴·엘니뇨·브라이어 점수를 우리 자료에 맞게 | 박씨팜', '국내 미시 신호, 원산지 노출, 세계 요인, 수요 달력을 갈래 상한 안에서 더하고 실제 값으로 채점하는 박씨팜의 예측 틀과 근거 문헌.', b), '0.7')
    home(); list_page()
    for it in items: item_page(it)
    alerts_page(); track_page(); world_page(); method_page()
    return {'items': len(items), 'up': counts['오름'], 'dn': counts['내림'], 'alerts': len(AL)}
