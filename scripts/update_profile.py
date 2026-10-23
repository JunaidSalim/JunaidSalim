"""Render public GitHub activity and language graphics using only the stdlib."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import urllib.request

USER = 'JunaidSalim'
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets'
FONT = 'Segoe UI,Arial,sans-serif'
COLORS = ['#80e1b4', '#7cb8ff', '#b8a0f3', '#f1c879', '#768a91']


def fetch(url: str, api: bool = False):
    headers = {'User-Agent': 'JunaidSalim-profile', 'Accept': 'application/vnd.github+json' if api else 'text/html'}
    token = os.environ.get('GITHUB_TOKEN')
    if api and token:
        headers['Authorization'] = f'Bearer {token}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=40) as response:
        data = response.read().decode('utf-8')
    return json.loads(data) if api else data


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
        self.tooltips = {}
        self.tooltip_id = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td' and 'data-date' in attrs:
            self.days[attrs['id']] = attrs['data-date']
        if tag == 'tool-tip':
            self.tooltip_id = attrs.get('for')
            self.tooltips[self.tooltip_id] = ''

    def handle_data(self, value):
        if self.tooltip_id:
            self.tooltips[self.tooltip_id] += value

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.tooltip_id = None

    def counts(self):
        result = {}
        for ident, day in self.days.items():
            text = self.tooltips.get(ident, '').strip()
            if text.startswith('No contributions'):
                result[day] = 0
            else:
                count = re.match(r'([\d,]+) contributions?\b', text)
                if not count:
                    raise ValueError(f'Unrecognized public calendar value on {day}: {text[:100]}')
                result[day] = int(count[1].replace(',', ''))
        if len(result) < 300:
            raise ValueError('Incomplete contribution calendar; retaining previous graphics.')
        return result


def txt(x, y, value, size=16, color='#b2c3c9', weight=400, anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>'


def svg(width, height, title, content):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title"><title id="title">{escape(title)}</title><rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="20" fill="#101d23" stroke="#2a3b43"/>{content}</svg>'''


def rhythm(data, mobile=False):
    width, height = (460, 390) if mobile else (840, 300)
    pad = 26 if mobile else 32
    c = txt(pad, 38, 'BUILD RHYTHM', 14, '#80e1b4', 600)
    c += txt(pad, 69, '12 weeks of GitHub activity', 22 if mobile else 25, '#eef6f6', 600)
    metrics = [(data['total'], 'contributions'), (data['active_days'], 'active days'), (data['peak'], 'most in one day')]
    if mobile:
        for i, (value, label) in enumerate(metrics):
            x = pad + i * 139
            c += txt(x, 117, value, 31, '#eef6f6', 600) + txt(x, 140, label, 13)
        x0, y0, w, h = pad, 178, width-pad*2, 151
    else:
        for i, (value, label) in enumerate(metrics):
            x = pad + i * 173
            c += txt(x, 116, value, 31, '#eef6f6', 600) + txt(x, 138, label, 14)
        x0, y0, w, h = pad, 169, width-pad*2, 77
        c += txt(width-pad, 37, 'PUBLIC CONTRIBUTION CALENDAR', 11, '#90a8af', anchor='end')
    for n in range(3):
        y = y0 + h*n/2
        c += f'<path d="M{x0} {y}h{w}" stroke="#2a3b43" stroke-dasharray="3 6"/>'
    weekly = data['weekly']
    maximum = max(max(weekly), 1)
    step = w / 12
    for i, count in enumerate(weekly):
        bar_h = max(3, count/maximum*(h-4))
        x, y = x0+i*step+5, y0+h-bar_h
        c += f'<rect x="{x:.1f}" y="{y:.1f}" width="{step-10:.1f}" height="{bar_h:.1f}" rx="4" fill="{COLORS[0] if count else "#2a3b43"}" opacity="{.5+i*.043:.2f}"><title>{count} contributions in week {i+1}</title></rect>'
    c += txt(pad, height-24, data['start_label'], 13)
    c += txt(width-pad, height-24, data['end_label'], 13, anchor='end')
    return svg(width, height, f"{data['total']} GitHub contributions on {data['active_days']} active days over 12 weeks. Weekly contribution bars.", c)


def code_mix(data, mobile=False):
    width, height = (460, 350) if mobile else (840, 280)
    pad = 26 if mobile else 32
    c = txt(pad, 38, 'CODE FINGERPRINT', 14, '#80e1b4', 600)
    c += txt(pad, 70, 'The shape of my public code', 22 if mobile else 25, '#eef6f6', 600)
    c += txt(pad, 97, f"Across {data['repository_count']} owned, non-fork repositories", 14)
    cx, cy, radius = (121, 202, 65) if mobile else (697, 143, 71)
    circumference = 2*math.pi*radius
    c += f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#273943" stroke-width="23"/>'
    offset = 0
    for i, item in enumerate(data['languages']):
        length = item['share']*circumference
        c += f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{COLORS[i]}" stroke-width="23" stroke-dasharray="{max(0,length-3):.2f} {circumference:.2f}" stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        offset += length
    c += txt(cx, cy-2, len(data['languages_all']), 28, '#eef6f6', 600, 'middle')
    c += txt(cx, cy+23, 'languages', 13, anchor='middle')
    for i, item in enumerate(data['languages']):
        if mobile:
            x, y = 225, 144+i*34
            percent_x = width-pad
        else:
            x, y = pad+(i%2)*242, 145+(i//2)*33
            percent_x = x+192
        c += f'<circle cx="{x+5}" cy="{y-5}" r="4" fill="{COLORS[i]}"/>'
        c += txt(x+20, y, ('Notebooks' if item['name']=='Jupyter Notebook' else item['name']), 15 if mobile else 16, '#e2ecee')
        c += txt(percent_x, y, f"{item['share']*100:.1f}%", 14, anchor='end')
    c += txt(pad, height-25, 'Language mix by bytes, not a proficiency rating.', 13)
    return svg(width, height, 'Public repository language distribution by code bytes: '+', '.join(f"{x['name']} {x['share']*100:.1f} percent" for x in data['languages']), c)


def main():
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        query = 'query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'
        request = urllib.request.Request(
            'https://api.github.com/graphql',
            data=json.dumps({'query': query, 'variables': {'login': USER}}).encode(),
            headers={'User-Agent': 'JunaidSalim-profile', 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            payload = json.load(response)
        if payload.get('errors'):
            raise ValueError('GitHub could not return the contribution calendar; retaining previous graphics.')
        weeks = payload['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
        counts = {day['date']: day['contributionCount'] for week in weeks for day in week['contributionDays']}
        if len(counts) < 300:
            raise ValueError('Incomplete GitHub contribution calendar.')
    else:
        calendar = Calendar()
        calendar.feed(fetch(f'https://github.com/users/{USER}/contributions'))
        counts = calendar.counts()
    # The most recent date actually returned by GitHub avoids inventing future days.
    end = min(datetime.now(timezone.utc).date(), max(date.fromisoformat(d) for d in counts))
    start = end-timedelta(days=83)
    days = [(start+timedelta(days=i)).isoformat() for i in range(84)]
    if any(d not in counts for d in days):
        raise ValueError('Calendar is missing dates in the 12-week period.')
    repos, page = [], 1
    while True:
        batch = fetch(f'https://api.github.com/users/{USER}/repos?per_page=100&page={page}', api=True)
        repos.extend(batch)
        if len(batch)<100:
            break
        page += 1
    repos = [r for r in repos if not r['fork'] and not r['private'] and r['owner']['login'].lower()==USER.lower()]
    with ThreadPoolExecutor(max_workers=4) as pool:
        language_sets = list(pool.map(lambda r: fetch(r['languages_url'], api=True), repos))
    languages = Counter()
    for item in language_sets:
        languages.update(item)
    total_bytes = sum(languages.values())
    if not total_bytes:
        raise ValueError('No language data; retaining previous graphics.')
    top = languages.most_common(4)
    other = total_bytes-sum(n for _, n in top)
    parts = top+([('Other', other)] if other else [])
    values = [counts[d] for d in days]
    data = {
        'updated': end.isoformat(), 'source_calendar': f'https://github.com/users/{USER}/contributions',
        'period_start': start.isoformat(), 'period_end': end.isoformat(),
        'start_label': start.strftime('%d %b %Y'), 'end_label': end.strftime('%d %b %Y'),
        'total': sum(values), 'active_days': sum(v>0 for v in values), 'peak': max(values),
        'weekly': [sum(values[i:i+7]) for i in range(0,84,7)], 'repository_count': len(repos),
        'languages_all': dict(languages.most_common()),
        'languages': [{'name': name, 'bytes': n, 'share': n/total_bytes} for name,n in parts],
    }
    # Fetch and validate all source data before replacing any existing graphic.
    OUT.mkdir(exist_ok=True)
    for mobile in (False, True):
        suffix = '-mobile' if mobile else ''
        (OUT/f'activity{suffix}.svg').write_text(rhythm(data,mobile))
        (OUT/f'code-mix{suffix}.svg').write_text(code_mix(data,mobile))
    (OUT/'profile-data.json').write_text(json.dumps(data, indent=2)+'\n')
    print(f"Rendered real public data through {end}: {data['total']} contributions, {data['active_days']} active days, {len(repos)} repositories.")


if __name__ == '__main__':
    main()
