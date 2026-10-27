"""Generate docs/housing-audit.html — the public Audit page, DERIVED, never hand-typed.

House discipline: no hand-typed result figures. The two year-by-year series are derived at build time
(ours from live v4 via stage_methods.co_total; the City's from the HCD APR mirror's completion columns),
and every finding is a row of corrections/v4/audit_findings.csv with its evidence. The page states the part
of the gap no finding explains, instead of claiming there is none.

2026-09-30 rewrite: the July page typed its findings and its "remaining gap" as prose ("~150u"), and its
headline read co_completions, which since 2026-09-26 runs past 2025, under a "2018–2025" label.

Run:  .venv/bin/python scripts/v4/build_audit_page.py   (then scripts/site_meta.py injects the head tags)
"""
import glob
import html
import json
import os
import sqlite3
import subprocess
import sys

import pandas as pd

ROOT = os.path.expanduser('~/berkeley-data')
sys.path.insert(0, ROOT)
from scripts.v4 import stage_methods as SM  # noqa: E402

OUT = os.path.join(ROOT, 'docs', 'housing-audit.html')
HCD = os.path.join(ROOT, 'databases', 'hcd_apr_mirror_2026-06-17_fresh.db')
REPO = 'https://github.com/blockXblock/berkeley-housing-analysis/blob/dev/'
YEARS = [str(y) for y in range(2018, 2026)]

BASE = json.load(open(sorted(glob.glob(os.path.join(ROOT, 'data', 'baselines', 'reconciliation_baseline_*.json')))[-1]))
as_of = BASE['as_of']
as_of_date = as_of[:10]   # the baseline id may carry a same-day suffix (2026-09-30b); the page shows the date
findings = pd.read_csv(os.path.join(ROOT, 'corrections', 'v4', 'audit_findings.csv'), dtype=str).fillna('')
n_ledger = len(pd.read_csv(os.path.join(ROOT, 'corrections', 'v4', 'grounded_counts.csv')))

# --- the two series, derived -------------------------------------------------------------------------------
v4 = SM.ro(SM.LIVE)
ours = {y: SM.co_total(v4, y, y) for y in YEARS}
co_cols = [c for (c,) in sqlite3.connect(f'file:{HCD}?mode=ro', uri=True).execute(
    "SELECT name FROM pragma_table_info('table_a2') WHERE name LIKE 'CO\\_%' ESCAPE '\\' AND name <> 'CO_ISSUE_DT1'")]
city = dict(sqlite3.connect(f'file:{HCD}?mode=ro', uri=True).execute(
    f"SELECT YEAR, SUM({'+'.join(f'COALESCE({c},0)' for c in co_cols)}) FROM table_a2 "
    "WHERE upper(JURIS_NAME)='BERKELEY' GROUP BY YEAR").fetchall())
city_years = sorted(y for y, v in city.items() if y)   # the years the City filed project-level rows
city = {y: int(city.get(y, 0) or 0) for y in YEARS}
assert sum(city.values()) == BASE['hard_gated']['city_co_total']['value'], 'City total drifted from the baseline'
tot_ours, tot_city = sum(ours.values()), sum(city.values())
gap = tot_ours - tot_city

# --- what the findings explain -----------------------------------------------------------------------------
findings['eff'] = pd.to_numeric(findings.units_effect_2018_25, errors='coerce').fillna(0).astype(int)
counted = findings[(findings.verified != '') & (findings.eff != 0)]
named = int(counted.eff.sum())
unattributed = gap - named
by_year = counted.groupby('year').eff.sum().to_dict()


def esc(s):
    return html.escape(str(s))


# Files kept out of git (too large) but published in the curriculum bundle on R2.
ON_R2 = {'data/processed/permits_clean.csv': 'https://docs.berkeleybuild.com/curriculum/data/permits_clean.csv'}


def source_link(path):
    """A link only to something that exists: the git-tracked file, its folder for a wildcard, the R2 copy;
    otherwise the path as plain text (a dead link reads as a missing source)."""
    if '*' in path:
        folder = path.rsplit('/', 1)[0]
        return f'<a href="{REPO.replace("/blob/", "/tree/")}{esc(folder)}"><code>{esc(path)}</code></a>'
    if path in ON_R2:
        return f'<a href="{ON_R2[path]}"><code>{esc(path)}</code></a>'
    tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', path], cwd=ROOT, capture_output=True).returncode == 0
    return f'<a href="{REPO}{esc(path)}"><code>{esc(path)}</code></a>' if tracked else f'<code>{esc(path)}</code>'


def evidence(s):
    out = []
    for part in [p.strip() for p in str(s).split(';') if p.strip()]:
        head, _, rest = part.partition(' ')
        if head.startswith('http'):
            label = head.rsplit('/', 1)[-1].replace('%20', ' ')[:48]
            out.append(f'<a href="{esc(head)}">{esc(label)}</a>{(" " + esc(rest)) if rest else ""}')
        elif head.startswith(('docs/', 'corrections/', 'scripts/', 'data/')):
            out.append(f'{source_link(head)}{(" " + esc(rest)) if rest else ""}')
        else:
            out.append(esc(part))
    return '<br>'.join(out)


def rows(df):
    r = []
    for f in df.itertuples():
        eff = f'{f.eff:+,}' if f.eff else '&mdash;'
        badge = '' if f.verified else '<br><span class="fine">carried from July; not re-verified</span>'
        r.append(f'<tr><td><strong>{esc(f.subject)}</strong><br><span class="fine">{esc(f.address)} · {esc(f.year)}</span>{badge}</td>'
                 f'<td class="num">{eff}</td><td>{esc(f.what)}{("<br><span class=fine>" + esc(f.note) + "</span>") if f.note else ""}</td>'
                 f'<td class="ev">{evidence(f.evidence)}</td></tr>')
    return '\n'.join(r)


year_rows = '\n'.join(
    f'<tr><td>{y}</td><td class="num">{ours[y]:,}</td><td class="num">{city[y]:,}</td><td class="num">{ours[y] - city[y]:+,}</td>'
    f'<td class="num">{(format(int(by_year[y]), '+,') if by_year.get(y) else '&mdash;')}</td><td class="num">{ours[y] - city[y] - int(by_year.get(y, 0)):+,}</td></tr>'
    for y in YEARS)
city_side = findings[findings.side.isin(['city_record', 'state_copy'])]
our_side = findings[findings.side == 'our_pipeline']

PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Housing Audit — berkeleybuild.com</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         color: #1a202c; margin: 0; background: #ffffff; line-height: 1.65; }}
  .hero {{ background: linear-gradient(135deg, #1a365d, #2c5282); color: white; padding: 3rem 1.5rem; text-align: center; }}
  .hero h1 {{ margin: 0 0 .5rem; font-size: 2.2rem; }}
  .hero p {{ font-size: 1.15rem; opacity: .92; max-width: 640px; margin: .5rem auto; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 2rem 1rem; }}
  h2 {{ color: #1a365d; margin-top: 2.5rem; border-bottom: 2px solid #e2e8f0; padding-bottom: .3rem; }}
  .scoreboard {{ display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center; margin: 2rem 0; }}
  .score {{ flex: 1 1 140px; background: #f7fafc; border-radius: 10px; padding: 1.2rem; text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,.07); }}
  .score .n {{ font-size: 2.1rem; font-weight: 700; color: #1a365d; font-variant-numeric: tabular-nums; }}
  .score .l {{ font-size: .85rem; color: #4a5568; }}
  .callout {{ background: #fdfaf3; border-left: 4px solid #b08968; border-radius: 0 8px 8px 0; padding: 1rem 1.5rem; margin: 1.5rem 0; }}
  .warn {{ background: #fff5f5; border-left: 4px solid #c53030; }}
  .good {{ background: #f0fff4; border-left: 4px solid #2f855a; }}
  .tablewrap {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .92rem; }}
  th, td {{ border: 1px solid #e2e8f0; padding: .5rem .7rem; text-align: left; vertical-align: top; }}
  th {{ background: #f7fafc; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  td.ev {{ font-size: .82rem; min-width: 12rem; }}
  code {{ background: #edf2f7; padding: .1rem .35rem; border-radius: 4px; font-size: .9em; }}
  .fine {{ color: #718096; font-size: .85rem; }}
  a {{ color: #2b6cb0; overflow-wrap: anywhere; }}
</style>
</head>
<body>
<div class="hero">
  <h1>The Housing Audit</h1>
  <p>We rebuilt Berkeley's housing-completion record from raw public permits, independently of the City's
     official filings, then examined where the two records disagree. This page is what we found, with the
     evidence for each finding.</p>
  <p class="fine">As of {esc(as_of_date)} · <a style="color:#bee3f8" href="index.html">berkeleybuild.com</a></p>
</div>
<div class="container">
<div class="scoreboard">
  <div class="score"><div class="n">{tot_ours:,}</div><div class="l">units completed 2018&ndash;2025<br>our count, from raw permits</div></div>
  <div class="score"><div class="n">{tot_city:,}</div><div class="l">units completed 2018&ndash;2025<br>the City's reports to the state</div></div>
  <div class="score"><div class="n">{gap:+,}</div><div class="l">difference</div></div>
  <div class="score"><div class="n">{named:+,}</div><div class="l">explained by the findings below</div></div>
  <div class="score"><div class="n">{unattributed:+,}</div><div class="l">not yet attributed</div></div>
</div>
<div class="callout {'good' if unattributed == 0 else 'warn'}"><strong>What this page claims.</strong>
Every finding below has its evidence: the City's own reports, permits, plan sets and staff reports.
{'Every unit of difference is attributed.' if unattributed == 0 else
 f'<strong>{unattributed:+,} units of the difference are not yet attributed</strong> to a named building. On 2026-09-26 we re-read every permit under the definition of a housing unit used by the state housing department (HCD), and we have not yet re-examined every row of disagreement since. We show the open number rather than hide it; it shrinks as findings are verified.'}</div>

<h2>Year by year</h2>
<p>Completions counted in each calendar year. The City's figures are its annual reports to the state, as
published in HCD's open data. "Explained" is the sum of the verified findings for that year.</p>
<div class="tablewrap"><table>
<tr><th>Year</th><th class="num">Ours</th><th class="num">City</th><th class="num">Difference</th><th class="num">Explained</th><th class="num">Not yet attributed</th></tr>
{year_rows}
<tr><th>2018&ndash;2025</th><th class="num">{tot_ours:,}</th><th class="num">{tot_city:,}</th><th class="num">{gap:+,}</th><th class="num">{named:+,}</th><th class="num">{unattributed:+,}</th></tr>
</table></div>

<h2>Why the comparison starts in 2018</h2>
<p><strong>Because that is where the City's building-by-building record starts.</strong> We compare against the
City's Annual Progress Reports to the state, and the state's open-data copy holds Berkeley's project-level rows
for {city_years[0]}&ndash;{city_years[-1]}. Each row names a project and the year it was entitled, permitted and
completed. That is what makes a building-by-building comparison possible.</p>
<p><strong>The start date comes from state law.</strong> Two 2017 housing laws, Assembly Bill 879 and Senate Bill 35,
changed what cities must report. The state housing department (HCD) rewrote the report form to match, and its
guidance draws the line at 2018: <em>&ldquo;For the years 2017 and prior, you must use the old version of the
APR.&rdquo;</em> Berkeley's rows in the state's open data begin with 2018, the first year on the new form.
(<a href="https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-instructions.pdf">HCD
report instructions</a>; <a href="https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-faq.pdf">HCD
FAQ</a>.)</p>
<p><strong>Our permit records were requested to match.</strong> The City's permit reports, obtained through
public-records requests, cover permits from 2018 onward.</p>
<p><strong>What did not set the date.</strong> Berkeley's Measure O housing bond and Measure P transfer tax both
passed in 2018, but their money reached projects from 2019 on, so 2018 is simply the year before the new
local money. The current state housing-target cycle (RHNA) starts in mid-2022 and counts building permits, not
completions. Some of our other records reach further back (state tax-credit awards to 1991; we are collecting City
planning records back to 2006), but without the City's project-level filings there is nothing to compare them against.</p>

<h2>What we found in the City's record</h2>
<p>A positive number means the City's record undercounts relative to ours; a negative number means it counts
something we don't. Rows marked "carried from July" come from our earlier audit and are not counted in
"explained" until re-verified under the current definitions.</p>
<div class="tablewrap"><table>
<tr><th>Finding</th><th class="num">Units</th><th>What happened</th><th>Evidence</th></tr>
{rows(city_side)}
</table></div>

<h2>What we found in our own work</h2>
<div class="callout warn"><strong>Independent verification cuts both ways, or it is worthless.</strong>
The audit keeps our mistakes beside the City's, with the fix for each.</div>
<div class="tablewrap"><table>
<tr><th>Finding</th><th class="num">Units</th><th>What happened</th><th>Evidence</th></tr>
{rows(our_side)}
</table></div>

<h2>How to check us</h2>
<p>Every count traces to a primary document: the permit's own text, the building's plan set, the City's staff
reports. The City's report is what we check against, never what we count from. Every correction is a row in a
public ledger ({n_ledger} entries, each with its evidence), every finding is a row in
<a href="{REPO}corrections/v4/audit_findings.csv"><code>audit_findings.csv</code></a>, and every change
appends a new dated baseline; nothing is silently edited. The pipeline rebuilds from the raw permit files:</p>
<p><code>JN-A (ingest) → JN-B (dedup) → JN-C (classify) → JN-F (corrections) → buildings → JN-E (reconcile)</code></p>
<p>The notebooks, ledgers, baselines and audit memos, including our retractions, are in the
<a href="https://github.com/blockXblock/berkeley-housing-analysis">public repository</a>.
<a href="data-science-curriculum.html">The curriculum</a> teaches the method for any city.</p>
<p class="fine">Generated {esc(as_of_date)} (baseline <code>{esc(as_of)}</code>) by <code>scripts/v4/build_audit_page.py</code>: the figures are derived
at build time, not typed.</p>
</div>
</body>
</html>
"""
with open(OUT, 'w') as f:
    f.write(PAGE)
print(f'wrote {OUT}  ours={tot_ours:,} city={tot_city:,} gap={gap:+,} named={named:+,} unattributed={unattributed:+,} as_of={as_of}')
