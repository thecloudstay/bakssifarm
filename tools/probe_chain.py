"""진단 작업용 사슬: 세계 공개 연동창구 수집 → 세계 요인 감시를 한 번에 돌려 tools/_debug 에 둘 다 기록"""
import runpy, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
for name in ('collect_global.py', 'collect_world.py'):
    print('==', name); sys.argv = [name]
    try: runpy.run_path(os.path.join(HERE, name), run_name='__main__')
    except SystemExit: pass
