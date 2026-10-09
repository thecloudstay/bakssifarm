import json,csv,io,re
F=json.load(open('raw/livestock_bundle.json'))
topo=json.load(open('site/data/units.json'))
units=set(g['properties']['u'] for g in topo['objects']['units']['geometries'])
YEARS=list(range(2018,2027))
GROUP={'한우':'소','젖소':'소','육우':'소','일반돼지':'돼지','종돈':'돼지','흑돼지':'돼지','미니피그':'돼지','실험용돼지':'돼지','멧돼지':'돼지',
 '육계':'닭','산란계':'닭','토종닭':'닭','육용종계':'닭','산란종계':'닭','산란중추':'닭','백세미':'닭','토종종계':'닭',
 '육용오리':'오리','종오리':'오리','산란오리':'오리','일반오리':'오리'}
ORDER=['한우','젖소','육우','일반돼지','종돈','흑돼지','육계','산란계','토종닭','백세미','육용종계','산란종계','산란중추','토종종계','육용오리','종오리','산란오리','일반오리','염소','사슴','꿀벌','말','면양','산양','메추리','거위','칠면조','오리','타조','꿩','기러기','토끼','관상조','멧돼지','미니피그','실험용돼지']
def binlabel(h,unit):
    h=h.replace('(호수)','').strip()
    h=h.replace('두','@').replace('수','@').replace('군','@')
    m=re.match(r'^(\d+)@ 이상$',h)
    if m: return f'{int(m.group(1)):,}{unit} 이상'
    m=re.match(r'^(\d+)@-(\d+)@ 이상$',h)
    if m:
        a,b=int(m.group(1)),int(m.group(2))
        return f'{a:,}{unit} 미만' if b==0 else f'{b:,}~{a:,}{unit}'
    return h
out=[]; miss=set()
for k,v in F.items():
    if 'txt' not in v or k=='15149185': continue
    name=re.search(r'시군별 (.+?) 사육규모',v['cd']).group(1)
    rows=list(csv.reader(io.StringIO(v['txt'].lstrip('﻿'))))
    hdr=rows[0]
    binh=[hdr[i] for i in range(7,len(hdr),2)]
    uc=re.search(r'\d(두|수|군)',binh[0]).group(1)
    unitword={'두':'두','수':'마리','군':'군'}[uc]
    bins=[binlabel(b,unitword if unitword!='마리' else '마리') for b in binh]
    d={}
    for r in rows[1:]:
        if len(r)<7 or not r[4].strip(): continue
        sd,sg=r[2].strip(),r[3].strip()
        sg=re.sub(r'시 .+구$','시',sg)
        u=f'{sd}|{sg}'
        if u not in units: miss.add(u); continue
        y=int(r[4]);
        if y not in YEARS: continue
        h=int(float(r[5] or 0)); n=int(float(r[6] or 0))
        bb=[(int(float(r[i] or 0)),int(float(r[i+1] or 0))) for i in range(7,len(r)-1,2)]
        e=d.setdefault(u,{'y':{},'b':{}})
        ph,pn=e['y'].get(y,(0,0)); e['y'][y]=(ph+h,pn+n)
        ob=e['b'].get(y)
        e['b'][y]=[(a+c,b2+d2) for (a,b2),(c,d2) in zip(ob,bb)] if ob else bb
    dd={}
    for u,e in d.items():
        dd[u]={'y':[list(e['y'][y]) if y in e['y'] else None for y in YEARS], 'b':[list(x) for x in e['b'].get(YEARS[-1],[])]}
    tot=[ [sum((dd[u]['y'][i] or [0,0])[0] for u in dd), sum((dd[u]['y'][i] or [0,0])[1] for u in dd)] for i in range(len(YEARS))]
    out.append({'k':name,'g':GROUP.get(name,'기타'),'w':unitword,'bins':bins,'tot':tot,'d':dd,'src':k})
out.sort(key=lambda s: ORDER.index(s['k']) if s['k'] in ORDER else 99)
json.dump({'years':YEARS,'species':out,'source':'가축위생방역지원본부 「전국 시군별 사육규모 현황」(공공데이터포털, 공공누리 제1유형), 각 연도 1월 기준'},open('site/data/livestock.json','w'),ensure_ascii=False,separators=(',',':'))
print('miss',miss)
for s in out: print(s['k'],s['g'],s['w'],'units',len(s['d']),'2026',s['tot'][-1],'2018',s['tot'][0],s['bins'])
