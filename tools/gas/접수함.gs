/**
 * 박씨팜 접수함 — 구글 앱스 스크립트 웹앱(해루낚과 같은 방식)
 * 배포: 배포 > 새 배포 > 웹 앱 / 실행: 나 / 액세스: 모든 사용자 → /exec 주소를 저장소 변수 FORM_ENDPOINT 에 넣음
 * 양식(구입가 제보·모집 열기·참여 신청·업체 등록·가격 알림)이 POST 로 들어오면 양식 이름별 시트에 한 줄씩 쌓고,
 * GET ?what=buy|gongu|count 로 집계만 내보냄(연락처·개별 제보는 절대 내보내지 않음)
 */
var SHEET_NAME = '박씨팜 접수';
var MIN_N = 5;   // 구입가 중위값을 여는 최소 제보 수

function ss_() {
  var id = PropertiesService.getScriptProperties().getProperty('SS_ID'); var ss = null;
  if (id) { try { ss = SpreadsheetApp.openById(id); } catch (e) {} }
  if (!ss) { ss = SpreadsheetApp.create(SHEET_NAME); PropertiesService.getScriptProperties().setProperty('SS_ID', ss.getId()); }
  return ss;
}
function sheet_(name) {
  var ss = ss_(); var sh = ss.getSheetByName(name);
  if (!sh) { sh = ss.insertSheet(name); sh.appendRow(['접수시각', '자료']); }
  return sh;
}
function doPost(e) {
  var p = (e && e.parameter) || {};
  var form = String(p['form-name'] || '기타').replace(/[^\w가-힣-]/g, '').slice(0, 40);
  if (p['bot-field']) return out_({ ok: false });
  var data = {}; Object.keys(p).forEach(function (k) { if (k !== 'form-name' && k !== 'bot-field') data[k] = String(p[k]).slice(0, 500); });
  var lock = LockService.getScriptLock(); lock.waitLock(5000);
  try { sheet_(form).appendRow([new Date(), JSON.stringify(data)]); } finally { lock.releaseLock(); }
  return out_({ ok: true });
}
function doGet(e) {
  var what = (e && e.parameter && e.parameter.what) || 'count';
  if (what === 'buy') return out_(buyStats_());
  if (what === 'gongu') return out_(gonguList_());
  return out_(counts_());
}
function rows_(form) {
  var sh = ss_().getSheetByName(form); if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().map(function (r) { var d = {}; try { d = JSON.parse(r[1]); } catch (x) {} d._at = Utilities.formatDate(new Date(r[0]), 'Asia/Seoul', 'yyyy-MM-dd'); return d; });
}
function counts_() {
  var o = {}; ss_().getSheets().forEach(function (sh) { o[sh.getName()] = Math.max(0, sh.getLastRow() - 1); }); return { at: now_(), counts: o };
}
function median_(a) { a = a.slice().sort(function (x, y) { return x - y; }); var m = a.length >> 1; return a.length % 2 ? a[m] : Math.round((a[m - 1] + a[m]) / 2); }
function buyStats_() {
  var g = {};
  rows_('buy-report').forEach(function (d) {
    var price = parseFloat(d['단가']); if (!(price > 0)) return;
    var k = [d['종류'] || '', (d['품목규격'] || '').trim(), d['단위'] || '', d['지역'] || ''].join('|');
    (g[k] = g[k] || []).push({ p: price, at: d._at });
  });
  var items = [];
  Object.keys(g).forEach(function (k) {
    var v = g[k]; if (v.length < MIN_N) return; var f = k.split('|');
    items.push({ kind: f[0], item: f[1], unit: f[2], area: f[3], median: median_(v.map(function (x) { return x.p; })), n: v.length, last: v.map(function (x) { return x.at; }).sort().pop() });
  });
  items.sort(function (a, b) { return b.n - a.n; });
  var n = rows_('buy-report').length;
  return { at: now_(), n: n, items: items };
}
function gonguList_() {
  var opens = rows_('gongu-open'); var joins = rows_('gongu-join'); var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
  var items = opens.map(function (d, i) {
    var id = '공구-' + ('0000' + (i + 1)).slice(-4); var got = 0;
    joins.forEach(function (j) { if ((j['모집번호'] || '').trim() === id) got += parseFloat(j['수량']) || 0; });
    var goal = parseFloat(d['목표수량']) || 0; var due = d['마감일'] || '';
    var st = goal && got >= goal ? '성립' : (due && due < today ? '마감' : '모집 중');
    return { id: id, kind: d['종류'] || '', item: d['품목규격'] || '', area: d['지역'] || '', goal: goal, got: got, due: due, status: st, note: (d['설명'] || '').slice(0, 140), opened: d._at };
  }).filter(function (it) { return it.status !== '마감' || daysAgo_(it.opened) < 60; });
  return { at: now_(), items: items.reverse() };
}
function daysAgo_(s) { return Math.floor((new Date() - new Date(s)) / 86400000); }
function now_() { return Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm'); }
function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
