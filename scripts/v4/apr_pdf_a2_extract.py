"""Table-A2 extractor v2 — GEOMETRY-based (replaces the failed text-stream apr_pdf_a2_extract.py;
its apr_pdf_rows_cy*.csv outputs were WRONG and are overwritten by this script).

Method (per the validated approach):
  * fitz page.get_text('words') + page.rotation_matrix (2019-2021 pages are rot=90; words come
    back in unrotated coords and MUST be rotated).
  * A2 page-run discovery: data pages (>=3 nine-digit APN words) starting at the first page whose
    flat text carries the 'Annual Building Activity Report Summary'+'New Construction' title,
    extending contiguously. Excel-print COLUMN SLICES (2018: 2 slices; 2022: 4) are detected by
    the APN sequence RESTARTING; slices are merged by row index (verified APN-equal).
  * Rows are BANDED between consecutive APN-anchor y-centers (cells are vertically centered, so
    tall multi-line rows in 2023 still band correctly; y-overlap clustering fails there).
  * Columns are mapped PER SLICE from the data itself: date tokens cluster in x; each date
    cluster's units column = the numeric word immediately right of the date (x1 median, numbers
    are right-aligned). Milestone identity (ENT/BP/CO) = nearest deep header keyword
    (Entitlement*/Permits/Occupancy, title row excluded) to the units column. A milestone with an
    anchor but no dates in the slice (2022 ENT slice) gets its units column by the numeric
    x1-cluster nearest the anchor.
  * '#VALUE!' cells -> None. 'Total' summary words cap the last band.

Output: scratch/2026-07-03/apr_pdf_rows_cy{Y}.csv
  (year,row_idx,pages,apn_raw,address,tracking,ent_date,ent_units,bp_date,bp_units,co_date,co_units)
Diagnostics printed per year: pages, slices, cluster->milestone map, row count, ENT/BP/CO sums.
"""
import csv
import os
import re
import statistics
from collections import defaultdict

import fitz

os.chdir(os.path.expanduser('~/berkeley-data'))
OUT_DIR = 'scratch/2026-07-03'

RE_APN9 = re.compile(r'^\d{9}$')
RE_APN3 = re.compile(r'^\d{2,3}[A-Z]?$')
RE_APN_HYph = re.compile(r'^\d{2,3}[A-Z]?-\d{3,4}-\d{2,3}(-\d+)?$')
RE_DATE = re.compile(r'^\d{1,2}/\d{1,2}/\d{2,4}$')
RE_NUM = re.compile(r'^-?[\d,]+$')
RE_TRACK = re.compile(r'^[A-Z]{1,3}\d{4}-\d{3,5}(-[A-Z0-9]+)?$')


def rot_words(pg):
    m = pg.rotation_matrix
    out = []
    for w in pg.get_text('words'):
        r = fitz.Rect(w[:4]) * m
        out.append((r.x0, r.y0, r.x1, r.y1, w[4]))
    return out


def page_flat(pg):
    return ' '.join((pg.get_text() or '').split())


def find_a2_run(doc):
    """Return list of page numbers forming the Table-A2 run."""
    data_pages, title_pages = [], set()
    for i, pg in enumerate(doc):
        flat = page_flat(pg)
        n9 = len(re.findall(r'\b\d{9}\b', flat))
        if n9 >= 3:
            data_pages.append(i)
        if ('Annual Building Activity Report' in flat and 'New Construction' in flat
                and 'Table A2' in flat.replace('Table A2', 'Table A2')):
            title_pages.add(i)
    start = None
    for p in data_pages:
        if p in title_pages:
            start = p
            break
    if start is None:
        return []
    run = [start]
    for p in data_pages:
        if p > start:
            if p == run[-1] + 1:
                run.append(p)
            else:
                break
    return run


def cluster_1d(vals, gap):
    """Cluster sorted scalar values; new cluster when jump > gap. Returns list of lists."""
    if not vals:
        return []
    vals = sorted(vals)
    out = [[vals[0]]]
    for v in vals[1:]:
        if v - out[-1][-1] > gap:
            out.append([v])
        else:
            out[-1].append(v)
    return out


def extract_year(year, verbose=True):
    doc = fitz.open(f'data/raw/city_apr_pdfs/cy{year}_apr_berkeley.pdf')
    run = find_a2_run(doc)
    if not run:
        print(f'cy{year}: NO A2 run found'); return []

    # --- per page: rotated words + APN anchors ---
    page_words, page_anchors = {}, {}
    for p in run:
        tw = rot_words(doc[p])
        page_words[p] = tw
        nine = [w for w in tw if RE_APN9.fullmatch(w[4])]
        # APN column = largest x0 cluster of 9-digit words
        if nine:
            cl = cluster_1d([w[0] for w in nine], 8)
            best = max(cl, key=len)
            lo, hi = min(best) - 3, max(best) + 3
            anchors = sorted([w for w in nine if lo <= w[0] <= hi], key=lambda w: w[1])
        else:
            anchors = []
        page_anchors[p] = anchors

    # --- split run into slices by APN-sequence restart ---
    slices = []  # each: list of page numbers
    first_sig = None
    for p in run:
        an = page_anchors[p]
        sig = tuple(w[4] for w in an[:3])
        if not slices:
            slices.append([p]); first_sig = sig
        elif sig and sig == first_sig:
            slices.append([p])
        else:
            slices[-1].append(p)

    # --- per slice: bands, columns, values ---
    slice_rows = []
    diag = []
    for si, sp in enumerate(slices):
        # header anchors from slice's first page (title row = topmost keyword y; exclude)
        hdr_words = page_words[sp[0]]
        kw = {'ent': [], 'bp': [], 'co': []}
        for w in hdr_words:
            t = w[4]
            if re.match(r'^Entitlement', t):
                kw['ent'].append(w)
            elif t.startswith('Permits'):
                kw['bp'].append(w)
            elif t.startswith('Occupancy') or t.startswith('Certificates'):
                kw['co'].append(w)
        anchors_x = {}
        for k, ws in kw.items():
            if not ws:
                continue
            ymin = min(w[1] for w in sum(kw.values(), []))
            deep = [w for w in ws if w[1] > ymin + 5] or ws
            wbest = max(deep, key=lambda w: w[1])
            anchors_x[k] = (wbest[0] + wbest[2]) / 2

        # bands per page
        bands = []  # (page, ycenter, [words])
        for p in sp:
            an = page_anchors[p]
            if not an:
                continue
            centers = [(w[1] + w[3]) / 2 for w in an]
            gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
            medgap = statistics.median(gaps) if gaps else 10
            # cap page bottom at a 'Total' word below last anchor if present
            bottom_cap = None
            for w in page_words[p]:
                if w[4] in ('Total', 'Totals') and (w[1] + w[3]) / 2 > centers[-1]:
                    yc = (w[1] + w[3]) / 2
                    bottom_cap = yc if bottom_cap is None else min(bottom_cap, yc)
            bounds = []
            for i, c in enumerate(centers):
                top = (centers[i - 1] + c) / 2 if i > 0 else c - (medgap / 2 if len(centers) > 1 else 6)
                bot = (centers[i + 1] + c) / 2 if i < len(centers) - 1 else c + (medgap / 2 if len(centers) > 1 else 6)
                if i == len(centers) - 1 and bottom_cap is not None:
                    bot = min(bot, bottom_cap - 0.2)
                bounds.append((top, bot))
            for (top, bot), aw, c in zip(bounds, an, centers):
                ws = [w for w in page_words[p] if top <= (w[1] + w[3]) / 2 < bot]
                # reading order: sub-line (y) first, then x — multi-line cells otherwise scramble
                if ws:
                    h = statistics.median(w[3] - w[1] for w in ws)
                    ws.sort(key=lambda w: ((w[1] + w[3]) / 2, w[0]))
                    lines, last = [], None
                    for w in ws:
                        yc2 = (w[1] + w[3]) / 2
                        if last is None or yc2 - last > h * 0.6:
                            lines.append([])
                        lines[-1].append(w); last = yc2
                    ws = [w for ln in lines for w in sorted(ln, key=lambda w: w[0])]
                bands.append({'page': p, 'anchor': aw, 'yc': c, 'words': ws})

        # date clusters across slice
        date_words = []
        for b in bands:
            for w in b['words']:
                if RE_DATE.fullmatch(w[4]):
                    date_words.append((b, w))
        dcl = cluster_1d([ (w[0]+w[2])/2 for _, w in date_words], 25)
        clusters = []
        for c in dcl:
            lo, hi = min(c) - 12, max(c) + 12
            members = [(b, w) for b, w in date_words if lo <= (w[0]+w[2])/2 <= hi]
            # units col: nearest numeric right of each date within band
            ux1 = []
            for b, w in members:
                cands = [v for v in b['words']
                         if (RE_NUM.fullmatch(v[4]) or v[4] == '#VALUE!') and v[0] >= w[2] - 2 and v[0] - w[2] < 150
                         and abs(((v[1]+v[3])/2) - ((w[1]+w[3])/2)) < max(2.5, (w[3]-w[1])*1.5)]
                if cands:
                    cands.sort(key=lambda v: v[0])
                    ux1.append(cands[0][2])
            clusters.append({'date_lo': lo, 'date_hi': hi, 'n': len(members),
                             'units_x1': statistics.median(ux1) if ux1 else None})
        # assign clusters -> milestones by units-col proximity to header anchors
        colmap = {}  # milestone -> cluster dict
        for cl in clusters:
            refx = cl['units_x1'] if cl['units_x1'] is not None else (cl['date_lo'] + cl['date_hi']) / 2
            best, bestd = None, 1e9
            for k, ax in anchors_x.items():
                d = abs(refx - ax)
                if d < bestd:
                    best, bestd = k, d
            if best is not None and bestd < 90 and cl['n'] >= 1:
                if best not in colmap or colmap[best]['n'] < cl['n']:
                    colmap[best] = cl
        # milestone with anchor but no date cluster: units col = numeric x1-cluster nearest anchor
        for k, ax in anchors_x.items():
            if k in colmap:
                continue
            numx1 = []
            for b in bands:
                for w in b['words']:
                    if RE_NUM.fullmatch(w[4]) and abs(w[2] - ax) < 90:
                        numx1.append(w[2])
            if len(numx1) >= 3:
                ncl = cluster_1d(numx1, 8)
                best = min(ncl, key=lambda c: abs(statistics.median(c) - ax))
                if abs(statistics.median(best) - ax) < 90:
                    colmap[k] = {'date_lo': None, 'date_hi': None, 'n': 0,
                                 'units_x1': statistics.median(best)}

        # identity columns
        street_x = None
        for w in hdr_words:
            if w[4] == 'Street':
                street_x = w[0] if street_x is None else min(street_x, w[0])
        track_x = None
        for w in hdr_words:
            if w[4].startswith('Tracking'):
                track_x = w[0] if track_x is None else min(track_x, w[0])

        rows = []
        for b in bands:
            aw = b['anchor']
            # book: 2-3 digit word left of the 9-digit anchor, OR stacked above/below it
            # (2023's tall wrapped rows put the book on its own sub-line at the same x)
            books = [w for w in b['words'] if RE_APN3.fullmatch(w[4]) and w is not aw
                     and ((w[2] <= aw[0] + 0.5 and aw[0] - w[0] < 25) or abs(w[0] - aw[0]) <= 3)]
            book = max(books, key=lambda w: w[0])[4] if books else ''
            apn_raw = (book + ' ' + aw[4]).strip()
            # address
            a_lo = (street_x - 15) if street_x is not None else aw[2] + 2
            a_hi = (track_x - 4) if track_x is not None else a_lo + 145
            addr_ws = [w for w in b['words'] if a_lo <= w[0] < a_hi and w is not aw
                       and not RE_APN9.fullmatch(w[4]) and not RE_TRACK.fullmatch(w[4])
                       and not RE_DATE.fullmatch(w[4])]
            addr_ws = [w for w in addr_ws if not (RE_APN3.fullmatch(w[4]) and w[2] <= aw[0] + 0.5)]
            address = ' '.join(w[4] for w in addr_ws).strip()
            track = ''
            for w in b['words']:
                if RE_TRACK.fullmatch(w[4]):
                    track = w[4]; break
            vals = {}
            for k, cl in colmap.items():
                dt, un = None, None
                if cl['date_lo'] is not None:
                    dts = [w for w in b['words'] if RE_DATE.fullmatch(w[4])
                           and cl['date_lo'] <= (w[0]+w[2])/2 <= cl['date_hi']]
                    if dts:
                        dts.sort(key=lambda w: abs((w[1]+w[3])/2 - b['yc']))
                        dt = dts[0][4]
                if cl['units_x1'] is not None:
                    uns = [w for w in b['words'] if (RE_NUM.fullmatch(w[4]) or w[4] == '#VALUE!')
                           and abs(w[2] - cl['units_x1']) <= 6]
                    if uns:
                        uns.sort(key=lambda w: abs((w[1]+w[3])/2 - b['yc']))
                        t = uns[0][4]
                        un = None if t == '#VALUE!' else int(t.replace(',', ''))
                vals[k] = (dt, un)
            rows.append({'page': b['page'], 'apn': apn_raw, 'address': address, 'tracking': track,
                         'vals': vals})
        slice_rows.append(rows)
        diag.append({'pages': sp, 'nrows': len(rows), 'anchors': {k: round(v) for k, v in anchors_x.items()},
                     'colmap': {k: (round(c['date_lo']) if c['date_lo'] else None,
                                    round(c['units_x1']) if c['units_x1'] else None, c['n'])
                                for k, c in colmap.items()}})

    # --- merge slices by row index ---
    n0 = len(slice_rows[0])
    ok = all(len(s) == n0 for s in slice_rows)
    mism = 0
    merged = []
    for i in range(n0):
        base = slice_rows[0][i]
        rec = {'year': year, 'row_idx': i, 'pages': str(base['page']),
               'apn_raw': base['apn'], 'address': base['address'], 'tracking': base['tracking'],
               'ent_date': None, 'ent_units': None, 'bp_date': None, 'bp_units': None,
               'co_date': None, 'co_units': None}
        for s in slice_rows:
            if i >= len(s):
                continue
            r = s[i]
            if r['apn'].split()[-1] != base['apn'].split()[-1]:
                mism += 1
            if len(r['address']) > len(rec['address']):
                rec['address'] = r['address']
            if r['tracking'] and not rec['tracking']:
                rec['tracking'] = r['tracking']
            for k in ('ent', 'bp', 'co'):
                dt, un = r['vals'].get(k, (None, None))
                if dt is not None and rec[f'{k}_date'] is None:
                    rec[f'{k}_date'] = dt
                if un is not None and rec[f'{k}_units'] is None:
                    rec[f'{k}_units'] = un
        merged.append(rec)

    if verbose:
        sums = {k: sum(r[f'{k}_units'] or 0 for r in merged) for k in ('ent', 'bp', 'co')}
        print(f'cy{year}: pages {run} | {len(slices)} slice(s) | rows {n0} '
              f'(slice sizes {[len(s) for s in slice_rows]}, apn mismatches {mism}) | '
              f"ENT {sums['ent']}  BP {sums['bp']}  CO {sums['co']}")
        for d in diag:
            print(f"   slice pages {d['pages']}: rows {d['nrows']} anchors {d['anchors']} "
                  f"colmap(date_x,units_x1,n_dates) {d['colmap']}")
    return merged


FIELDS = ['year', 'row_idx', 'pages', 'apn_raw', 'address', 'tracking',
          'ent_date', 'ent_units', 'bp_date', 'bp_units', 'co_date', 'co_units']

if __name__ == '__main__':
    for y in range(2018, 2026):
        rows = extract_year(y)
        with open(f'{OUT_DIR}/apr_pdf_rows_cy{y}.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            for r in rows:
                w.writerow(r)
