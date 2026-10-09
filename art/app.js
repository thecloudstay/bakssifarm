/* 박씨네 — 한 지도, 세 가지 보기(동물농장·어장·농장)
   동물농장: 가축위생방역지원본부 시군별 사육규모(2018~2026, 1월) · 공판장·가축시장
   어장: 국립해양조사원 어장정보도 2025(양식 면허 구역) · 수협 위판장
   농장: 지리적표시 등록부(대표 판매 품목) · 공영도매시장
   경계: 통계청 통계지리정보서비스(2018). 카카오 바탕지도는 자바스크립트 키 등록 뒤 확대 단계에서 켜지도록 자리만 둠(CFG.kakaoKey). */
(function () {
  'use strict';
  var CFG = { kakaoKey: (window.BK_CFG || {}).kakaoKey || '', zoneZoom: 9.5 };
  var MOB = window.matchMedia('(max-width:760px)');
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };

  /* ── 색 */
  var RAMP = ['#eef4eb', '#d4e6cc', '#b2d3a6', '#87b97c', '#5c9a57', '#3b773c', '#24502a'];
  var SEA = ['#eaf2f7', '#cfe1ec', '#aacbdd', '#7fb0c9', '#5591b1', '#356f91', '#1f4c67'];
  var DIV = ['#a8452c', '#d07a5e', '#efc3b2', '#f1f3f0', '#c5dfbd', '#7fb274', '#2f6a34'];
  var DIV_BR = [-0.4, -0.2, -0.05, 0.05, 0.2, 0.4];
  var NONE = '#f1f3f0';
  var KIND = { '과일': '#c96a2a', '채소': '#4f9a4a', '곡물': '#d1a53a', '특용': '#8661a8', '임산': '#7b5a3a', '수산': '#3a7ea5', '축산': '#b2443a', '가공·기타': '#8a938c' };
  var ZONE = { P: ['#2c5530', '패류양식'], H: ['#2f6b8f', '해조류양식'], Y: ['#a8821a', '기타양식'], M: ['#68716a', '마을어업'], J: ['#a8452c', '정치망'] };
  var PIN = { '공판장': 'pin', '가축시장': 'pin cattle', '위판장': 'pin wharf', '도매시장': 'pin whole' };

  /* ── 보기(모드) 정의 */
  var MODES = {
    ani: { name: '동물농장', pickTitle: '어떤 가축을 보시나요', measures: [['n', '마릿수'], ['h', '농가 수'], ['c', '농가 증감']], ramp: RAMP,
      credit: '경계 통계청 통계지리정보서비스(2018) · 사육 가축위생방역지원본부(2026년 1월) · 공공누리 제1유형' },
    sea: { name: '어장', pickTitle: '어떤 양식 품종을 보시나요', measures: [['n', '면허 수'], ['a', '면적'], ['v', '마을어장']], ramp: SEA,
      credit: '경계 통계청(2018) · 어장 국립해양조사원 어장정보도 2025(개방해) · 위판장 위치는 시군 중심 근사' },
    crop: { name: '농장', pickTitle: '어떤 품목을 보시나요', measures: [['k', '대표 품목'], ['n', '등록 수']], ramp: RAMP,
      credit: '경계 통계청(2018) · 품목 지리적표시 등록부(2024년 4월) · 도매시장 위치 근사' }
  };

  var S = { mode: 'ani', sp: '한우', m: 'n', sel: null, pin: null, zone: null, layers: { farm: true, market: true, cattle: true, wharf: true, zone: true, whole: true } };
  var LS, AQ, CR, PL, MK, TOPO, FEAT, UNITS = {}, map, polyLayer, lblLayer, pinLayer, zoneLayer, bizLayer, breaks = [], YEARS, SP, CELLS = {};
  var PR = null, BIZ = null, BIZD = {};   // 경락가 최신값, 인허가 사업장 겹(있을 때만)
  var BIZN = { feed: '사료 공장', slaughter: '도축장', hatchery: '부화장', breeding: '종축장', vet: '동물병원', pharmacy: '동물약국' };
  var ALL_SEA = { k: '모든 양식', g: '', all: true };

  /* ── 글자·숫자 */
  function man(n) {
    if (n == null) return '–';
    if (n >= 100000000) return (n / 100000000).toLocaleString('ko-KR', { maximumFractionDigits: 1 }) + '억';
    if (n >= 10000) return (n / 10000).toLocaleString('ko-KR', { maximumFractionDigits: n >= 1000000 ? 0 : 1 }) + '만';
    return Math.round(n * 10) / 10 === Math.round(n) ? Math.round(n).toLocaleString('ko-KR') : n.toLocaleString('ko-KR', { maximumFractionDigits: 1 });
  }
  function pct(x) { return (x > 0 ? '+' : '') + Math.round(x * 1000) / 10 + '%'; }
  function unitName(u) { var p = u.split('|'); return p[0] === p[1] ? p[0] : p[1]; }
  function unitFull(u) { var p = u.split('|'); return p[0] === p[1] ? p[0] + ' 전체' : p[0] + ' ' + p[1]; }
  function mode() { return MODES[S.mode]; }
  function ramp() { return S.m === 'c' ? DIV : mode().ramp; }

  /* ── 값: 동물농장 */
  function rec(u) { return SP && SP.d ? SP.d[u] : null; }
  function firstIdx(arr, k) { for (var i = 0; i < arr.length; i++) if (arr[i] && arr[i][k] > 0) return i; return -1; }
  function latest(u, k) { var r = rec(u); if (!r) return 0; var v = r.y[r.y.length - 1]; return v ? v[k] : 0; }
  function change(arr, k) {
    var i = firstIdx(arr, k); var last = arr[arr.length - 1];
    if (i < 0 || i === arr.length - 1 || !last) return null;
    return { from: YEARS[i], v: last[k] / arr[i][k] - 1 };
  }
  function baseFarms(u) { var r = rec(u); if (!r) return 0; var i = firstIdx(r.y, 0); return i < 0 ? 0 : r.y[i][0]; }

  /* ── 값: 모드 공통 */
  function val(u) {
    if (S.mode === 'ani') {
      var r = rec(u); if (!r) return null;
      if (S.m === 'n') return latest(u, 1) || null;
      if (S.m === 'h') return latest(u, 0) || null;
      var c = change(r.y, 0); if (!c) return null;
      var i = firstIdx(r.y, 0); if (r.y[i][0] < 10) return null;
      return c.v;
    }
    if (S.mode === 'sea') {
      var e = AQ.units[u]; if (!e) return null;
      if (S.m === 'v') return e.v[0] || null;
      if (SP.all) return (S.m === 'n' ? e.n : e.ha) || null;
      var x = SP.units[u]; if (!x) return null;
      return (S.m === 'n' ? x[0] : x[1]) || null;
    }
    var c2 = CR.units[u]; if (!c2) return null;
    if (SP.all) return S.m === 'k' ? c2.main : c2.n;
    return c2.items.indexOf(SP.k) >= 0 ? (S.m === 'k' ? SP.kind : c2.list.filter(function (x) { return x.name.indexOf(SP.k) >= 0; }).length) : null;
  }
  function unitKeys() {
    if (S.mode === 'ani') return Object.keys(SP.d);
    if (S.mode === 'sea') return Object.keys(SP.all ? AQ.units : SP.units);
    return Object.keys(CR.units).filter(function (u) { return SP.all || CR.units[u].items.indexOf(SP.k) >= 0; });
  }
  function computeBreaks() {
    if (S.m === 'c') { breaks = DIV_BR; return; }
    if (S.m === 'k') { breaks = []; return; }
    var vs = unitKeys().map(val).filter(function (v) { return v > 0; }).sort(function (a, b) { return a - b; });
    breaks = [];
    var R = ramp();
    for (var i = 1; i < R.length; i++) breaks.push(vs[Math.floor(vs.length * i / R.length)] || 0);
  }
  function colorOf(v) {
    if (v == null) return NONE;
    if (S.m === 'c') { var j = 0; while (j < DIV_BR.length && v >= DIV_BR[j]) j++; return DIV[j]; }
    if (S.m === 'k') return KIND[v] || NONE;
    var R = ramp(), k = 0; while (k < breaks.length && v >= breaks[k]) k++; return R[k];
  }
  function dark(c) { var R = ramp(); return R.indexOf(c) >= 5 || c === DIV[0] || c === DIV[6] || S.m === 'k'; }
  function valText(u) {
    var v = val(u); if (v == null) return '자료 없음';
    if (S.mode === 'ani') return S.m === 'c' ? '농가 ' + pct(v) : S.m === 'n' ? man(v) + SP.w : man(v) + '호';
    if (S.mode === 'sea') return S.m === 'v' ? '마을어장 ' + man(v) + '곳' : S.m === 'n' ? '면허 ' + man(v) + '건' : man(v) + '㏊';
    if (S.m === 'k') return SP.all ? '대표 ' + v + ' · ' + CR.units[u].items.slice(0, 3).join(', ') : SP.k;
    return '등록 ' + v + '건';
  }

  /* ── 지도 */
  function initMap() {
    map = L.map('map', { zoomControl: !MOB.matches, attributionControl: false, minZoom: 6, maxZoom: 14, zoomSnap: 0.25, preferCanvas: true });
    if (map.zoomControl) map.zoomControl.setPosition('topright');
    var land = topojson.merge(TOPO, TOPO.objects.units.geometries);
    L.geoJSON(land, { interactive: false, style: { stroke: false, fillColor: NONE, fillOpacity: 1 } }).addTo(map);
    polyLayer = L.geoJSON(FEAT, {
      style: styleOf,
      onEachFeature: function (f, lyr) {
        var u = f.properties.u; UNITS[u] = lyr;
        lyr.on('mouseover', function () { if (S.sel !== u) lyr.setStyle({ weight: 2, color: '#1e2621' }); lyr.bringToFront(); hoverTip(u, lyr); });
        lyr.on('mouseout', function () { lyr.setStyle(styleOf(f)); lyr.closeTooltip(); if (S.sel) UNITS[S.sel] && UNITS[S.sel].bringToFront(); });
        lyr.on('click', function () { selectUnit(u, false); });
      }
    }).addTo(map);
    var sido = topojson.mesh(TOPO, TOPO.objects.units, function (a, b) { return a !== b && a.properties.sd !== b.properties.sd; });
    L.geoJSON(sido, { interactive: false, style: { color: '#7f8b81', weight: 1.1, opacity: 0.9 } }).addTo(map);
    var coast = topojson.mesh(TOPO, TOPO.objects.units, function (a, b) { return a === b; });
    L.geoJSON(coast, { interactive: false, style: { color: '#9aa59c', weight: 0.9, opacity: 0.9 } }).addTo(map);
    zoneLayer = L.layerGroup().addTo(map);
    bizLayer = L.layerGroup().addTo(map);
    lblLayer = L.layerGroup().addTo(map);
    pinLayer = L.layerGroup().addTo(map);
    fitKorea();
    map.on('zoomend', function () { drawLabels(); drawPins(); drawZones(); hint(); });
    map.on('moveend', function () { drawZones(); drawBiz(); });
  }
  function fitKorea() {
    var pad = MOB.matches ? { paddingTopLeft: [16, 130], paddingBottomRight: [16, 225] } : { padding: [24, 24] };
    map.fitBounds([[33.1, 125.0], [38.62, 129.6]], pad);
  }
  function styleOf(f) {
    var u = f.properties.u, v = val(u), sel = S.sel === u;
    var fill = S.layers.farm ? colorOf(v) : '#ffffff';
    var z = map ? map.getZoom() : 7;
    var faded = S.mode === 'sea' && z >= CFG.zoneZoom && S.layers.zone;
    if (faded) return { fillColor: '#e6e9e4', fillOpacity: 1, color: sel ? '#1e2621' : '#ffffff', weight: sel ? 2.4 : 0.8, opacity: 1 };
    return { fillColor: fill, fillOpacity: 1, color: sel ? '#1e2621' : '#ffffff', weight: sel ? 2.4 : 0.8, opacity: 1 };
  }
  function restyle() { polyLayer.setStyle(styleOf); if (S.sel && UNITS[S.sel]) UNITS[S.sel].bringToFront(); }
  function hoverTip(u, lyr) {
    lyr.bindTooltip('<b>' + esc(unitName(u)) + '</b> · ' + esc(valText(u)), { className: 'tip', sticky: true, direction: 'top', offset: [0, -8] }).openTooltip();
  }
  function centerOf(lyr) {
    var best = null, area = -1;
    var ll = lyr.getLatLngs(); var rings = [];
    (function walk(a) { if (a.length && a[0].lat !== undefined) rings.push(a); else a.forEach(walk); })(ll);
    rings.forEach(function (r) { var b = L.latLngBounds(r); var s = (b.getNorth() - b.getSouth()) * (b.getEast() - b.getWest()); if (s > area) { area = s; best = b; } });
    return best ? best.getCenter() : lyr.getBounds().getCenter();
  }
  function drawLabels() {
    lblLayer.clearLayers();
    if (!S.layers.farm) return;
    var z = map.getZoom();
    var list = unitKeys().filter(function (u) { return val(u) != null && UNITS[u] && (S.m !== 'c' || baseFarms(u) >= 50); });
    if (S.m === 'k') list.sort(function (a, b) { return (CR.units[b] ? CR.units[b].n : 0) - (CR.units[a] ? CR.units[a].n : 0); });
    else list.sort(function (a, b) { return S.m === 'c' ? Math.abs(val(b)) - Math.abs(val(a)) : val(b) - val(a); });
    var n = z < 7 ? 5 : z < 8 ? 10 : z < 9 ? 24 : 200;
    list.slice(0, n).forEach(function (u) {
      var c = colorOf(val(u));
      var txt = unitName(u);
      if (S.mode === 'crop' && S.m === 'k' && SP.all && z >= 7.5) txt += '<small>' + esc(CR.units[u].items.slice(0, 2).join('·')) + '</small>';
      L.marker(centerOf(UNITS[u]), { interactive: false, keyboard: false,
        icon: L.divIcon({ className: '', html: '<div class="lbl' + (dark(c) ? ' on-dark' : '') + '">' + txt + '</div>', iconSize: [0, 0] }) }).addTo(lblLayer);
    });
  }

  /* ── 핀(공판장·가축시장·위판장·도매시장) */
  function pins() {
    if (S.mode === 'ani') return MK.items.filter(function (m) { return m.type === '공판장' ? S.layers.market : S.layers.cattle; });
    if (S.mode === 'sea') return S.layers.wharf ? PL.wharfs : [];
    return S.layers.whole ? PL.markets : [];
  }
  function allPins() { return MK.items.concat(PL.wharfs, PL.markets); }
  function pinById(id) { return allPins().filter(function (x) { return x.id === id; })[0]; }
  function shortName(m) { return m.name.replace(/^농협 /, '').replace(/축산물공판장|축산물도매시장|공판장|농수산물도매시장|농산물도매시장|수협$/, '').replace(/ 농$/, '').trim(); }
  function drawPins() {
    pinLayer.clearLayers();
    var z = map.getZoom();
    pins().forEach(function (m) {
      var cls = PIN[m.type] + (m.verified ? '' : ' unv') + (S.pin === m.id ? ' sel' : '') + (z < 8.5 && m.type !== '공판장' ? ' sm' : '');
      var mk = L.marker([m.lat, m.lng], { icon: L.divIcon({ className: '', html: '<div class="' + cls + '"></div>', iconSize: [16, 16], iconAnchor: [8, 8] }), keyboard: true, title: m.name, riseOnHover: true, zIndexOffset: 600 });
      mk.on('click', function () { selectPin(m.id); });
      mk.addTo(pinLayer);
      if (z >= 8 || S.pin === m.id) {
        L.marker([m.lat, m.lng], { interactive: false, icon: L.divIcon({ className: '', html: '<div class="pin-name ' + (m.type === '위판장' ? 'sea' : '') + '">' + esc(shortName(m)) + '</div>', iconSize: [0, 0] }) }).addTo(pinLayer);
      }
    });
  }

  /* ── 인허가 사업장 핀(사료 공장·도축장 등, 공공 좌표) */
  function drawBiz() {
    bizLayer.clearLayers();
    if (S.mode !== 'ani' || !BIZ) return;
    var z = map.getZoom(), b = map.getBounds();
    BIZ.layers.forEach(function (l) {
      if (!l.public || !S.layers['biz_' + l.k]) return;
      if (!BIZD[l.k]) { BIZD[l.k] = { pins: [] }; fetch('data/biz/' + l.k + '.json').then(function (r) { return r.json(); }).then(function (d) { BIZD[l.k] = d; drawBiz(); }); return; }
      (BIZD[l.k].pins || []).forEach(function (p) {
        if (!p.lat || !b.contains([p.lat, p.lng])) return;
        var mk = L.marker([p.lat, p.lng], { icon: L.divIcon({ className: '', html: '<div class="pin biz' + (z < 9 ? ' sm' : '') + '" title="' + esc(p.name) + '"></div>', iconSize: [12, 12], iconAnchor: [6, 6] }), zIndexOffset: 400 });
        mk.bindTooltip('<b>' + esc(p.name) + '</b> · ' + esc(BIZN[l.k] || l.name) + (p.kind ? ' · ' + esc(p.kind) : '') + '<br>' + esc(p.addr || ''), { className: 'tip', direction: 'top', offset: [0, -6] });
        mk.addTo(bizLayer);
      });
    });
  }

  /* ── 어장 구역(확대하면 칸 단위로 불러옴) */
  function drawZones() {
    if (S.mode !== 'sea' || !S.layers.zone || map.getZoom() < CFG.zoneZoom) { if (zoneLayer.getLayers().length) { zoneLayer.clearLayers(); restyle(); } return; }
    var b = map.getBounds();
    var need = AQ.cells.filter(function (c) { return !(c.b[2] < b.getSouth() || c.b[0] > b.getNorth() || c.b[3] < b.getWest() || c.b[1] > b.getEast()); });
    zoneLayer.clearLayers(); restyle();
    need.forEach(function (c) {
      if (CELLS[c.f]) { paintCell(CELLS[c.f]); return; }
      CELLS[c.f] = [];
      fetch('data/aqua/' + c.f).then(function (r) { return r.json(); }).then(function (zs) { CELLS[c.f] = zs; if (map.getZoom() >= CFG.zoneZoom && S.mode === 'sea') paintCell(zs); });
    });
  }
  function paintCell(zs) {
    zs.forEach(function (z) {
      var st = ZONE[z.k] || ZONE.Y;
      var isM = z.k === 'M', isJ = z.k === 'J';
      var sel = S.zone === z;
      var poly = L.polygon(z.p, { color: st[0], weight: sel ? 2.5 : isM ? 1 : 1.2, dashArray: isM || isJ ? '4 3' : null, fillColor: st[0], fillOpacity: isJ ? 0.05 : isM ? 0.12 : 0.42, opacity: 0.9 });
      poly.bindTooltip('<b>' + esc(st[1]) + '</b>' + (z.f ? ' · ' + esc(z.f) : '') + (z.ha ? ' · ' + esc(z.ha) + '㏊' : ''), { className: 'tip', sticky: true, direction: 'top' });
      poly.on('click', function (e) { L.DomEvent.stopPropagation(e); selectZone(z); });
      poly.addTo(zoneLayer);
    });
  }
  function hint() {
    var el = $('#hint');
    if (S.mode !== 'sea' || !S.layers.zone) { el.hidden = true; return; }
    if (map.getZoom() < CFG.zoneZoom) { el.textContent = '바다 쪽을 더 확대하면 양식 면허 구역이 하나씩 보입니다'; el.hidden = false; }
    else el.hidden = true;
  }

  /* ── 지도 위 칩·범례·출처 */
  var WAIT = [['사료 공장', '전국 1만 4천여 곳'], ['도축장', '전국 200곳'], ['종축·부화장', '전국 2천여 곳'], ['동물병원·약국', '산업동물 구분 작업 후']];
  function drawLayers() {
    var h = '';
    if (S.mode === 'ani') {
      var nM = MK.items.filter(function (m) { return m.type === '공판장'; }).length, nC = MK.items.length - nM;
      h += chip('farm', '사육 분포', RAMP[4]);
      h += chip('market', '공판장 <span class="n">' + nM + '</span>', '#a8821a');
      h += chip('cattle', '가축시장 <span class="n">' + nC + '</span>', '#ffffff', true);
      if (BIZ && BIZ.layers && BIZ.layers.some(function (l) { return l.public; })) BIZ.layers.filter(function (l) { return l.public; }).forEach(function (l) { S.layers['biz_' + l.k] = S.layers['biz_' + l.k] || false; h += chip('biz_' + l.k, esc(BIZN[l.k] || l.name), '#68716a'); });
      else h += '<button type="button" class="chip wait" title="' + esc('공공데이터 키 연결 후 전국 좌표로 표시: ' + WAIT.map(function (w) { return w[0] + '(' + w[1] + ')'; }).join(', ')) + '"><span class="dot"></span>사료 공장·도축장 외 2종 <span class="n">곧 추가</span></button>';
    } else if (S.mode === 'sea') {
      h += chip('farm', '양식 분포', SEA[4]);
      h += chip('zone', '면허 구역 <span class="n">1만 1천</span>', '#2c5530');
      h += chip('wharf', '위판장 <span class="n">' + PL.wharfs.length + '</span>', '#3a7ea5');
      h += '<button type="button" class="chip wait" title="수협 위판 시세·어촌계 연락처는 연동창구 연결 뒤 표시"><span class="dot"></span>위판 시세 <span class="n">곧 추가</span></button>';
    } else {
      h += chip('farm', '대표 품목', KIND['과일']);
      h += chip('whole', '도매시장 <span class="n">' + PL.markets.length + '</span>', '#a8821a');
      h += '<button type="button" class="chip wait" title="농업경영체 등록 통계·재배면적은 자료 받는 대로 시군 단위로 표시"><span class="dot"></span>재배면적·농가 수 <span class="n">곧 추가</span></button>';
    }
    $('#layers').innerHTML = h;
    $('#layers').querySelectorAll('[data-l]').forEach(function (b) {
      b.addEventListener('click', function () {
        var k = b.getAttribute('data-l'); S.layers[k] = !S.layers[k]; b.setAttribute('aria-pressed', S.layers[k]);
        if (k === 'farm') { restyle(); drawLabels(); drawLegend(); } else if (k === 'zone') { drawZones(); hint(); } else if (k.indexOf('biz_') === 0) drawBiz(); else drawPins();
      });
    });
    $('#credit').textContent = mode().credit;
  }
  function chip(k, label, color, ring) {
    return '<button type="button" class="chip" data-l="' + k + '" aria-pressed="' + S.layers[k] + '"><span class="dot" style="background:' + color + (ring ? ';box-shadow:inset 0 0 0 2px #1e2621' : '') + '"></span>' + label + '</button>';
  }
  function drawLegend() {
    var el = $('#legend');
    if (!S.layers.farm) { el.hidden = true; return; } el.hidden = false;
    var t, R = ramp();
    if (S.m === 'c') {
      t = S.sp + ' 농가 증감 (' + firstYearOf() + '→' + YEARS[YEARS.length - 1] + ')';
      el.innerHTML = '<h3>' + esc(t) + '</h3><div class="sw">' + DIV.map(function (c) { return '<span style="background:' + c + '"></span>'; }).join('') + '</div><div class="ticks"><span>줄어듦</span><span>그대로</span><span>늘어남</span></div>';
      return;
    }
    if (S.m === 'k') {
      t = SP.all ? '시군별 대표 품목(가장 많이 등록된 갈래)' : SP.k + ' 지리적표시가 있는 시군';
      el.innerHTML = '<h3>' + esc(t) + '</h3><div class="cats">' + (SP.all ? CR.kinds : [SP.kind]).map(function (k) { return '<span><i style="background:' + KIND[k] + '"></i>' + esc(k) + '</span>'; }).join('') + '</div><div class="none"><i></i>등록 품목 없음</div>';
      return;
    }
    var unit, title;
    if (S.mode === 'ani') { unit = S.m === 'n' ? SP.w : '호'; title = S.sp + ' ' + (S.m === 'n' ? '마릿수' : '농가 수') + ' · ' + YEARS[YEARS.length - 1] + '년 1월'; }
    else if (S.mode === 'sea') { unit = S.m === 'n' ? '건' : S.m === 'a' ? '㏊' : '곳'; title = S.m === 'v' ? '마을어장(어촌계) 수' : (SP.all ? '양식 ' : SP.k + ' 양식 ') + (S.m === 'n' ? '면허 수' : '면적'); }
    else { unit = '건'; title = (SP.all ? '지리적표시' : SP.k) + ' 등록 수'; }
    var lo = breaks[0], hi = breaks[breaks.length - 1];
    el.innerHTML = '<h3>' + esc(title) + '</h3><div class="sw">' + R.map(function (c) { return '<span style="background:' + c + '"></span>'; }).join('') +
      '</div><div class="ticks"><span>' + man(lo) + unit + ' 아래</span><span>' + man(hi) + unit + ' 넘음</span></div><div class="none"><i></i>없음 또는 자료 없음</div>';
  }
  function firstYearOf() { var i = firstIdx(SP.tot, 0); return YEARS[Math.max(0, i)]; }

  /* ── 판: 공통 조각 */
  function linksBlock() {
    return '<section class="sec more-in"><p class="eyebrow"><span>박씨네가 더 해 드리는 일</span></p><div class="cards">' +
      '<a href="price/index.html"><b>경락가 조회</b><span>소·돼지 등급별 경락가, 농산물 도매시장·수협 위판 시세</span></a>' +
      '<a href="gongu/index.html"><b>사료·자재 공동구매</b><span>같은 시군끼리 모아서 싸게. 모집판 열고 신청받기</span></a>' +
      '<a href="pro/index.html"><b>데이터·업체 등록</b><span>리 단위 사료 수요 지도, 진입·이탈 지수, 업체 알리기</span></a></div></section>';
  }
  function kakaoLink(name) { return 'https://map.kakao.com/?q=' + encodeURIComponent(name); }

  /* ── 판: 동물농장 */
  var EX = {
    소: { t: '한우 거세 경락가', g: ['1++', '1+', '1', '2', '3'], p: [23180, 21040, 19350, 16220, 12480], d: [120, -40, 85, 0, -60], on: 1 },
    돼지: { t: '돼지 탕박 경락가', g: ['1+', '1', '2', '등외'], p: [5820, 5610, 4980, 3900], d: [35, 22, -10, 0], on: 0 }
  };
  function board(group) {
    var ex = EX[group];
    if (PR && PR.ekape) {
      var sec = PR.ekape.filter(function (x) { return x.title.indexOf(group === '소' ? '한우' : group === '돼지' ? '돼지' : '없음') === 0; })[0];
      if (sec) {
        var cells2 = sec.rows.map(function (r, i) { var d = r.d; var dc = d > 0 ? 'up' : d < 0 ? 'dn' : ''; return '<div class="' + (i === 1 ? 'on' : '') + '"><span class="g">' + esc(r.g) + '</span><span class="p">' + r.p.toLocaleString('ko-KR') + '</span><span class="d ' + dc + '">' + (d > 0 ? '▲' + d : d < 0 ? '▼' + (-d) : d === 0 ? '–' : '') + '</span></div>'; }).join('');
        return '<section class="sec sec-board"><p class="eyebrow"><span>' + esc(PR.date) + ' ' + esc(sec.title) + ' 경락가</span><span>원/kg</span></p><div class="board" style="--cols:' + sec.rows.length + '">' + cells2 + '</div><p class="board-note">축산물품질평가원 등급판정정보, 전국 평균(결함 포함). <a href="price/index.html">공판장별 가격 →</a></p></section>';
      }
    }
    if (!ex) return '<section class="sec"><p class="eyebrow"><span>오늘 경락가</span></p><p class="board-note" style="margin:0">' + esc(S.sp) + '은(는) 공식 경락가가 없는 품목입니다. 산지 가격은 제보가 모이는 대로 이곳에 올립니다.</p></section>';
    var cells = ex.g.map(function (g, i) {
      var d = ex.d[i]; var dc = d > 0 ? 'up' : d < 0 ? 'dn' : '';
      return '<div class="' + (i === ex.on ? 'on' : '') + '"><span class="g">' + g + '</span><span class="p">' + ex.p[i].toLocaleString('ko-KR') + '</span><span class="d ' + dc + '">' + (d > 0 ? '▲' + d : d < 0 ? '▼' + (-d) : '–') + '</span></div>';
    }).join('');
    return '<section class="sec sec-board"><p class="eyebrow"><span>오늘 ' + ex.t + ' <span class="tag">예시 숫자</span></span><span>원/kg</span></p>' +
      '<div class="board" style="--cols:' + ex.g.length + '">' + cells + '</div>' +
      '<p class="board-note">공공데이터 키를 붙이면 축산물품질평가원 경락가가 3시간마다 들어옵니다. 지금 숫자는 화면 확인용 예시입니다. <a href="price/index.html">경락가 조회 화면 →</a></p></section>';
  }
  function summary(arr, bins, label, sub) {
    var last = arr[arr.length - 1] || [0, 0];
    var ch = change(arr, 0), cn = change(arr, 1);
    var h = '<section class="sec"><h1 class="place">' + esc(label) + '<small>' + esc(sub) + '</small></h1>';
    h += '<div class="nums"><div><b>' + man(last[0]) + '<i>호</i></b><span>농가</span></div><div><b>' + man(last[1]) + '<i>' + SP.w + '</i></b><span>마릿수</span></div></div>';
    if (ch && cn) {
      h += '<p class="chg">' + ch.from + '년보다 농가 <em class="' + (ch.v >= 0 ? 'up' : 'dn') + '">' + pct(ch.v) + '</em> · 마릿수 <em class="' + (cn.v >= 0 ? 'up' : 'dn') + '">' + pct(cn.v) + '</em></p>';
      h += '<p class="read">' + reading(ch.v, cn.v) + concentration(bins) + '</p>';
    }
    return h + '</section>';
  }
  function reading(a, b) {
    if (a < -0.03 && b > 0.03) return '농가는 줄었는데 마릿수는 늘었습니다. 큰 농장으로 모이고 있습니다. ';
    if (a < -0.03 && b < -0.03) return '농가와 마릿수가 함께 줄고 있습니다. ';
    if (a > 0.03 && b > 0.03) return '농가와 마릿수가 함께 늘고 있습니다. ';
    if (a > 0.03 && b < -0.03) return '농가는 늘었지만 마릿수는 줄었습니다. 작은 농가가 늘고 있습니다. ';
    return '몇 해째 큰 변화 없이 유지되고 있습니다. ';
  }
  function concentration(b) {
    if (!b || !b.length) return '';
    var H = b.reduce(function (s, x) { return s + x[0]; }, 0), N = b.reduce(function (s, x) { return s + x[1]; }, 0);
    if (!H || !N || !b[0][0]) return '';
    var ph = b[0][0] / H, pn = b[0][1] / N;
    if (pn < 0.2) return '';
    return SP.bins[0] + ' 농가는 ' + Math.round(ph * 100) + '%뿐이지만 마릿수는 ' + Math.round(pn * 100) + '%를 차지합니다.';
  }
  function trendSvg(arr) {
    var W = 340, H = 112, pl = 4, pr = 4, pt = 14, pb = 22, n = YEARS.length, bw = (W - pl - pr) / n;
    var mN = Math.max.apply(null, arr.map(function (x) { return x ? x[1] : 0; })) || 1;
    var mH = Math.max.apply(null, arr.map(function (x) { return x ? x[0] : 0; })) || 1;
    var s = '<svg class="trend" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + YEARS[0] + '년부터 ' + YEARS[n - 1] + '년까지 마릿수와 농가 수">';
    var pts = [];
    arr.forEach(function (x, i) {
      var cx = pl + bw * i + bw / 2;
      if (x && x[1] > 0) { var bh = (H - pt - pb) * x[1] / mN; s += '<rect x="' + (cx - bw * 0.3) + '" y="' + (H - pb - bh) + '" width="' + bw * 0.6 + '" height="' + bh + '" rx="2" fill="#cfe2c8"/>'; }
      if (x && x[0] > 0) pts.push([cx, pt + (H - pt - pb) * (1 - x[0] / mH) * 0.92]);
      if (i === 0 || i === n - 1 || i === Math.floor(n / 2)) s += '<text x="' + cx + '" y="' + (H - 6) + '" text-anchor="middle">' + YEARS[i] + '</text>';
    });
    if (pts.length > 1) {
      s += '<polyline points="' + pts.map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ') + '" fill="none" stroke="#2c5530" stroke-width="2" stroke-linejoin="round"/>';
      var a = pts[pts.length - 1]; s += '<circle cx="' + a[0] + '" cy="' + a[1] + '" r="3.5" fill="#2c5530"/>';
    }
    return s + '</svg>';
  }
  var BINC = ['#24502a', '#3b773c', '#5c9a57', '#87b97c', '#b2d3a6', '#d4e6cc', '#eef4eb'];
  function scaleBlock(b) {
    if (!b || !b.length) return '';
    var H = b.reduce(function (s, x) { return s + x[0]; }, 0), N = b.reduce(function (s, x) { return s + x[1]; }, 0);
    if (!H) return '';
    function row(lab, k, T) { return '<span class="lab">' + lab + '</span><div class="stack">' + b.map(function (x, i) { var w = T ? x[k] / T * 100 : 0; return w > 0 ? '<span style="width:' + w.toFixed(2) + '%;background:' + BINC[i] + '" title="' + esc(SP.bins[i]) + ' ' + Math.round(w) + '%"></span>' : ''; }).join('') + '</div>'; }
    return '<section class="sec"><p class="eyebrow"><span>농장 규모별</span><span>' + YEARS[YEARS.length - 1] + '년 1월</span></p><div class="scale">' + row('농가 수', 0, H) + row('마릿수', 1, N) + '</div>' +
      '<div class="scale-key">' + SP.bins.map(function (l, i) { return '<span><i style="background:' + BINC[i] + '"></i>' + esc(l) + '</span>'; }).join('') + '</div></section>';
  }
  function topList(title, unit, us, get) {
    if (!us.length) return '';
    var mx = get(us[0]);
    return '<section class="sec"><p class="eyebrow"><span>' + esc(title) + '</span><span>' + esc(unit) + '</span></p><ol class="top">' + us.map(function (u, i) {
      return '<li data-u="' + esc(u) + '" tabindex="0"><span class="no">' + (i + 1) + '</span><span class="nm">' + esc(unitFull(u)) + '</span><span class="v">' + man(get(u)) + esc(unit) + '</span><span class="bar2"><span style="width:' + (get(u) / mx * 100).toFixed(1) + '%"></span></span></li>';
    }).join('') + '</ol></section>';
  }
  function rankText(u) {
    var all = Object.keys(SP.d).filter(function (x) { return latest(x, 1) > 0; }).sort(function (a, b) { return latest(b, 1) - latest(a, 1); });
    var i = all.indexOf(u); if (i < 0) return '';
    var sd = u.split('|')[0]; var inSd = all.filter(function (x) { return x.split('|')[0] === sd; });
    var j = inSd.indexOf(u);
    return '<p class="rank">마릿수 전국 ' + (i + 1) + '위' + (inSd.length > 1 ? ' · ' + sd + ' 안에서 ' + (j + 1) + '위' : '') + ' (' + all.length + '개 시군 중)</p>';
  }
  function aniPanel() {
    var h = '', boardHtml = board(SP.g), key = '<div class="key"><span><i style="background:#cfe2c8"></i>마릿수</span><span><i style="background:#2c5530;height:2px;vertical-align:3px"></i>농가 수</span></div>';
    if (S.sel) {
      var r = rec(S.sel);
      h += backBtn();
      if (!r) h += '<section class="sec"><h1 class="place">' + esc(unitFull(S.sel)) + '<small>' + esc(S.sp) + '</small></h1><p class="read">이 시군에는 ' + esc(S.sp) + ' 사육 기록이 없습니다.</p></section>';
      else {
        var sum = summary(r.y, r.b, unitFull(S.sel), S.sp + ' · ' + YEARS[YEARS.length - 1] + '년 1월').replace('</section>', rankText(S.sel) + '</section>');
        h += MOB.matches ? sum + boardHtml : boardHtml + sum;
        h += '<section class="sec"><p class="eyebrow"><span>' + YEARS[0] + '년부터 지금까지</span></p>' + trendSvg(r.y) + key + '</section>';
        h += scaleBlock(r.b);
      }
      h += otherModes(S.sel);
    } else {
      var nb = Object.keys(SP.d).reduce(function (acc, u) { var b = SP.d[u].b; if (!b) return acc; b.forEach(function (x, i) { acc[i] = acc[i] || [0, 0]; acc[i][0] += x[0]; acc[i][1] += x[1]; }); return acc; }, []);
      var sum2 = summary(SP.tot, nb, '전국 ' + S.sp, YEARS[YEARS.length - 1] + '년 1월 · ' + Object.keys(SP.d).length + '개 시군');
      h += MOB.matches ? sum2 + boardHtml : boardHtml + sum2;
      h += '<section class="sec"><p class="eyebrow"><span>' + YEARS[0] + '년부터 지금까지</span></p>' + trendSvg(SP.tot) + key + '</section>';
      var us = Object.keys(SP.d).filter(function (u) { return latest(u, 1) > 0; }).sort(function (a, b) { return latest(b, 1) - latest(a, 1); }).slice(0, 8);
      h += topList(S.sp + ' 많은 곳', SP.w, us, function (u) { return latest(u, 1); });
      h += scaleBlock(nb);
      h += linksBlock();
    }
    h += '<section class="sec"><p class="src">자료: 가축위생방역지원본부 「전국 시군별 ' + esc(S.sp) + ' 사육규모 현황」, 공공데이터포털(공공누리 제1유형). 해마다 1월 기준. 광역시는 구·군을 합친 값입니다. 개별 농가 위치는 싣지 않습니다.</p></section>';
    return h;
  }

  /* ── 판: 어장 */
  function seaBoard(title) {
    return '<section class="sec"><p class="eyebrow"><span>' + esc(title || '오늘 위판 시세') + ' <span class="tag mute">연동 전</span></span></p><p class="board-note" style="margin:0">수협 위판 시세는 수협중앙회 위판정보 연동창구를 붙이면 품종별로 들어옵니다. 지금은 면허 구역과 위판장 위치까지만 보입니다. <a href="price/index.html">경락가 조회 화면 →</a></p></section>';
  }
  function seaPanel() {
    var h = '';
    if (S.zone) return zonePanel();
    if (S.sel) {
      var e = AQ.units[S.sel];
      h += backBtn();
      if (!e) h += '<section class="sec"><h1 class="place">' + esc(unitFull(S.sel)) + '<small>어장</small></h1><p class="read">이 시군에는 어장 면허 기록이 없습니다. 바다를 끼지 않은 곳이거나 내수면만 있는 곳입니다.</p></section>';
      else {
        h += '<section class="sec"><h1 class="place">' + esc(unitFull(S.sel)) + '<small>양식 면허 · 어장정보도 2025</small></h1>';
        h += '<div class="nums"><div><b>' + man(e.n) + '<i>건</i></b><span>양식 면허</span></div><div><b>' + man(e.ha) + '<i>㏊</i></b><span>면허 면적</span></div></div>';
        h += '<p class="chg">마을어장(어촌계) ' + man(e.v[0]) + '곳 · ' + man(e.v[1]) + '㏊' + (e.j ? ' · 정치망 ' + e.j + '곳' : '') + '</p>';
        if (e.top.length) h += '<p class="read">주된 양식은 ' + e.top.slice(0, 3).map(function (t) { return t[0]; }).join(', ') + '입니다. ' + (e.top[0][1] / e.n > 0.5 ? e.top[0][0] + ' 면허가 절반을 넘습니다.' : '') + '</p>';
        h += '</section>';
        if (e.top.length) {
          var mx = e.top[0][1];
          h += '<section class="sec"><p class="eyebrow"><span>품종별 면허</span><span>건 · ㏊</span></p><ol class="top">' + e.top.map(function (t, i) {
            return '<li data-sp="' + esc(t[0]) + '" tabindex="0"><span class="no">' + (i + 1) + '</span><span class="nm">' + esc(t[0]) + '</span><span class="v">' + t[1] + '건 · ' + man(t[2]) + '㏊</span><span class="bar2"><span style="width:' + (t[1] / mx * 100).toFixed(1) + '%"></span></span></li>';
          }).join('') + '</ol></section>';
        }
        var ws = PL.wharfs.filter(function (w) { return w.u === S.sel; });
        if (ws.length) h += '<section class="sec"><p class="eyebrow"><span>이 시군 위판장</span><span>수협</span></p><ul class="plain">' + ws.map(function (w) { return '<li><button type="button" class="lnk" data-pin="' + w.id + '">' + esc(w.name) + '</button> <span class="tag mute">위치 근사</span></li>'; }).join('') + '</ul></section>';
        h += seaBoard();
        h += '<section class="sec"><p class="read small">지도를 확대하면 이 시군의 면허 구역이 한 칸씩 보입니다. 구역을 누르면 면허 종류·품종·면적·만료 연도가 나옵니다.</p></section>';
      }
      h += otherModes(S.sel);
    } else {
      var tn = 0, ta = 0; Object.keys(AQ.units).forEach(function (u) { tn += AQ.units[u].n; ta += AQ.units[u].ha; });
      if (SP.all) {
        h += '<section class="sec"><h1 class="place">전국 양식 어장<small>어장정보도 2025 · ' + Object.keys(AQ.units).length + '개 시군</small></h1>';
        h += '<div class="nums"><div><b>' + man(tn) + '<i>건</i></b><span>양식 면허</span></div><div><b>' + man(ta) + '<i>㏊</i></b><span>면허 면적</span></div></div>';
        h += '<p class="read">김·미역·다시마 같은 해조류, 굴·꼬막·전복 같은 패류가 대부분입니다. 전남이 면허의 절반 넘게 차지합니다.</p></section>';
        h += seaBoard();
        var sp = AQ.species.filter(function (s) { return s.n >= 20; }).sort(function (a, b) { return b.n - a.n; }).slice(0, 10);
        var mx = sp[0].n;
        h += '<section class="sec"><p class="eyebrow"><span>품종별 면허</span><span>건</span></p><ol class="top">' + sp.map(function (s, i) {
          return '<li data-sp="' + esc(s.k) + '" tabindex="0"><span class="no">' + (i + 1) + '</span><span class="nm">' + esc(s.k) + (s.g !== s.k ? ' <small>' + esc(s.g) + '</small>' : '') + '</span><span class="v">' + man(s.n) + '건 · ' + man(s.ha) + '㏊</span><span class="bar2"><span style="width:' + (s.n / mx * 100).toFixed(1) + '%"></span></span></li>';
        }).join('') + '</ol></section>';
        var us = Object.keys(AQ.units).sort(function (a, b) { return AQ.units[b].n - AQ.units[a].n; }).slice(0, 8);
        h += topList('면허 많은 시군', '건', us, function (u) { return AQ.units[u].n; });
      } else {
        h += '<section class="sec"><h1 class="place">전국 ' + esc(SP.k) + ' 양식<small>' + esc(SP.g) + ' · ' + Object.keys(SP.units).length + '개 시군</small></h1>';
        h += '<div class="nums"><div><b>' + man(SP.n) + '<i>건</i></b><span>면허</span></div><div><b>' + man(SP.ha) + '<i>㏊</i></b><span>면적</span></div></div>';
        h += '<p class="chg">전체 양식 면허의 ' + Math.round(SP.n / tn * 100) + '%</p></section>';
        h += seaBoard('오늘 ' + SP.k + ' 위판 시세');
        var us2 = Object.keys(SP.units).sort(function (a, b) { return SP.units[b][0] - SP.units[a][0]; }).slice(0, 8);
        h += topList(SP.k + ' 많은 시군', '건', us2, function (u) { return SP.units[u][0]; });
      }
      h += linksBlock();
    }
    h += '<section class="sec"><p class="src">자료: ' + esc(AQ.source) + '. 어촌계 구역(마을어업)과 정치망은 따로 셉니다. 위판장은 수협 지구별 조합 기준이며 위치는 시군 중심 근사입니다.</p></section>';
    return h;
  }
  function zonePanel() {
    var z = S.zone, st = ZONE[z.k] || ZONE.Y;
    var h = '<button type="button" class="back" id="backBtn">‹ ' + (S.sel ? esc(unitName(S.sel)) : '전국') + ' 보기</button>';
    h += '<section class="sec"><h1 class="place">' + esc(st[1]) + '<small>' + esc(z.a || '') + '</small></h1><dl class="facts">';
    if (z.f) h += '<dt>품종</dt><dd>' + esc(z.f) + '</dd>';
    if (z.ha) h += '<dt>면적</dt><dd>' + esc(z.ha) + '㏊</dd>';
    if (z.e) h += '<dt>만료</dt><dd>' + esc(z.e) + '</dd>';
    h += '<dt>종류</dt><dd><i class="swk" style="background:' + st[0] + '"></i>' + esc(st[1]) + '</dd></dl>';
    h += '<p class="read small">면허권자(어촌계·개인) 이름은 싣지 않습니다. 면허 번호별 상세는 해당 시군 해양수산과에서 확인할 수 있습니다.</p></section>';
    return h;
  }

  /* ── 판: 농장 */
  function cropBoard(title) {
    return '<section class="sec"><p class="eyebrow"><span>' + esc(title || '오늘 도매시장 경락가') + ' <span class="tag mute">연동 전</span></span></p><p class="board-note" style="margin:0">농산물 경락가는 농림축산식품부 농넷(도매시장 통합홈페이지) 연동창구를 붙이면 품목·등급별로 들어옵니다. <a href="price/index.html">경락가 조회 화면 →</a></p></section>';
  }
  function kindChips(items, unitList) {
    return '<div class="chips">' + items.map(function (it) {
      var k = (unitList.filter(function (x) { return x.name.indexOf(it) >= 0; })[0] || {}).kind || '가공·기타';
      return '<button type="button" class="chipk" data-sp="' + esc(it) + '"><i style="background:' + KIND[k] + '"></i>' + esc(it) + '</button>';
    }).join('') + '</div>';
  }
  function cropPanel() {
    var h = '';
    if (S.sel) {
      var c = CR.units[S.sel];
      h += backBtn();
      if (!c) h += '<section class="sec"><h1 class="place">' + esc(unitFull(S.sel)) + '<small>농장</small></h1><p class="read">이 시군에는 아직 지리적표시로 등록된 품목이 없습니다. 재배면적·농가 수 자료가 들어오면 주력 작물을 보여 드립니다.</p></section>';
      else {
        h += '<section class="sec"><h1 class="place">' + esc(unitFull(S.sel)) + '<small>대표 판매 품목 · 지리적표시 ' + c.n + '건</small></h1>';
        h += kindChips(c.items, c.list);
        h += '<p class="read">' + esc(unitName(S.sel)) + ' 하면 ' + c.items.slice(0, 3).join(', ') + '. 등록 품목을 누르면 같은 품목을 가진 다른 시군이 지도에 보입니다.</p></section>';
        h += '<section class="sec"><p class="eyebrow"><span>등록 내역</span><span>등록일</span></p><ul class="reg">' + c.list.map(function (x) { return '<li><span><i style="background:' + KIND[x.kind] + '"></i>' + esc(x.name) + ' <small>' + esc(x.cat) + '</small></span><span class="dt">' + esc(x.date.slice(0, 7).replace('-', '.')) + '</span></li>'; }).join('') + '</ul></section>';
      }
      var ms = PL.markets.filter(function (m) { return m.u === S.sel; });
      if (ms.length) h += '<section class="sec"><p class="eyebrow"><span>이 시군 공영도매시장</span></p><ul class="plain">' + ms.map(function (m) { return '<li><button type="button" class="lnk" data-pin="' + m.id + '">' + esc(m.name) + '</button> <span class="tag mute">위치 근사</span></li>'; }).join('') + '</ul></section>';
      h += cropBoard();
      h += otherModes(S.sel);
    } else {
      if (SP.all) {
        var cnt = {}; CR.items.forEach(function (it) { if (!it.off) cnt[it.kind] = (cnt[it.kind] || 0) + 1; });
        h += '<section class="sec"><h1 class="place">전국 대표 판매 품목<small>지리적표시 ' + CR.items.filter(function (i) { return !i.off; }).length + '건 · ' + Object.keys(CR.units).length + '개 시군</small></h1>';
        h += '<div class="cats big">' + CR.kinds.map(function (k) { return '<span><i style="background:' + KIND[k] + '"></i>' + esc(k) + ' <b>' + (cnt[k] || 0) + '</b></span>'; }).join('') + '</div>';
        h += '<p class="read">시군을 누르면 그곳의 대표 품목과 등록 내역이 나옵니다. 재배면적·농가 수는 농업경영체 통계가 들어오는 대로 함께 보여 드립니다.</p></section>';
        h += cropBoard();
        var us = Object.keys(CR.units).sort(function (a, b) { return CR.units[b].n - CR.units[a].n; }).slice(0, 8);
        h += topList('등록 품목 많은 시군', '건', us, function (u) { return CR.units[u].n; });
      } else {
        var us2 = unitKeys();
        h += '<section class="sec"><h1 class="place">' + esc(SP.k) + '<small>' + esc(SP.kind) + ' · 지리적표시 ' + us2.length + '개 시군</small></h1>';
        h += '<p class="read">' + esc(SP.k) + ' 지리적표시를 가진 시군: ' + us2.map(unitFull).join(', ') + '</p></section>';
        h += cropBoard('오늘 ' + SP.k + ' 도매시장 경락가');
        h += '<section class="sec"><ol class="top">' + us2.map(function (u, i) { return '<li data-u="' + esc(u) + '" tabindex="0"><span class="no">' + (i + 1) + '</span><span class="nm">' + esc(unitFull(u)) + '</span><span class="v">' + esc(CR.units[u].list.filter(function (x) { return x.name.indexOf(SP.k) >= 0; }).map(function (x) { return x.name; }).join(', ')) + '</span></li>'; }).join('') + '</ol></section>';
      }
      h += linksBlock();
    }
    h += '<section class="sec"><p class="src">자료: ' + esc(CR.source) + ' 가공품(고춧가루·곶감 등)은 원재료 품목으로 묶었습니다.</p></section>';
    return h;
  }

  /* ── 판: 핀 */
  function pinPanel() {
    var m = pinById(S.pin);
    var h = backBtn() + '<section class="sec"><h1 class="place">' + esc(m.name) + '<small>' + esc(m.type + ' · ' + m.sido + ' ' + m.sigun) + '</small></h1><dl class="facts">';
    if (m.day) h += '<dt>경매</dt><dd>' + esc(m.day) + '</dd>';
    if (m.note) h += '<dt>참고</dt><dd>' + esc(m.note) + '</dd>';
    if (m.phone) h += '<dt>전화</dt><dd><a href="tel:' + esc(m.phone) + '">' + esc(m.phone) + '</a></dd>';
    h += '<dt>확인</dt><dd>' + (m.verified ? '주소·전화 대조함' : '<span class="tag mute">위치 근사</span> 확인 전') + '</dd></dl>';
    h += '<div class="btns"><a class="btn prime" href="' + kakaoLink(m.name) + '" target="_blank" rel="noopener">카카오맵에서 길찾기</a>' + (m.phone ? '<a class="btn" href="tel:' + esc(m.phone) + '">전화하기</a>' : '') + '</div></section>';
    if (m.type === '공판장') {
      var ab = PR && PR.abattoir && PR.abattoir.cattle ? Object.keys(PR.abattoir.cattle).filter(function (k) { return m.name.indexOf(k.split(' ')[1] || k) >= 0 || m.name.indexOf(k.replace(/\(.*\)/, '').trim()) >= 0; })[0] : null;
      if (ab) {
        var g = PR.abattoir.cattle[ab];
        h += '<section class="sec sec-board"><p class="eyebrow"><span>' + esc(PR.abattoir.date) + ' 이 공판장 한우 거세 경락가</span><span>원/kg</span></p><div class="board" style="--cols:' + Object.keys(g).length + '">' + Object.keys(g).map(function (k) { return '<div><span class="g">' + esc(k) + '</span><span class="p">' + g[k].toLocaleString('ko-KR') + '</span></div>'; }).join('') + '</div></section>';
      } else h += board('소').replace('오늘 한우 거세 경락가', '오늘 이 공판장 한우 경락가');
    }
    else if (m.type === '위판장') h += seaBoard('오늘 이 위판장 시세');
    else if (m.type === '도매시장') h += cropBoard('오늘 이 도매시장 경락가');
    var srcs = { '공판장': '위치: 박씨네 정리본(공판장 13곳). 전화·주소 대조한 곳은 「대조함」으로 표시.', '가축시장': '가축시장 장날·위치는 공공 연동창구가 없어 직접 확인해 채우는 중입니다.',
      '위판장': '위판장은 수협 지구별 조합 기준 63곳. 공공 좌표가 없어 시군 중심에 두었고, 산지위판장 현황 자료의 주소로 바꿀 예정입니다.', '도매시장': '공영도매시장 32곳. 좌표는 근사(1~2㎞)이며 주소 대조 뒤 확정합니다.' };
    h += '<section class="sec"><p class="src">' + esc(srcs[m.type] || '') + '</p></section>';
    return h;
  }
  function otherModes(u) {
    var a = [], e = AQ.units[u], c = CR.units[u];
    if (S.mode !== 'ani') { var ls = LS.species.filter(function (s) { return s.d[u] && s.d[u].y[s.d[u].y.length - 1] && s.d[u].y[s.d[u].y.length - 1][1] > 0; }).sort(function (x, y) { return y.d[u].y[y.d[u].y.length - 1][1] - x.d[u].y[x.d[u].y.length - 1][1]; }).slice(0, 3); if (ls.length) a.push('<button type="button" class="lnk" data-mode="ani">동물농장</button> ' + ls.map(function (s) { return s.k + ' ' + man(s.d[u].y[s.d[u].y.length - 1][1]) + s.w; }).join(', ')); }
    if (S.mode !== 'sea' && e) a.push('<button type="button" class="lnk" data-mode="sea">어장</button> 양식 면허 ' + man(e.n) + '건 · ' + e.top.slice(0, 2).map(function (t) { return t[0]; }).join(', '));
    if (S.mode !== 'crop' && c) a.push('<button type="button" class="lnk" data-mode="crop">농장</button> 대표 품목 ' + c.items.slice(0, 3).join(', '));
    if (!a.length) return '';
    return '<section class="sec"><p class="eyebrow"><span>같은 시군, 다른 보기</span></p><ul class="plain">' + a.map(function (x) { return '<li>' + x + '</li>'; }).join('') + '</ul></section>';
  }
  function backBtn() { return '<button type="button" class="back" id="backBtn">‹ 전국 보기</button>'; }

  function renderPanel() {
    var h = S.pin ? pinPanel() : S.mode === 'ani' ? aniPanel() : S.mode === 'sea' ? seaPanel() : cropPanel();
    var el = $('#panelIn'); el.innerHTML = h;
    var bb = $('#backBtn'); if (bb) bb.addEventListener('click', function () { if (S.zone) { S.zone = null; renderPanel(); drawZones(); } else clearSel(); });
    el.querySelectorAll('.top li[data-u]').forEach(function (li) {
      var go = function () { selectUnit(li.getAttribute('data-u'), true); };
      li.addEventListener('click', go); li.addEventListener('keydown', function (e) { if (e.key === 'Enter') go(); });
    });
    el.querySelectorAll('[data-sp]').forEach(function (b) {
      var go = function () { setSpecies(b.getAttribute('data-sp')); if (S.sel && S.mode === 'crop') clearSel(); };
      b.addEventListener('click', go); b.addEventListener('keydown', function (e) { if (e.key === 'Enter') go(); });
    });
    el.querySelectorAll('[data-pin]').forEach(function (b) { b.addEventListener('click', function () { selectPin(b.getAttribute('data-pin')); }); });
    el.querySelectorAll('[data-mode]').forEach(function (b) { b.addEventListener('click', function () { var u = S.sel; setMode(b.getAttribute('data-mode')); if (u) selectUnit(u, false); }); });
    $('#panel').scrollTop = 0;
  }

  /* ── 고르기 */
  function selectUnit(u, fly) {
    S.pin = null; S.zone = null; S.sel = u; restyle(); drawPins(); renderPanel();
    if (fly && UNITS[u]) map.flyToBounds(UNITS[u].getBounds(), { padding: MOB.matches ? [40, 40] : [60, 60], maxZoom: 9, duration: 0.6 });
    if (MOB.matches) $('#panel').classList.add('open');
  }
  function selectPin(id) {
    var m = pinById(id); if (!m) return;
    S.sel = null; S.zone = null; S.pin = id; restyle(); drawPins(); renderPanel();
    map.flyTo([m.lat, m.lng], Math.max(map.getZoom(), 9), { duration: 0.6 });
    if (MOB.matches) $('#panel').classList.add('open');
  }
  function selectZone(z) { S.zone = z; S.pin = null; renderPanel(); drawZones(); if (MOB.matches) $('#panel').classList.add('open'); }
  function clearSel() { S.sel = null; S.pin = null; S.zone = null; restyle(); drawPins(); renderPanel(); }

  function speciesList() {
    if (S.mode === 'ani') return LS.species;
    if (S.mode === 'sea') return [ALL_SEA].concat(AQ.species);
    return cropItems();
  }
  var _ci;
  function cropItems() {
    if (_ci) return _ci;
    var seen = {}, out = [{ k: '모든 품목', all: true, kind: '' }];
    CR.items.forEach(function (it) { if (it.off || it.units[0] === '전국') return; if (!seen[it.item]) { seen[it.item] = { k: it.item, kind: it.kind, n: 0 }; out.push(seen[it.item]); } seen[it.item].n += 1; });
    return (_ci = out);
  }
  function findSpecies(k) { return speciesList().filter(function (s) { return s.k === k; })[0]; }
  function setSpecies(k) {
    var s = findSpecies(k); if (!s) return;
    SP = s; S.sp = k;
    $('#pickName').textContent = k;
    computeBreaks(); restyle(); drawLabels(); drawLegend(); renderPanel();
  }
  function openPick() {
    var h = '';
    $('#pickTitle').textContent = mode().pickTitle;
    if (S.mode === 'ani') {
      ['소', '돼지', '닭', '오리', '기타'].forEach(function (g) {
        var list = LS.species.filter(function (s) { return s.g === g && s.tot[s.tot.length - 1][0] > 0; });
        if (!list.length) return;
        h += '<h3 class="pick-g">' + g + '</h3><div class="pick-grid">' + list.map(function (s) {
          var t = s.tot[s.tot.length - 1];
          return spBtn(s.k, man(t[0]) + '호 · ' + man(t[1]) + s.w);
        }).join('') + '</div>';
      });
    } else if (S.mode === 'sea') {
      var tot = 0; Object.keys(AQ.units).forEach(function (u) { tot += AQ.units[u].n; });
      h += '<div class="pick-grid">' + spBtn(ALL_SEA.k, tot.toLocaleString('ko-KR') + '건 · 모든 품종') + '</div>';
      ['해조류', '패류', '어류', '기타'].forEach(function (g) {
        var list = AQ.species.filter(function (s) { return s.g === g && s.n >= 5; });
        if (!list.length) return;
        h += '<h3 class="pick-g">' + g + '</h3><div class="pick-grid">' + list.map(function (s) { return spBtn(s.k, man(s.n) + '건 · ' + man(s.ha) + '㏊'); }).join('') + '</div>';
      });
    } else {
      var items = cropItems();
      h += '<div class="pick-grid">' + spBtn(items[0].k, '시군별 대표 갈래로 칠함') + '</div>';
      CR.kinds.forEach(function (g) {
        var list = items.filter(function (s) { return s.kind === g; }).sort(function (a, b) { return b.n - a.n; });
        if (!list.length) return;
        h += '<h3 class="pick-g"><i class="swk" style="background:' + KIND[g] + '"></i>' + g + '</h3><div class="pick-grid">' + list.map(function (s) { return spBtn(s.k, s.n + '곳 등록'); }).join('') + '</div>';
      });
    }
    $('#pickBody').innerHTML = h;
    $('#pickSheet').hidden = false; $('#pickDim').hidden = false;
    $('#pickBody').querySelectorAll('.sp').forEach(function (b) { b.addEventListener('click', function () { setSpecies(b.getAttribute('data-k')); if (S.mode === 'crop' && S.sel) clearSel(); closePick(); }); });
    var cur = $('#pickBody .sp[aria-current="true"]'); (cur || $('#pickClose')).focus();
  }
  function spBtn(k, sub) { return '<button type="button" class="sp" data-k="' + esc(k) + '"' + (k === S.sp ? ' aria-current="true"' : '') + '><b>' + esc(k) + '</b><span>' + esc(sub) + '</span></button>'; }
  function closePick() { $('#pickSheet').hidden = true; $('#pickDim').hidden = true; $('#pickBtn').focus(); }

  /* ── 보기(모드) 바꾸기 */
  function drawSeg() {
    $('#seg').innerHTML = mode().measures.map(function (m) { return '<button type="button" role="radio" data-m="' + m[0] + '" aria-checked="' + (S.m === m[0]) + '">' + m[1] + '</button>'; }).join('');
    $('#seg').querySelectorAll('button').forEach(function (b) {
      b.addEventListener('click', function () {
        S.m = b.getAttribute('data-m');
        $('#seg').querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-checked', x === b); });
        computeBreaks(); restyle(); drawLabels(); drawLegend();
      });
    });
  }
  function setMode(k, keep) {
    if (!MODES[k]) return;
    S.mode = k;
    document.querySelectorAll('#modes [data-mode]').forEach(function (b) { b.setAttribute('aria-selected', b.getAttribute('data-mode') === k); });
    document.body.setAttribute('data-mode', k);
    if (!keep) { S.sel = null; S.pin = null; S.zone = null; }
    var ms = mode().measures.map(function (m) { return m[0]; }); if (!keep || ms.indexOf(S.m) < 0) S.m = ms.indexOf(S.m) >= 0 && keep ? S.m : ms[0];
    var first = speciesList()[0]; SP = findSpecies(S.sp) || first; S.sp = SP.k; $('#pickName').textContent = S.sp;
    drawSeg(); computeBreaks(); restyle(); drawLabels(); drawPins(); drawZones(); drawBiz(); drawLayers(); drawLegend(); hint(); renderPanel();
    document.title = '박씨네 ' + mode().name + ' — ' + S.sp + ' 지도';
  }

  /* ── 찾기 */
  function initFind() {
    var inp = $('#findInput'), list = $('#findList'), items = [];
    function show() {
      var q = inp.value.trim().replace(/\s/g, '');
      if (!q) { list.hidden = true; return; }
      items = Object.keys(UNITS).filter(function (u) { return u.replace('|', '').indexOf(q) >= 0; }).slice(0, 8);
      var ps = allPins().filter(function (p) { return p.name.replace(/\s/g, '').indexOf(q) >= 0; }).slice(0, 4);
      if (!items.length && !ps.length) { list.innerHTML = '<li aria-disabled="true">맞는 시군·시장이 없습니다</li>'; list.hidden = false; return; }
      list.innerHTML = items.map(function (u, i) { return '<li role="option" data-u="' + esc(u) + '"' + (i === 0 ? ' aria-selected="true"' : '') + '><span>' + esc(unitFull(u)) + '</span><small>' + esc(valText(u)) + '</small></li>'; }).join('') +
        ps.map(function (p) { return '<li role="option" data-pin="' + p.id + '"><span>' + esc(p.name) + '</span><small>' + esc(p.type) + '</small></li>'; }).join('');
      list.hidden = false;
      list.querySelectorAll('li[data-u]').forEach(function (li) { li.addEventListener('mousedown', function (e) { e.preventDefault(); pick(li.getAttribute('data-u')); }); });
      list.querySelectorAll('li[data-pin]').forEach(function (li) { li.addEventListener('mousedown', function (e) { e.preventDefault(); inp.value = ''; list.hidden = true; inp.blur(); var p = pinById(li.getAttribute('data-pin')); var md = p.type === '위판장' ? 'sea' : p.type === '도매시장' ? 'crop' : 'ani'; if (md !== S.mode) setMode(md); selectPin(p.id); }); });
    }
    function pick(u) { inp.value = ''; list.hidden = true; inp.blur(); selectUnit(u, true); }
    inp.addEventListener('input', show);
    inp.addEventListener('keydown', function (e) { if (e.key === 'Enter' && items[0]) pick(items[0]); if (e.key === 'Escape') { inp.value = ''; list.hidden = true; inp.blur(); } });
    inp.addEventListener('blur', function () { setTimeout(function () { list.hidden = true; }, 120); });
  }

  /* ── 시작 */
  function get(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); }
  function opt(u) { return fetch(u).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); }
  Promise.all([get('data/livestock.json'), get('data/units.json'), get('data/markets.json'), get('data/aqua.json'), get('data/crops.json'), get('data/places.json'), opt('data/price/latest.json'), opt('data/biz/index.json'), opt('data/price/abattoir.json')])
    .then(function (res) {
      LS = res[0]; TOPO = res[1]; MK = res[2]; AQ = res[3]; CR = res[4]; PL = res[5]; YEARS = LS.years;
      PR = res[6]; BIZ = res[7]; if (PR && res[8]) PR.abattoir = res[8];
      FEAT = topojson.feature(TOPO, TOPO.objects.units);
      var q = new URLSearchParams(location.search);
      S.mode = MODES[q.get('mode')] ? q.get('mode') : 'ani';
      SP = speciesList()[0]; S.sp = SP.k;
      if (q.get('sp') && findSpecies(q.get('sp'))) { SP = findSpecies(q.get('sp')); S.sp = SP.k; }
      S.m = q.get('m') || MODES[S.mode].measures[0][0];
      initMap(); initFind();
      setMode(S.mode, true);
      if (q.get('u') && UNITS[q.get('u')]) selectUnit(q.get('u'), true);
      if (q.get('pin')) selectPin(q.get('pin'));
      if (q.get('z')) map.setView(q.get('z').split(',').slice(0, 2).map(Number), Number(q.get('z').split(',')[2] || 11));
      if (q.get('open') && MOB.matches) $('#panel').classList.add('open');
      if (q.get('pick')) openPick();
    })
    .catch(function (e) { $('#panelIn').innerHTML = '<p class="read">자료를 불러오지 못했습니다. 새로 고침해 주세요.</p>'; console.error(e); });

  document.querySelectorAll('#modes [data-mode]').forEach(function (b) { b.addEventListener('click', function () { if (LS) setMode(b.getAttribute('data-mode')); }); });
  $('#pickBtn').addEventListener('click', openPick);
  $('#pickClose').addEventListener('click', closePick);
  $('#pickDim').addEventListener('click', closePick);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !$('#pickSheet').hidden) closePick(); });
  $('#grip').addEventListener('click', function () { $('#panel').classList.toggle('open'); });
})();
