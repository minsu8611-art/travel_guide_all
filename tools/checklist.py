"""index.html의 여행 정보를 '고정'과 '변동'으로 분류해 점검 목록(점검목록.md)을 만든다.

사용법: python3 tools/checklist.py
- 변동 정보는 성격별(입국·비자 / 세금·경보 / 항공·노선 / 요금 / 날짜 의존)로 나눈다.
- 매월 점검 범위: 입국·비자, 세금·경보는 매월 전체 + 지역 4묶음 중 한 묶음(4개월에 한 바퀴).
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'index.html'
OUT = ROOT / '점검목록.md'

# 지역 순환: 월 % 4 → 묶음 번호
REGION_GROUPS = [
    ['일본', '중국·홍콩'],
    ['동남아·대만'],
    ['유럽·아프리카'],
    ['미주·하와이·캐나다·중남미', '호주·뉴질랜드', '남태평양', '중앙아시아·서남아'],
]

MONEY = (r'\d[\d,.~]*\s*(원|만원|엔|위안|바트|동|페소|링깃|루피아|루피|달러|유로|파운드|코루나|포린트|라리|킵)'
         r'|[$€£¥₩]\s?\d'
         r'|\b(USD|AUD|NZD|CAD|JOD|HKD|TWD|SGD|THB|MYR|IDR|CHF|EUR|GBP|JPY|AED|MOP|NT\$|RM)\s?\$?\d'
         r'|\d\s?(USD|AUD|NZD|CAD|JOD|HKD|TWD|SGD|THB|MYR|IDR|CHF|EUR|GBP|JPY|AED|MOP)\b')
CATEGORIES = [
    # (이름, 정규식, 점검 주기)
    ('입국·비자', r'무비자|비자|ESTA|eTA|\bETA\b|NZeTA|ETIAS|EES|MDAC|TDAC|eTravel|G-CNMI|입국카드|여권 유효', '매월'),
    ('세금·경보', r'관광세|출국세|방문세|숙박세|환경세|그린세|입산료|여행경보|여행금지|출국권고', '매월'),
    ('항공·노선', r'직항|취항|운항|항공사|경유', '지역 순환'),
    ('요금', MONEY + r'|요금|입장료|입장 무료|환율', '지역 순환'),
    ('날짜 의존', r'20\d\d[.년]', '지역 순환'),
]


def load():
    data = {}
    for line in HTML.read_text(encoding='utf-8').split('\n'):
        for n in ('C', 'R', 'COM', 'EX'):
            if line.startswith(f'const {n}={{'):
                data[n] = json.loads(line[len(f'const {n}='):-1])
    return data


def rows(data):
    """(지역, 위치, 항목명, 내용) 목록."""
    out = []

    def secs(region, where, sections):
        for title, items in sections:
            for it in items:
                k, v = (it if isinstance(it, list) else ('', it))
                out.append((region, f'{where} › {title}', k, v))
    secs('공통', '공통 준비사항', data['COM']['sections'])
    for r, v in data['R'].items():
        secs(r, f'{r} 지역 안내', v['sections'])
    for city, v in data['C'].items():
        reg = v['region']
        for f, label in (('best', '최적 시기'), ('visa', '비자'), ('flight', '항공')):
            out.append((reg, f'{city} › 기본', label, v[f]))
        secs(reg, city, v['sections'])
        for sec, rs in data['EX'].get(city, {}).items():
            for k, val in rs:
                out.append((reg, f'{city} › {sec}', k, val))
    return out


def classify(text):
    for name, rx, cycle in CATEGORIES:
        if re.search(rx, text):
            return name, cycle
    return None, None


def main():
    data = load()
    allrows = rows(data)
    fixed = 0
    by_cat = defaultdict(list)
    for region, where, k, v in allrows:
        cat, cycle = classify(f'{k} {v}')
        if cat is None:
            fixed += 1
        else:
            by_cat[cat].append((region, where, k, v))
    total = len(allrows)
    vol = total - fixed

    L = ['# 여행 가이드 점검 목록', '',
         '`python3 tools/checklist.py`로 자동 생성되는 파일입니다. 직접 고치지 마세요.', '',
         '## 분류 요약', '',
         '| 구분 | 항목 수 | 점검 주기 |', '|---|---:|---|',
         f'| 고정 정보 (명소 설명·역사·음식·문화 등) | {fixed} | 점검 불필요 |']
    for name, _, cycle in CATEGORIES:
        L.append(f'| 변동 — {name} | {len(by_cat[name])} | {cycle} |')
    L += [f'| **합계** | **{total}** (변동 {vol}) | |', '',
          '## 지역 순환 일정', '',
          '매월 점검 시 `입국·비자`, `세금·경보`는 전체를, 나머지 변동 항목은 아래 묶음 하나만 확인합니다.', '',
          '| 묶음 | 지역 | 점검 월 |', '|---|---|---|']
    for i, g in enumerate(REGION_GROUPS):
        months = ', '.join(f'{m}월' for m in range(1, 13) if m % 4 == i)
        L.append(f'| {i} | {", ".join(g)} | {months} |')
    L += ['', '공통 준비사항(지역 `공통`)은 매월 점검합니다.', '']
    for name, _, cycle in CATEGORIES:
        L += [f'## {name} ({cycle})', '']
        cur = None
        for region, where, k, v in sorted(by_cat[name], key=lambda r: (r[0], r[1])):
            if region != cur:
                L += ['', f'### {region}', '']
                cur = region
            label = f'{k}: ' if k else ''
            L.append(f'- [ ] {where} — {label}{v}')
        L.append('')
    OUT.write_text('\n'.join(L), encoding='utf-8')
    print(f'총 {total}개 항목: 고정 {fixed} / 변동 {vol} → {OUT.name}')


if __name__ == '__main__':
    main()
