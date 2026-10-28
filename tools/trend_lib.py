# 경향 분석·주식식 차트 공통 함수(2026-10-28) — 값 흐름을 계량(이동평균·기울기·추세 판정·변동성·교차·위치)하고 SVG 로 그린다.
#   metrics(series)  series = [(날짜, 값), ...] 오름차순. 일별이면 5·20일, 월별이면 1·3개월 창.
#   stock_svg(series, vols=None, ...)  값선 + 5일선 + 20일선(점선) + ±2σ 띠 + 거래량 막대 + 교차 표시.
import math, html, statistics
E = html.escape

def fmt(x):
    """지수(1000 미만)는 소수 1자리, 값(원)은 정수"""
    return f'{x:,.1f}' if abs(x) < 1000 else f'{x:,.0f}'

def _ma(v, n):
    out = []
    for i in range(len(v)):
        w = v[max(0, i - n + 1):i + 1]
        out.append(sum(w) / len(w) if len(w) == n else None)
    return out

def _slope_pct(y):
    """최근 점들의 1차 회귀 기울기를 마지막 값 대비 %/점으로"""
    y = [x for x in y if x is not None]
    n = len(y)
    if n < 3 or not y[-1]: return None
    xs = list(range(n)); mx = sum(xs) / n; my = sum(y) / n
    den = sum((x - mx) ** 2 for x in xs) or 1
    b = sum((x - mx) * (yy - my) for x, yy in zip(xs, y)) / den
    return round(b / y[-1] * 100, 3)

def metrics(series, monthly=False):
    """계량 요약. 반환 키: last, chg5, chg20, ma5, ma20, slope, regime, cross, vol, band_lo, band_hi, pos, streak, n, hi, lo"""
    s = [(d, float(v)) for d, v in series if v is not None and float(v) > 0]
    if len(s) < 3: return {'n': len(s), 'regime': '자료 부족', 'last': s[-1][1] if s else None}
    v = [x[1] for x in s]; ds = [x[0] for x in s]
    short, long_ = (1, 3) if monthly else (5, 20)
    ma_s = _ma(v, short) if short > 1 else v[:]; ma_l = _ma(v, long_)
    last = v[-1]
    def chg(k): return round((last / v[-1 - k] - 1) * 100, 1) if len(v) > k and v[-1 - k] else None
    slope = _slope_pct([x for x in ma_l[-10:] if x is not None]) if sum(1 for x in ma_l[-10:] if x is not None) >= 3 else _slope_pct(v[-min(10, len(v)):])
    th = 2.0 if monthly else 0.15   # 월별 2%/달, 일별 0.15%/일
    mal = ma_l[-1] if ma_l[-1] is not None else (statistics.mean(v[-min(len(v), long_):]))
    if slope is not None and last > mal and slope > th: regime = '상승 추세'
    elif slope is not None and last < mal and slope < -th: regime = '하락 추세'
    elif slope is not None and abs(slope) <= th: regime = '횡보'
    else: regime = '전환 중'
    # 단기선·장기선 교차
    cross = None
    for i in range(len(v) - 1, 0, -1):
        if ma_s[i] is None or ma_l[i] is None or ma_s[i - 1] is None or ma_l[i - 1] is None: continue
        a = ma_s[i - 1] - ma_l[i - 1]; b = ma_s[i] - ma_l[i]
        if a <= 0 < b: cross = {'date': ds[i], 'kind': '골든', 'ago': len(v) - 1 - i}; break
        if a >= 0 > b: cross = {'date': ds[i], 'kind': '데드', 'ago': len(v) - 1 - i}; break
    # 변동성(수익률 표준편차)
    rets = [math.log(v[i] / v[i - 1]) for i in range(1, len(v)) if v[i - 1] > 0]
    win = rets[-long_:] if len(rets) >= 3 else rets
    vol = round(statistics.pstdev(win) * 100, 2) if len(win) >= 2 else None
    sd = statistics.pstdev(v[-long_:]) if len(v) >= 3 else 0
    streak = 0
    for i in range(len(v) - 1, 0, -1):
        d = v[i] - v[i - 1]
        if d == 0: break
        if streak == 0: streak = 1 if d > 0 else -1
        elif (d > 0) == (streak > 0): streak += 1 if streak > 0 else -1
        else: break
    hi, lo = max(v), min(v)
    return {'n': len(v), 'last': last, 'date': ds[-1], 'chg_s': chg(short), 'chg_l': chg(long_), 'ma_s': round(ma_s[-1], 1) if ma_s[-1] else None, 'ma_l': round(mal, 1),
            'slope': slope, 'regime': regime, 'cross': cross, 'vol': vol, 'vol_word': (None if vol is None else '낮음' if vol < (1.5 if not monthly else 4) else '보통' if vol < (3.5 if not monthly else 10) else '높음'),
            'band_lo': round(mal - 2 * sd, 1), 'band_hi': round(mal + 2 * sd, 1), 'pos': round((last - lo) / (hi - lo) * 100) if hi > lo else 50, 'hi': hi, 'lo': lo, 'streak': streak,
            'short': short, 'long': long_, 'unit_word': '개월' if monthly else '일'}

def regime_badge(m):
    r = (m or {}).get('regime') or ''
    cls = 'up' if r == '상승 추세' else 'dn' if r == '하락 추세' else 'flat'
    return f'<span class="fx {cls}">{E(r or "–")}</span>'

def stock_svg(series, vols=None, w=720, h=300, pad_l=12, pad_r=58, pad_t=18, pad_b=44, color='var(--moss)', monthly=False, label=''):
    """주식 차트처럼: 값선, 단기선(가는 선), 장기선(점선), ±2σ 띠, 아래 거래량 막대, 교차점 표시, 마지막 값 꼬리표"""
    s = [(d, float(v)) for d, v in series if v is not None and float(v) > 0]
    if len(s) < 2: return ''
    v = [x[1] for x in s]; ds = [x[0] for x in s]; n = len(v)
    short, long_ = (1, 3) if monthly else (5, 20)
    ma_s = _ma(v, short) if short > 1 else [None] * n; ma_l = _ma(v, long_)
    sd = [statistics.pstdev(v[max(0, i - long_ + 1):i + 1]) if i >= long_ - 1 else None for i in range(n)]
    volh = 56 if vols else 0
    ph = h - pad_t - pad_b - volh
    lo = min(v + [ma_l[i] - 2 * sd[i] for i in range(n) if ma_l[i] is not None and sd[i] is not None])
    hi = max(v + [ma_l[i] + 2 * sd[i] for i in range(n) if ma_l[i] is not None and sd[i] is not None])
    rng = (hi - lo) or 1; lo -= rng * 0.04; hi += rng * 0.04; rng = hi - lo
    X = lambda i: pad_l + (w - pad_l - pad_r) * (i / (n - 1))
    Y = lambda val: pad_t + ph - ph * (val - lo) / rng
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart stock" role="img" aria-label="{E(label or "값 흐름 차트")}">']
    # 격자·눈금
    for k in range(5):
        yv = lo + rng * k / 4; yy = Y(yv)
        out.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{w - pad_r}" y2="{yy:.1f}" stroke="var(--line)" stroke-width="1"/><text x="{w - pad_r + 6}" y="{yy + 4:.1f}" font-size="11" fill="var(--faint)">{fmt(yv)}</text>')
    # ±2σ 띠
    band = [(i, ma_l[i] + 2 * sd[i], ma_l[i] - 2 * sd[i]) for i in range(n) if ma_l[i] is not None and sd[i] is not None]
    if len(band) >= 2:
        up = ' '.join(f'{X(i):.1f},{Y(a):.1f}' for i, a, _ in band); dn = ' '.join(f'{X(i):.1f},{Y(b):.1f}' for i, _, b in reversed(band))
        out.append(f'<polygon points="{up} {dn}" fill="{color}" opacity=".07"/>')
    # 장기선(점선)·단기선
    pl = ' '.join(f'{X(i):.1f},{Y(ma_l[i]):.1f}' for i in range(n) if ma_l[i] is not None)
    if pl: out.append(f'<polyline points="{pl}" fill="none" stroke="var(--grain)" stroke-width="1.6" stroke-dasharray="5 4"/>')
    ps = ' '.join(f'{X(i):.1f},{Y(ma_s[i]):.1f}' for i in range(n) if ma_s[i] is not None)
    if ps: out.append(f'<polyline points="{ps}" fill="none" stroke="#2f5f8a" stroke-width="1.2" opacity=".8"/>')
    # 값선
    out.append('<polyline points="' + ' '.join(f'{X(i):.1f},{Y(v[i]):.1f}' for i in range(n)) + f'" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round"/>')
    # 점 + 설명
    for i in range(n):
        out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v[i]):.1f}" r="{2.2 if n <= 60 else 1.2}" fill="{color}"><title>{E(ds[i])} {fmt(v[i])}</title></circle>')
    # 교차 표시(긴 그림은 최근 8개만 — 2년치에 수십 개가 찍히면 읽기 어려움)
    crosses = []
    for i in range(1, n):
        if None in (ma_s[i], ma_l[i], ma_s[i - 1], ma_l[i - 1]): continue
        a = ma_s[i - 1] - ma_l[i - 1]; b = ma_s[i] - ma_l[i]
        if (a <= 0 < b) or (a >= 0 > b): crosses.append((i, a, b))
    for i, a, b in crosses[-8:]:
        if a <= 0 < b: out.append(f'<path d="M{X(i):.1f},{Y(ma_s[i]) + 12:.1f} l-5,8 h10 z" fill="var(--brick)"><title>{E(ds[i])} 골든 크로스(단기선이 장기선 위로)</title></path>')
        elif a >= 0 > b: out.append(f'<path d="M{X(i):.1f},{Y(ma_s[i]) - 12:.1f} l-5,-8 h10 z" fill="#2f5f8a"><title>{E(ds[i])} 데드 크로스(단기선이 장기선 아래로)</title></path>')
    # 마지막 값 꼬리표
    out.append(f'<rect x="{w - pad_r + 2}" y="{Y(v[-1]) - 9:.1f}" width="{pad_r - 4}" height="18" rx="4" fill="{color}"/><text x="{w - pad_r + (pad_r - 4) / 2 + 2:.0f}" y="{Y(v[-1]) + 4:.1f}" font-size="11" text-anchor="middle" fill="#fff" font-weight="700">{fmt(v[-1])}</text>')
    # 거래량
    if vols:
        vm = {d: q for d, q in vols if q}
        qs = [vm.get(d, 0) for d in ds]; qmax = max(qs) or 1; y0 = pad_t + ph + 8
        bw = max(1.5, (w - pad_l - pad_r) / n * 0.6)
        for i, q in enumerate(qs):
            if q: out.append(f'<rect x="{X(i) - bw / 2:.1f}" y="{y0 + (volh - 12) * (1 - q / qmax):.1f}" width="{bw:.1f}" height="{(volh - 12) * q / qmax:.1f}" fill="var(--line)"><title>{E(ds[i])} 물량 {q:,.0f}</title></rect>')
        out.append(f'<text x="{pad_l}" y="{y0 + volh - 2}" font-size="10" fill="var(--faint)">물량</text>')
    # 날짜 눈금
    ticks = sorted(set([0, n // 4, n // 2, 3 * n // 4, n - 1]))
    span_months = ds[-1][:7] != ds[0][:7]
    for i in ticks:
        lab = ds[i][2:7].replace('-', '.') if (monthly or (span_months and n > 90)) else ds[i][5:10].replace('-', '.')
        out.append(f'<text x="{X(i):.0f}" y="{h - 6}" font-size="11" text-anchor="{"start" if i == 0 else "end" if i == n - 1 else "middle"}" fill="var(--faint)">{lab}</text>')
    out.append(f'<text x="{pad_l}" y="{pad_t - 6}" font-size="11" fill="var(--mute)">― 값 <tspan fill="#2f5f8a">― {short}{"개월" if monthly else "일"}선</tspan> <tspan fill="var(--grain)">- - {long_}{"개월" if monthly else "일"}선</tspan> <tspan fill="var(--faint)">▒ ±2σ 띠</tspan></text>')
    out.append('</svg>')
    return ''.join(out)

def metrics_html(m, unit='원/㎏'):
    if not m or m.get('n', 0) < 3: return '<p class="mini">경향을 잴 만큼 점이 쌓이지 않았습니다(3점 이상 필요).</p>'
    u = m['unit_word']; c = m.get('cross')
    def pc(x): return f'{x:+}%' if x is not None else '–'
    cells = [('추세', regime_badge(m)), (f'{m["short"]}{u}·{m["long"]}{u} 변화', f'{pc(m["chg_s"])} · {pc(m["chg_l"])}'),
             (f'{m["long"]}{u}선 기울기', f'{(m["slope"] or 0):+.2f}%/{u}' if m.get('slope') is not None else '–'), (f'{m["long"]}{u}선 대비', f'{(m["last"] / m["ma_l"] - 1) * 100:+.1f}%' if m.get('ma_l') else '–'),
             ('변동성', f'{m["vol"]}%/{u} ({m["vol_word"]})' if m.get('vol') is not None else '–'), ('기간 내 위치', f'{m["pos"]}% (저 {fmt(m["lo"])} ~ 고 {fmt(m["hi"])})'),
             ('연속', f'{abs(m["streak"])}{u} {"상승" if m["streak"] > 0 else "하락"}' if m.get('streak') else '–'), ('교차', f'{c["ago"]}{u} 전 {c["kind"]} 크로스({c["date"][5:]})' if c else '최근 교차 없음')]
    return '<dl class="kv tm">' + ''.join(f'<dt>{E(k)}</dt><dd>{v}</dd>' for k, v in cells) + '</dl>'

def regime_text(m):
    if not m or m.get('n', 0) < 3: return ''
    r = m['regime']; u = m['unit_word']
    base = {'상승 추세': f'값이 {m["long"]}{u}선 위에서 기울기 {(m["slope"] or 0):+.2f}%/{u}로 올라가는 중', '하락 추세': f'값이 {m["long"]}{u}선 아래에서 기울기 {(m["slope"] or 0):+.2f}%/{u}로 내려가는 중',
            '횡보': f'{m["long"]}{u}선 기울기가 거의 평평(±{0.15 if u == "일" else 2}% 안)', '전환 중': f'값과 {m["long"]}{u}선의 위아래가 기울기 방향과 엇갈림 — 추세가 바뀌는 길목일 수 있음'}.get(r, '')
    if m.get('cross') and m['cross']['ago'] <= (3 if u == '개월' else 10): base += f'. {m["cross"]["ago"]}{u} 전 {m["cross"]["kind"]} 크로스'
    if m.get('vol_word') == '높음': base += '. 변동성이 커서 하루 값에 끌려가지 말 것'
    return base
