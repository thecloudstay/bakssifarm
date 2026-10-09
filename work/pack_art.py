# 아티팩트(미리보기)용 묶음: 절대 경로 링크를 상대 경로로, 디렉터리 링크에 index.html 붙임
import os, re, shutil, json
SRC='site'; DST='art'
if os.path.exists(DST): shutil.rmtree(DST)
files = []
for root, dirs, fs in os.walk(SRC):
    if os.path.basename(root) == 'og' or '/og/' in root + '/': continue
    for f in fs:
        p = os.path.join(root, f); rel = os.path.relpath(p, SRC)
        if rel.endswith('.txt') or rel in ('sitemap.xml','rss.xml','robots.txt','404.html'): continue
        out = os.path.join(DST, rel); os.makedirs(os.path.dirname(out), exist_ok=True)
        if rel.endswith('.html') or rel == 'app.js':
            depth = rel.count('/'); pre = '../' * depth if depth else './'
            s = open(p, encoding='utf-8').read()
            if rel.endswith('.html'):
                s = re.sub(r'(href|src|action)="/(?!/)', lambda m: f'{m.group(1)}="{pre}', s)
                s = re.sub(r'(href|action)="([^"#?]*?/)(["#?])', lambda m: f'{m.group(1)}="{m.group(2)}index.html{m.group(3)}', s)
            else:
                s = s.replace('href="price/"', 'href="price/index.html"').replace('href="gongu/"', 'href="gongu/index.html"').replace('href="pro/"', 'href="pro/index.html"')
            open(out, 'w', encoding='utf-8').write(s)
        else: shutil.copy(p, out)
        if rel != 'index.html': files.append(rel)
json.dump([{'path': f} for f in files], open('work/art_list.json', 'w'), ensure_ascii=False)
print(len(files))
