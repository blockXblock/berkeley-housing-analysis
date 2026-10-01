"""Parse the Harris & Associates 2016 segment cost table (Attachment 2 of the Baseline Study, inside the City's
January 2018 'Conceptual Study to Underground Utility Wires in Berkeley', PDF pp. 81-88).

Each street has a header row (number, street, limits, total length), then segment rows: an UNDERGROUNDED section
(from, to, length only) or an OVERHEAD section (from, to, length, three 1-5 impact ratings and their total, then the
cost in two zone columns: M/CB/C-DMU/SP zones and MUR/R zones). Checked against the report's own totals: arterial and
collector subtotals, and the $134,800,000 headline.
"""
import re

MONEY = r'\$\s*(?:‐|-|([\d,]+))'
SEG = re.compile(r'^\s{2,}(\S.*?)\s{2,}(\S.*?)\s{2,}(\d+)(?:\s+(\d)\s+(\d)\s+(\d)\s+(\d+)\s+(.*?))?\s*$')


def amounts(rest):
    """The two cost columns. Usually '$ ‐  $ 1,170,000'; some rows print a bare 0 for an empty column
    ('0 $ 7,800,000', Keith Ave). Dropping the '$' signs leaves exactly two tokens, a dash or a number."""
    tok = rest.replace('$', ' ').split()
    assert len(tok) == 2, f'cost columns not understood: {rest!r}'
    return [0 if t in ('‐', '-') else int(t.replace(',', '')) for t in tok]
HEAD = re.compile(r'^\s*(\d+)\s+(\S.*?)\s{2,}(\S.*?)\s{2,}(\S.*?)\s{2,}(\d+)\s*$')
# Fallback: some rows print the from and to limits with ONE space between them ('E OF CALIFORNIA ST ADELINE ST'), so
# they cannot be split by column; the limits are then kept together in seg_from and seg_to is left empty.
SEG1 = re.compile(r'^\s{2,}(\S.*?[^\d\s])\s+(\d+)(?:\s+(\d)\s+(\d)\s+(\d)\s+(\d+)\s+(.*?))?\s*$')
TOTAL = re.compile(r'^\s*Total\s+(.*\$.*?)\s*$')


def parse(txt_path):
    lines = open(txt_path, encoding='utf-8').read().split('\n')
    start = next(i for i, l in enumerate(lines) if 'ROAD NETWORK UTILITY UNDERGROUNDING PLANNING LEVEL ESTIMATE' in l)
    rows, totals, network, street = [], [], None, None
    for l in lines[start:]:
        if 'RESIDENTIAL ROAD' in l or 'RESIDENTIAL STREET' in l:
            break
        if 'ARTERIAL ROAD NETWORK' in l:
            network = 'arterial'; continue
        if 'COLLECTOR ROAD NETWORK' in l:
            network = 'collector'; continue
        if (m := TOTAL.match(l)):
            cc, cr = amounts(m.group(1))
            totals.append(dict(network=network, street_no=street and street['no'], street=street and street['street'],
                               cost_commercial=cc, cost_residential=cr))
            continue
        if (m := HEAD.match(l)):
            street = dict(network=network, no=int(m.group(1)), street=m.group(2).strip(), limits_from=m.group(3).strip(),
                          limits_to=m.group(4).strip(), street_length_ft=int(m.group(5)))
            continue
        m = SEG.match(l) if street else None
        if m:
            g = list(m.groups())
        elif street and (m1 := SEG1.match(l)):
            g = [m1.group(1), ''] + list(m1.groups()[1:])
        else:
            continue
        if True:
            costed = g[3] is not None
            cc, cr = amounts(g[7]) if costed else (0, 0)
            m = type('G', (), {'group': staticmethod(lambda i: g[i - 1])})
            rows.append(dict(network=network, street_no=street['no'], street=street['street'], seg_from=m.group(1).strip(),
                             seg_to=m.group(2).strip(), length_ft=int(m.group(3)),
                             status='overhead' if costed else 'undergrounded',
                             sidewalk_impact=m.group(4), traffic_impact=m.group(5), utility_density_impact=m.group(6),
                             impact_total=m.group(7), cost_m_cb_cdmu_sp_zones=cc, cost_mur_r_zones=cr, cost_total=cc + cr))
    return rows, totals


if __name__ == '__main__':
    import sys, collections
    rows, totals = parse(sys.argv[1])
    c = collections.Counter((r['network'], r['status']) for r in rows)
    print(len(rows), dict(c))
    for net in ('arterial', 'collector'):
        print(net, 'rows', sum(r['cost_commercial'] for r in totals if r['network'] == net),
              sum(r['cost_residential'] for r in totals if r['network'] == net),
              '| segments', sum(r['cost_m_cb_cdmu_sp_zones'] for r in rows if r['network'] == net),
              sum(r['cost_mur_r_zones'] for r in rows if r['network'] == net),
              '| overhead mi', round(sum(r['length_ft'] for r in rows if r['network'] == net and r['status'] == 'overhead') / 5280, 1))
    print('grand', sum(r['cost_total'] for r in rows))


# ---------------------------------------------------------------------------------------------------------------
# Bellecci & Associates, "Projected Costs of Undergrounding Utilities along City of Berkeley's Evacuation Routes"
# (December 2019), Appendix D, inside the Transportation Commission packet of 2020-01-16. Three versions of one
# per-street table: FY2019 baseline (programmatic), FY2023 programmatic (4%/yr inflation), FY2023 traditional CIP.
BELLECCI_VERSIONS = ['FY2019 baseline, programmatic', 'FY2023, programmatic', 'FY2023, traditional capital program']
BROW = re.compile(r'^\s*([A-Z][A-Za-z .]+?)\s{2,}(N/A|\d)\s+([\d.]+)\s+MILE\s+\$\s*([\d,]+|-)\s*\$\s*([\d,]+|-)\s*$')
BTOTAL = re.compile(r'^\s*Total\s+([\d.]+)\s+\$\s*([\d,]+)\s*$')


def parse_bellecci(txt_path):
    lines = open(txt_path, encoding='utf-8').read().split('\n')
    start = next(i for i, l in enumerate(lines) if l.strip() == 'Appendix D' and i > 2000)
    rows, totals, v = [], [], 0
    for l in lines[start:]:
        if (m := BROW.match(l)):
            n = lambda s: 0 if s == '-' else int(s.replace(',', ''))
            rows.append(dict(version=BELLECCI_VERSIONS[v], street=m.group(1).strip(),
                             complexity_level=None if m.group(2) == 'N/A' else int(m.group(2)),
                             overhead_centerline_miles=float(m.group(3)), unit_cost_per_mile=n(m.group(4)),
                             total_cost=n(m.group(5))))
        elif (m := BTOTAL.match(l)):
            totals.append(dict(version=BELLECCI_VERSIONS[v], miles=float(m.group(1)), printed_total=int(m.group(2).replace(',', ''))))
            v += 1
            if v == len(BELLECCI_VERSIONS):
                break
    for t in totals:          # the printed totals are rounded to $100,000
        s = sum(r['total_cost'] for r in rows if r['version'] == t['version'])
        mi = round(sum(r['overhead_centerline_miles'] for r in rows if r['version'] == t['version']), 2)
        assert abs(s - t['printed_total']) <= 50_000 and mi == t['miles'], (t, s, mi)
    return rows, totals
