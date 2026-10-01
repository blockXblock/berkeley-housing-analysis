#!/usr/bin/env python3
"""build_report.py — render the Berkeley Snapshot report (docs/berkeley-snapshot-2026-10.html) from derive.py's output.

Every number comes from docs/data/snapshot/facts.json or the data files beside it, except the figures in CITED below,
which come from documents rather than data files; each carries its source. Nothing else is typed by hand.

Run: .venv/bin/python scripts/snapshot/derive.py && .venv/bin/python scripts/snapshot/build_report.py
"""
import csv, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'docs', 'data', 'snapshot')
PAGE = os.path.join(ROOT, 'docs', 'berkeley-snapshot-2026-10.html')
F = json.load(open(os.path.join(DATA, 'facts.json')))
ACS = {r['column']: r for r in csv.DictReader(open(os.path.join(DATA, 'acs_city_2024_1yr_all_columns.csv')))}

# Figures from documents, not data files. Each: value(s) + where it is printed.
CITED = dict(
    streets=dict(centerline_mi=214.16, lane_mi=448.73, pci=55, arterial_mi=21.8, collector_mi=37.0, residential_mi=155.4,
                 pavement_sqft='39.63 million',
                 src='City of Berkeley, 2022 Pavement Management Program update (P-TAP 23 final report)'),
    ssmp=dict(miles=254, pump_stations=7, rehab_since_1986=227, src='City of Berkeley Sewer System Management Plan'),
    # Fall 2026's student census (taken after the fifth Friday of instruction) is not yet published as of 2026-10-01;
    # update undergrads/grads when OPA posts it. Admission offers are not enrollment.
    uc=dict(students=46151, undergrads=33122, grads=13029, term='fall 2025', staff=13422,
            offers_2026=(13982, 5284), convocation_2026=9000, housed_undergrads_2026=9700,
            src='UC Berkeley Office of Planning & Analysis, Quick Facts (fall 2025 enrollment); Berkeley News, July 29, '
                '2026 (fall 2026 admission offers); Berkeley News, August 26, 2026 (Fall Convocation: "over 9,000" new '
                'students); Berkeley News, March 23, 2026 (9,700 undergraduates in campus housing); IPEDS 2024-25 (faculty and staff)'),
    cap=dict(elec=-36, gas=-24, ghg_2023=432806, buildings_2023=168453,
             src='City of Berkeley, Climate Action Plan and Resilience Update, Council item 23, April 15, 2025 '
                 '(community inventory; UC Berkeley and Lawrence Berkeley National Laboratory excluded)'),
    water_household=dict(ccf_month=5, src='EBMUD presentation to the Berkeley City Council, June 11, 2019: '
                                          '"Typical water use in Berkeley is about 5 CCF per month"'),
    ebmud=dict(served=1_500_000, reservoirs=170, pipe_mi=4200, pumping=133,
               use_2025_mg=[('Single family', 22708), ('Multi-family', 9777), ('Industrial (incl. petroleum)', 6930),
                            ('Commercial', 4153), ('Landscape', 3578), ('Institutional/government', 2292)],
               potable_2025_mg=49438,
               src='EBMUD 2025 Urban Water Management Plan (pinned in the manifest) and EBMUD service-area page'),
    reservoirs=[('Summit', '416 Spruce St', '3.5 million gallons (tank; replaced the 37-million-gallon open reservoir, 2019)',
                 'EBMUD, Summit Reservoir Replacement page; CEQA filing 2010072060'),
                ('Berryman', 'above Euclid Ave, near Codornices Park', '2.6 million gallons', 'project architect (Muller & Caulfield)'),
                ('Shasta', 'Berkeley hills', 'not published', 'OpenStreetMap, within the City boundary'),
                ('Woods', 'Berkeley hills', 'not published', 'OpenStreetMap, within the City boundary'),
                ('Claremont (covered)', 'Claremont hills', 'not published', 'OpenStreetMap (tagged EBMUD)'),
                ('Berkeley View', 'Berkeley hills', 'not published; serves about 2,100 hill homes', 'press report (2017)')],
    kld=dict(residents=117000, zones=106, vehicles=90000, through=47000, primary_ai=(139, 1547), secondary_ai=(195, 3715),
             hill_capacity=900, flat_capacity=1700, fire_inspections=8600,
             src='KLD Associates, City of Berkeley Evacuation Time Estimate Study, TR-1296, July 1, 2025 (Tables 3-14, 6-6, 7-4; section 10.2); City of '
                 'Berkeley Evacuation StoryMaps (text version, July 2025); Community Wildfire Protection Plan (2023)'),
    # Hazards: every value verified 2026-10-01 in the saved source text (data/raw/hazards/*.txt). LHMP = City of Berkeley
    # 2024 Local Hazard Mitigation Plan, adopted March 18, 2025 (Council item 09); page labels as printed in the plan.
    hz=dict(
        lhmp_actions=33, lhmp_lapse='December 10, 2024',
        eq_bay_pct=72, eq_hayward_pct=33, eq_window='2014–2043',
        eq_deaths=100, eq_displaced='3,000 to 12,000', eq_damage='over $2 billion', eq_destroyed=620, eq_damaged=21000,
        eq_no_power=29000, ebmud_breaks=1800, ebmud_leaks=3900, eq_water_out='6 weeks, some as long as 6 months',
        sewer_liq_mi=101, sewer_liq_pct=39, sewer_slide_mi=50, storm_slide_mi=13,
        softstory=dict(asof='July 23, 2026', retrofitted=293, removed=63, permitting=6, out_of_compliance=7),
        urm='over 99% of about 700 unreinforced masonry buildings retrofitted or demolished since 1991 (2019 plan)',
        vulnerable=1047, transfer_rebate='up to one-third of the 1.5% transfer tax; over $12 million paid since 2002 (2019 plan)',
        fire_parcels=8603, fire_residents=32109, fire1923_structures=584, fire1923_homeless=4000, fire1923_footprint=1858,
        tunnel_deaths=25, ff_vote=74.2, ff_fy22=12.7, ff_fy23=9.3, ff_fy26=10969060, ff_inspections=8600,
        calfire_grant=2.8,
        tsu_people=1416, tsu_households=502, tsu_daytime=6840, tsu_businesses=448, tsu_employees=4821, marina_households=113,
        bay_rise_since1900='about eight inches', slr_i80='5.5 feet of rise with a 25-year storm could flood Interstate 80 and as far east as Fifth Street',
        gw='at 48 inches of rise, groundwater surfaces in West Berkeley north of University Avenue',
        storm_design='a 10-year storm; many parts over 90 years old', storms_2223='more than 15 inches of rain in 20 days',
        src=['City of Berkeley 2024 Local Hazard Mitigation Plan, adopted March 18, 2025 (Council item 09) and the 2019 plan',
             'USGS Fact Sheet 2016-3020 (Bay Area earthquake probabilities, 2014–2043)',
             'City of Berkeley soft-story inventory, status as of July 23, 2026',
             'Measure FF reports to Council, December 3, 2024 and June 24, 2025; Fire Department wildfire memo, August 25, 2023',
             'City Evacuation StoryMaps (July 2025) and the KLD Evacuation Time Estimate Study (2025)']),
    # City of Berkeley finances, verified 2026-10-01 in data/raw/city_finance/*.txt (adopted FY2027-28 budget, Council
    # 2026-06-23 Special Item 01; Budget & Finance Committee presentation 2026-05-14; FY2025 ACFR; CalPERS valuations as
    # of 6/30/2025; City Auditor, Berkeley's Financial Condition FY2016-FY2025, April 2026; Measure U resolution, item 38).
    city=dict(
        fte=[('Police Department', 302.00, 272.00), ('Public Works', 351.00, 337.00), ('Health, Housing & Community Services', 253.20, 195.00),
             ('Fire Department', 214.00, 190.00), ('Library', 131.18, 131.05), ('Parks, Recreation & Waterfront', 114.00, 114.00),
             ('Planning & Development', 109.04, 105.04), ('City Manager', 57.00, 44.00), ('Finance', 56.00, 48.00),
             ('Information Technology', 51.00, 45.00), ('Rent Board', 29.00, 29.00), ('Human Resources', 27.00, 24.00),
             ('Mayor and Council', 23.00, 23.00), ('City Attorney', 20.00, 19.00), ('City Auditor', 15.75, 15.75),
             ('City Clerk', 10.00, 9.00), ('Police Accountability', 6.00, 4.00)],
        fte_total=(1769.17, 1604.84), fte_gf=663.41, cut_fte=164.33, cut_if_no_tax=183,
        all_funds=916.8e6, general_fund=313.8e6,
        dept_gf=[('Police', 101111166), ('Fire', 51999702), ('Health, Housing & Community Services', 34054672),
                 ('City Manager', 13936928), ('Parks, Recreation & Waterfront', 12213160), ('Finance', 9114584),
                 ('Public Works', 8402866), ('Planning & Development', 3207882)],
        deficits=[('2018-19', 10), ('2020-21', 40), ('2022', 27), ('2023', 22), ('2024', 12), ('2025', 17), ('2026', 29)],
        deficit_fy27=31349339, deficit_fy28=29532958,
        calpers=[('Miscellaneous', 309023056, 77.4, 72.6), ('Police', 205663030, 64.5, 60.8), ('Fire', 96115914, 74.3, 70.7)],
        pension_paid_fy2016=36.8e6, pension_paid_fy2025=77.9e6, pension_forecast='$76 million in FY 2025 to $108 million in FY 2034',
        net_pension_liability=686433892, opeb=43.2e6,
        ot_police_fy2025=9.3e6, ot_fire_fy2025=7.9e6, ot_increase='$10.6 million increase in Police and Fire overtime expenditures from FY 2016 to FY 2025',
        deferred_maint=1.8e9, bond=300e6, bond_projects=272.5e6, bond_staffing=40.5e6, bond_debt_service=610e6,
        bond_parks=90697000, bond_pw=75135000, bond_fire=106668000, paving_plan=250e6, pci=56,
        src='City of Berkeley adopted FY2027-28 budget and FY2027-31 Capital Improvement Program (Council, June 23, 2026); '
            'Budget & Finance Policy Committee presentation, May 14, 2026; FY2025 Annual Comprehensive Financial Report; CalPERS '
            'actuarial valuations as of June 30, 2025; City Auditor, Berkeley\'s Financial Condition FY2016–FY2025 (April 2026); '
            'Police and Fire mid-biennial budget presentations (May 22, 2025); Measure U resolution (Council item 38, June 16, '
            '2026) and project list (February 2026)'),
    # Bikes, e-bikes, scooters (research 2026-10-01; sources in 'src').
    bikes=dict(
        compare=[('Davis', 11.22, 14.59), ('Boulder', 7.99, 12.18), ('Palo Alto', 7.91, 12.23), ('Cambridge, Mass.', 7.77, 11.23),
                 ('Berkeley', 4.35, 6.92), ('Portland', 3.37, 4.71), ('San Francisco', 3.30, 4.79), ('Oakland', 1.73, 2.36),
                 ('United States', 0.45, 0.52)],
        berkeley_2008_12=8.1, network=[('Paths (Class I)', 19.2, 19.8), ('Painted lanes (Class II)', 12.1, 10.6),
                 ('Upgraded painted lanes', 0.3, 1.8), ('Signed routes (Class III)', 8.2, 12.6), ('Bike boulevards', 11.9, 12.7),
                 ('Separated bikeways (Class IV)', 0.1, 3.6)], network_total=(51.8, 61.1),
        baywheels=[(2024, 87853, 49954), (2025, 134581, 100948)], baywheels_stations=48,
        scooters='up to 1,200 shared scooters and e-bikes, at most three operators, a $25,000 annual permit fee and $71 per device (2026 terms); Lime and VeoRide operate now',
        ava='Ava Community Energy pledged $10 million for over 9,000 e-bike rebates across its territory (launched July 2025; about 600 a month)',
        us_ownership='51% of U.S. adults lived in a household with an adult bicycle in 2022 (PeopleForBikes survey)',
        milvia=3477475, southside=16.5e6, hopkins=('$14–15 million', '$11 million', 1.2), unc_lane_median=89470,
        vision_zero='people walking and biking are almost 80% of those killed or severely injured in collisions, while making up about 40% of trips (2013–2017)',
        src='U.S. Census American Community Survey 2020–2024 5-year (table B08301, via Census Reporter) and the Census Bureau\'s 2008–2012 '
            'commuting report; Berkeley Bike Plan update, FITES committee, July 2025; Bay Wheels public trip files (counted by '
            'BerkeleyBuild: trips starting at Berkeley stations, BK- prefix); City of Berkeley shared-mobility permit terms (2026); '
            'Ava Community Energy (July 2025); PeopleForBikes 2022 participation study; Milvia Bikeway contract (Council, January 26, '
            '2021); Southside Complete Streets project page; Hopkins Corridor referral (Council, July 28, 2026); UNC Highway Safety '
            'Research Center, Costs for Pedestrian and Bicyclist Infrastructure Improvements (2013); Berkeley Vision Zero Action Plan'),
    # UC Berkeley and Berkeley Lab run their own utilities and are excluded from City figures. Each value: (number, year).
    campus=dict(
        ucb=dict(acres=(1095, '2021'), gsf=(13858460, '2018-19'), buildings_core=(100, '2024'), beds=(11621, '2024-25'),
                 beds_planned=(2613, 'by fall 2029'), lrdp_beds=(20750, 'LRDP buildout'), parking=(6340, '2018-19'),
                 water_gal=(594404932, '2018'), gas_mmbtu=(2334237, '2018'), elec_mwh=(None, ''),
                 ghg=(160270, '2024'), ghg_scope1=(127957, '2024'), ghg_cogen=(114262, '2024'), ghg_scope2=(196, '2024'),
                 ghg_scope3=(32117, '2024'), ghg_series=[200700, 204909, 179998, 159363, 174113, 160270],
                 employees=(13422, '2024-25'), sov_staff=('34%', '2024-25')),
        lbnl=dict(acres=(202, '2025'), gsf=(2061500, '2024'), buildings=(170, '2025'), employees=(3350, 'spring 2024'),
                  academics=(1200, 'spring 2024'), affiliates=(5000, 'spring 2024'), onsite_daily=(3000, '2024'),
                  parking=(2200, '2024'), water_gal=(42600000, 'FY2023'), elec_mwh=(132397, 'FY2023'),
                  gas_therms=(1500000, 'FY2023'), peak_mw=(21.5, '2022'), ghg=(37713, '2024'), ghg_scope1=(7826, '2024'),
                  ghg_scope2=(19119, '2024'), sov=('about 30%', 'spring 2024')),
        src=['UC Regents item F4, July 21, 2021 (LRDP: 1,095 acres; Table 1-2: 2018-19 floor area, beds, parking, staff)',
             'California State Auditor report 2024-111, Table B.1, October 2025 (UC Berkeley beds)',
             'UC Berkeley 2021 LRDP EIR, greenhouse-gas appendix (2018 water and natural gas)',
             'UC Berkeley Office of Sustainability, greenhouse gas inventory (2019-2024)',
             'UC Regents item F2, July 16, 2025 (Berkeley Clean Energy Campus); ACEEE 2024 paper by campus staff (core campus, cogeneration)',
             'UC 2025 Annual Report on Sustainable Practices (commuting; per-campus chart data from its public Google Sheets, fetched 2026-10-01)',
             'AASHE STARS, UC Berkeley 2025 report (submitted February 19, 2025): credits OP-3, OP-5, OP-6, OP-14 and PRE-3, saved 2026-10-01 with a signed-in account',
             'UC Berkeley Clean Energy Campus fact sheet, April 5, 2023 (sustainability.berkeley.edu)',
             'UC Regents item F4, May 15, 2024 (Phase 1 budget, geothermal wells); cleanenergycampus.berkeley.edu (schedule, viewed 2026-10-01); STARS 2025 review template (completion-date note)',
             'Lawrence Berkeley National Laboratory 2025 LRDP Draft EIR, April 2025 (people, energy, water, GHG, parking); '
             'UC Regents item F1B, September 17, 2025 (202 acres, buildings, floor area)']),
    # Harris 2016 Table 1 (feet as printed): total and undergrounded, by street class. Miles are computed from the feet;
    # the table's own residential overhead figure prints 149.9 mi, but its 775,399 ft is 146.9 mi.
    table1_ft=dict(arterial=(135095, 66015), collector=(190460, 59660), residential=(832666, 57267)),
    ug=dict(harris_rule20a_per_year=533000, harris_rule20a_balance=6_400_000, bellecci_rule20a_balance=9_009_095,
            uud48_parcels=175, uud48_feet=7000, conceptual_per_mile='$4.5–5.2 million', conceptual_range='$170–200 million',
            src_harris='Harris & Associates, Baseline Study for the Development of a Utility Undergrounding Program, '
                       'July 22, 2016 (Appendix A of the City\'s January 2018 Conceptual Study to Underground Utility Wires)',
            src_concept='Public Works, Disaster and Fire Safety, and Transportation Commissions, Conceptual Study to '
                        'Underground Utility Wires in Berkeley (Phase 2), January 2018, Table 8',
            src_bellecci='Bellecci & Associates, Projected Costs of Undergrounding Utilities along City of Berkeley\'s '
                         'Evacuation Routes, December 2019 (Transportation Commission packet, January 16, 2020)',
            src_uud48='CEQA Notice of Exemption, January 15, 2019; CPUC Draft Resolution E-4993, October 10, 2019'),
)

esc = html.escape
n = lambda v, d=0: '—' if v is None or v == '' else (f'{float(v):,.{d}f}')
usd = lambda v: '—' if v is None else f'${float(v):,.0f}'
big = lambda v: f'${v / 1e9:,.1f} billion' if v >= 1e9 else f'${v / 1e6:,.1f} million'
pct = lambda a, b: f'{100 * a / b:.0f}%' if b else '—'


def rnd(v):
    """Round an ESTIMATE (survey, model, synthetic data) to a sensible precision: tens under 1,000, hundreds under
    100,000, thousands above. Exact counts (registrations, assessor records, budgets, trips) are never passed here."""
    v = float(v)
    step = 10 if abs(v) < 1000 else (100 if abs(v) < 100000 else 1000)
    return f"{round(v / step) * step:,.0f}"


about = lambda v: f'about {rnd(v)}'
pc = lambda x: f'{float(x):.0f}%'                    # survey percentages: whole numbers


def table(head, rows, right=None, cls=''):
    right = set(right or [])
    h = ''.join(f'<th class="r">{esc(c)}</th>' if i in right else f'<th>{esc(c)}</th>' for i, c in enumerate(head))
    b = ''.join('<tr>' + ''.join(f'<td class="r">{c}</td>' if i in right else f'<td>{c}</td>' for i, c in enumerate(r))
                + '</tr>' for r in rows)
    return (f'<div class="tw"><button class="full" type="button">Open full table \u2922</button>'
            f'<table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>')


def bar(v, mx, w=9):
    return f'<span class="bar" style="width:{w * v / mx:.2f}rem"></span>' if mx else ''


def acs_table(tid, skip=(), title=None):
    """Every column of one ACS table, with its margin of error and a bar."""
    cols = sorted(c for c in ACS if c.startswith(tid) and c not in skip)
    tot = float(ACS[cols[0]]['estimate'])
    body = cols[1:]
    mx = max(float(ACS[c]['estimate']) for c in body)
    rows = [[esc(ACS[c]['label']), n(ACS[c]['estimate']), '±' + n(ACS[c]['margin_of_error']),
             pct(float(ACS[c]['estimate']), tot), bar(float(ACS[c]['estimate']), mx)] for c in body]
    rows.append([f'<strong>{esc(ACS[cols[0]]["label"].rstrip(":"))}</strong>', f'<strong>{n(tot)}</strong>',
                 '±' + n(ACS[cols[0]]['margin_of_error']), '', ''])
    return table([title or ACS[cols[0]]['table_title'], 'Estimate', 'Margin', 'Share', ''], rows, right={1, 2, 3})


def card(num, label, sub=''):
    return f'<div class="card"><div class="n">{num}</div><div class="l">{label}</div><div class="s">{sub}</div></div>'


def csvrows(name):
    return list(csv.DictReader(open(os.path.join(DATA, name))))


def dl(name):
    return f'<a class="dl" href="data/snapshot/{name}">{esc(name)}</a>'


LEDE = {
    'people': 'How many people live in Berkeley, in what kinds of homes, and how that has changed since 2020.',
    'tenure': 'Who rents and who owns, what homes cost, and what share of income rent takes.',
    'income': 'Household income, poverty and education, citywide; the same measures for each block group are in the data files.',
    'age': 'The ages and origins of Berkeley residents.',
    'tide': 'Who comes into Berkeley to work, who leaves, where they come from and go, and how residents travel.',
    'cars': 'Vehicles registered by ZIP code and fuel, households without a car, and the bikes, e-bikes and scooters that are changing how people move.',
    'land': 'What the County assesses Berkeley\'s land and buildings at, who is exempt, and how value spreads across neighborhoods.',
    'city': 'How many people the City employs, what it spends and on what, its pension and overtime costs, its deficits, and the gap between its capital needs and its funding.',
    'networks': 'The streets, water mains, sewers, storm drains, gas lines and poles under and over the city, how old they are, and what is not public.',
    'undergrounding': 'How much of Berkeley still has overhead wires, and what the City\'s own studies say it costs to bury them.',
    'water-energy': 'How much water and power Berkeley uses, and what can be known about use by building, block or neighborhood.',
    'fire': 'The three disasters Berkeley plans for: how likely each is, who and what is exposed, and the steps taken so far.',
    'campus': 'What the campus and the Lab use and emit, how many buildings they run, and the plan to retire the campus\'s gas plant.',
    'ucpay': 'How much the University pays the City and County each year, under what agreement, for what, and what the City gave up in return.',
    'business': 'How many businesses are licensed in Berkeley, what kinds, where they are, and what they pay.',
    'innovation': 'The changes already under way that will reshape streets, power and water: electric cars, e-bikes, working from home, an electric campus, undergrounding.',
    'data': 'Every data file behind this report, what each holds, and where each source came from.',
}


ORDER = ['people', 'tenure', 'income', 'age', 'tide', 'cars', 'business', 'networks', 'undergrounding', 'water-energy',
         'fire', 'campus', 'ucpay', 'land', 'city', 'innovation', 'data']


def section(id_, kicker, title, body):
    if id_ in ORDER:                               # number sections by their order, never by hand
        kicker = re.sub(r'^\d+ · ', f'{ORDER.index(id_) + 1} · ', kicker)
    lede = f'<p class="lede" style="margin-bottom:.6rem">{LEDE[id_]}</p>' if id_ in LEDE else ''
    return f'<section class="page" id="{id_}"><div class="kicker">{kicker}</div><h2>{title}</h2>{lede}{body}</section>'


# ============================================================================================ sections
V2050 = 'berkeley2050/founding/papers/2020-05_vision2050-framework_taskforce-edition.pdf'
DRAWDOWN = 'berkeley2050/founding/2017-08-24_berkeley-drawdown-solutions.pdf'


def s_findings():
    """What the numbers say: the findings, each computed from the data, linked to its section and its data file."""
    D = F['dof']['rows'][-1]
    i = F['acs_city']['ind']
    L = F['lodes']
    dm = F['dmv']
    A = F['assessor']
    I = F['infra']
    U = F['ug']
    T1 = CITED['table1_ft']
    over = sum(a - b for a, b in T1.values()) / 5280
    total = sum(a for a, _ in T1.values()) / 5280
    res_over = (T1['residential'][0] - T1['residential'][1]) / 5280
    tr = F['poles']['traced']
    lo, hi = over * 5280 / tr['250']['mean_span_ft'], over * 5280 / tr['200']['mean_span_ft']
    CS = F['campus_sus']
    g24 = sum(next(r['total'] for r in CS[t]['rows'] if r['year'] == 2024) for t in ('ucb', 'lbnl'))
    ST = F['stars2025']
    sqft = ST['floor_m2'] * 10.7639
    true_kbtu = (ST['total_mwh'] - ST['gas_mwh'] + ST['implied_gas_mwh']) * 3412.14 / sqft
    true_mwh = ST['total_mwh'] - ST['gas_mwh'] + ST['implied_gas_mwh']
    lab_mwh = 132397 + 1.5e6 * 0.0293071                      # LBNL FY2023: 132,397 MWh electricity + 1.5 million therms
    ci = [r for r in F['beso']['by_type'] if r['property_type'] in ('Commercial', 'Industrial', 'Mixed Use (Comm/Ind)')]
    bc_mwh = sum(r['electricity_kwh_2024'] / 1000 + r['gas_therms_2024'] * 0.0293071 for r in ci)
    bc_n = sum(r['buildings'] for r in ci)
    stars_kbtu = ST['total_mwh'] * 3412.14 / sqft
    d = U['disagree'][0]
    rn = U['summary']['report_network_totals']
    fz = {r['fire_zone']: r for r in A['by_fire']}
    a = lambda href, text: f'<a href="{href}">{text}</a>'
    item = lambda title, body, links: (f'<div class="finding"><h3>{title}</h3><p>{body}</p>'
                                        f'<p class="note">{links}</p></div>')
    F_ = [
        item('A university city, and a commuter city',
             f"{n(D['population'])} people live in Berkeley; {n(D['group_quarters'])} of them, one in six, live in dorms, co-ops and "
             f"other group housing. Each workday {about(L['inflow'])} people commute in and {about(L['outflow'] + L['out_of_state_out'])} residents "
             f"commute out, so Berkeley gains about {round(L['inflow'] - L['outflow'] - L['out_of_state_out'], -2):,.0f} workers by day, "
             f"before counting {n(CITED['uc']['students'])} UC Berkeley students. The largest employer sector is education: "
             f"{about(L['sectors'][0][1])} of {about(L['jobs'])} jobs in the city.",
             f"{a('#people', 'People')} · {a('#tide', 'Daily tide')} · data: {dl('lodes_2023_inflow_by_home_place.csv')}"),
        item('Room for many more: plans point to 30,000 or more new residents',
             f"Berkeley's population has held near {rnd(D['population'])} since 2020. The State requires the City to plan for 8,934 new "
             f"homes by 2031; BerkeleyBuild's pipeline counts 11,222 homes approved or proposed but not yet built; and UC Berkeley's "
             f"long-range plan adds up to 11,730 beds. Built out at today's {D['persons_per_household']:.2f} people per home, the pipeline "
             f"alone would house about {rnd(11222 * D['persons_per_household'])} more people, and with UC's beds the city would approach "
             f"{rnd(D['population'] + 11222 * D['persons_per_household'] + 11730)}. Every new resident adds to the daily load on the same "
             f"water mains, sewers, power lines and evacuation routes this report describes.",
             f"{a('#people', 'People')} · {a('#campus', 'The University')} · data: {dl('dof_e5_berkeley_2020_2026.csv')}"),
        item('Most households rent, and most renters are stretched',
             f"{pc(i['renter_household_pct'])} of households rent. {pc(i['rent_burdened_30pct'])} of renter households pay 30% or more of "
             f"their income in rent, and about one in three pay half or more. Incomes split "
             f"at both ends: {about(i['hh_income_under_50k'])} households earn under $50,000 and {about(i['hh_income_200k_plus'])} earn "
             f"$200,000 or more.",
             f"{a('#tenure', 'Renters and owners')} · {a('#income', 'Income')} · maps: {dl('berkeley_blockgroups.geojson')}"),
        item('How people move has already changed',
             f"About a third of employed residents work from home, as many as drive alone to work "
             f"(about {pc(i['commute_drive_alone_pct'])} each). One household in five has no car. Of {n(dm['total'])} registered "
             f"vehicles, {n(dm['ev'])} ({100 * dm['ev'] / dm['total']:.0f}%) are electric or plug-in hybrids, up from "
             f"{n(F['dmv_trend']['2021']['plug_in'])} five years earlier. Shared e-bike trips are growing fast: Bay Wheels rides from "
             f"Berkeley stations rose 53% in 2025. In 2020 the City's "
             f"Vision 2050 framework wrote that it was \u201cunknown what alternative forms of transportation might emerge and how "
             f"personal transportation behaviors might change\u201d; the working-from-home figure answers part of that. Autonomous "
             f"vehicles and home deliveries, which the 2017 Berkeley Drawdown list flagged, are not yet counted by any public source.",
             f"{a('#cars', 'Cars')} · {a('#tide', 'Commuting')} · {a(V2050, 'Vision 2050 framework (2020)')} · "
             f"{a(DRAWDOWN, 'Berkeley Drawdown solutions (2017)')}"),
        item(f'{over:.0f} of {total:.0f} street miles still carry overhead wires',
             f"Only {total - over:.1f} miles ({100 * (total - over) / total:.0f}%) have their wires underground: half of the arterials, a third "
             f"of the collectors and {100 * T1['residential'][1] / T1['residential'][0]:.0f}% of residential streets. Overhead lines are a "
             f"hazard in each disaster Berkeley plans for. In a fire, burning poles topple across the streets fire engines and evacuees "
             f"need, and drop live high-voltage lines on homes and people; in the 1991 Oakland fire, falling lines blocked streets, started "
             f"new fires and cut power to the pumps that supplied the hydrants. In an earthquake or windstorm, swaying poles snap their "
             f"wires. About {round(lo, -2):,.0f}–{round(hi, -2):,.0f} poles<sup>1</sup> line Berkeley's streets, carrying roughly "
             f"7,000–8,000 oil-filled transformers for homes<sup>2</sup>, and perhaps 10,000 counting businesses, the campus and the Lab. "
             f"Burying all {over:.0f} miles would cost roughly ${over * 3.25 / 1000:.1f} to ${over * 6.1 / 1000:.1f} billion<sup>3</sup>; the "
             f"City's capital plan budgets nothing for it. Even the City's own estimate for the main streets is low: its 2016 cost table "
             f"prices {esc(d['street'].title())}'s five residential-zone segments at {usd(d['segments_residential'])} but leaves them out of "
             f"its totals, so the arterials and collectors cost {big(U['total'])} in 2016 dollars, not the {big(rn['headline'])} quoted "
             f"ever since.",
             f"{a('#undergrounding', 'Undergrounding')} · {a('#networks', 'Under the streets')} · data: {dl('undergrounding_segments_harris_2016.csv')}, "
             f"{dl('wood_pole_lines_traced.geojson')}"),
        item('Water and sewer pipes are old, and the money for them shrank',
             f"Half of the pipe segments in Berkeley's {I['water_mi']:.0f} miles of water main were laid before {I['water_median_year']}, and "
             f"{I['water_pre1940_mi']:.0f} miles before 1940. The City has relined about 180 of its 261 miles of sewer main since "
             f"1986, work worth about $450 million at its own current unit costs, and budgets about $24 million a year more. The weak "
             f"link is the roughly 31,600 house laterals, most as old as the houses they serve; nearly half of Berkeley's homes were "
             f"built before 1940. Rain leaking through cracked laterals, joints and mains can raise sewage flows more than tenfold in "
             f"storms, which is why a federal consent decree requires each lateral to be tested, and repaired if it leaks, when a "
             f"property is sold or substantially remodeled. "
             f"Vision 2050 documented the City's annual infrastructure funding falling from $53 million to $40 million between FY2012 "
             f"and FY2019, while unfunded needs grew.",
             f"{a('#networks', 'Under the streets')} · {a(V2050, 'Vision 2050 framework (2020)')} · maps: {dl('infrastructure_by_blockgroup.csv')}"),
        item('Leaving the hills in a fire takes hours',
             f"The City's 2025 evacuation study finds that clearing 90% of vehicles from hill Fire Zones 2 and 3 takes 1:45 to 2:20, "
             f"and the last vehicles 3:25 to 3:40. One hour in, most roads in the zones are over capacity. "
             f"{n(CITED['kld']['primary_ai'][1])} residential parcels have a single way out. The hill zones hold "
             f"{n(fz[2]['parcels'] + fz[3]['parcels'])} parcels and {big(fz[2]['net_taxable_value'] + fz[3]['net_taxable_value'])} of "
             f"taxable value.",
             f"{a('#fire', 'Fire evacuation')} · data: {dl('evacuation_clearance_times_kld_2025.csv')}"),
        item('The University and the Lab use far more energy than all of Berkeley\'s large businesses',
             f"UC Berkeley used about {round(true_mwh, -4):,.0f} MWh of energy in 2023, most of it gas burned in its own power plant, and "
             f"Berkeley Lab about {round(lab_mwh, -3):,.0f} MWh. All of Berkeley's large commercial and industrial buildings, the "
             f"{bc_n} that report under the City's energy ordinance, used about {round(bc_mwh, -3):,.0f} MWh in 2024: the University "
             f"and the Lab together used about {(true_mwh + lab_mwh) / bc_mwh:.0f} times as much. They draw about "
             f"{(ST['water_m3'] * 264.172 + 42.6e6) / 365 / 1e6:.1f} million gallons of water a day, roughly {100 * ((ST['water_m3'] * 264.172 + 42.6e6) / 365) / (49438e6 / 365 * F['dof']['rows'][-1]['population'] / 1.5e6):.0f}% of "
             f"the city's estimated use. Together they emitted {g24:,.0f} tonnes of CO\u2082e in 2024, equal to "
             f"{100 * g24 / CITED['cap']['ghg_2023']:.0f}% of the City's community inventory, which leaves both out. The campus's gas plant "
             f"is due to be replaced by an electric heating and cooling plant, its retirement now expected between 2030 and 2033. Under a "
             f"2021 settlement the University pays the City about $4.75 million a year, rising 3% annually; in return the City agreed not "
             f"to sue over its growth plans or enrollment.",
             f"{a('#campus', 'The University and the Lab')} · {a('#ucpay', 'What UC pays')} · {a('#water-energy', 'Water and power')} · data: "
             f"{dl('campus_lab_emissions_energy_2009_2024.csv')}, {dl('beso_large_buildings_energy.csv')}"),
        item(f"{n(F['business']['licenses'])} licensed businesses, most of them small",
             f"The City licenses {n(F['business']['licenses'])} businesses, {n(F['business']['located'])} of them at a Berkeley address; "
             f"the rest are mostly contractors and firms based elsewhere that work here. Most are small: "
             f"{n(F['business']['ownership'].get('Sole Ownership', 0))} are sole proprietorships. The most common local businesses are "
             f"therapists' and counselors' offices, restaurants, beauty salons, architects and lawyers, clustered downtown, in South and "
             f"Southwest Berkeley and along College Avenue in the Elmwood. They paid "
             f"${json.load(open(os.path.join(ROOT, 'data', 'reference', 'berkeley_budget_external_facts_2026-08-15.json')))['revenues_fy2025_actual']['business_license_tax'] / 1e6:.1f} million "
             f"in business license tax in FY2025. Berkeley's {about(L['jobs'])} jobs are dominated by education, about {rnd(L['sectors'][0][1])}, "
             f"followed by professional and technical services and health care.",
             f"{a('#business', 'Businesses')} · {a('#tide', 'Daily tide')} · maps: {dl('businesses_by_blockgroup.csv')}"),
        item('The next large earthquake is the biggest single danger',
             f"The U.S. Geological Survey gives a {CITED['hz']['eq_hayward_pct']}% chance of a magnitude 6.7 or larger earthquake on "
             f"the Hayward or Rodgers Creek faults between 2014 and 2043. The City's hazard plan estimates that a large Hayward "
             f"earthquake would kill about {CITED['hz']['eq_deaths']} people in Berkeley, displace {CITED['hz']['eq_displaced']} "
             f"households and cut water to some homes for as long as six months. {CITED['hz']['softstory']['retrofitted']} soft-story "
             f"apartment buildings have been retrofitted under the City's mandate; {n(CITED['hz']['vulnerable'])} other potentially "
             f"vulnerable buildings face no requirement. On the shoreline, {about(CITED['hz']['tsu_people'])} residents live in the "
             f"tsunami zone, and the Bay has risen {CITED['hz']['bay_rise_since1900']} since 1900.",
             f"{a('#fire', 'Fire, flood and earthquake')} · sources: the City's 2024 Local Hazard Mitigation Plan; USGS"),
        item("The City's needs outrun its money",
             f"The City lists {big(F['capital']['total']['need'])} of capital and maintenance needs, from buildings and storm drains "
             f"to streets, parks and undergrounding, and funds {big(F['capital']['total']['available_5yr'])} of it over five years; the "
             f"unfunded gap stays above $2.1 billion every year through 2031. Its General Fund has run a deficit every year since "
             f"2018, $31.3 million projected for FY2027, closed each time with one-time money, and the FY2027 budget cuts 164 positions. "
             f"Pension payments doubled in nine years, to $77.9 million. The $300 million Measure U bond on the November ballot would "
             f"cover about 14% of the stated need and none of the undergrounding.",
             f"{a('#city', 'The City\'s money')} · data: {dl('city_capital_needs_fy2027_2031.csv')}"),
        item('A $30 billion tax base, with the University outside it',
             f"Berkeley's {n(A['parcels'])} parcels carry {big(A['net'])} of net taxable value, about "
             f"${round(A['net'] * 0.012323 / 1e6):,.0f} million a year in base property tax for all agencies. {n(A['exempt'])} parcels pay none: the "
             f"University, the City, schools, churches and other exempt owners.",
             f"{a('#land', 'Land and money')} · data: {dl('assessor_by_neighborhood.csv')}"),
    ]
    # findings follow the report's outline: people, businesses, infrastructure, dangers, institutions, money
    outline = ['A university city', 'Room for many more', 'Most households rent', 'How people move', 'licensed businesses',
               'street miles', 'Water and sewer pipes', 'Leaving the hills', 'The next large earthquake',
               'The University and the Lab use', 'A $30 billion tax base', "The City's needs outrun"]
    F_.sort(key=lambda h: next((k for k, key in enumerate(outline) if key in h.split('</h3>')[0]), 99))
    gaps = table(['What is not public', 'Who holds it'], [
        ['Citywide electricity and gas use', 'PG&amp;E (by ZIP code, after registration); the City (trend only)'],
        ["Berkeley's water use", 'EBMUD (customer data is confidential; the City could request its total)'],
        ['Utility poles, their age and their transformers', 'PG&amp;E (Joint Use Map Portal, closed to the public)'],
        ["The campus's total electricity", "UC Berkeley's Office of Sustainability"],
        ['Autonomous vehicles, ride-hailing and delivery trips', 'CPUC and DMV permit data; the companies'],
        ['Fall 2026 student enrollment', 'UC Berkeley Office of Planning &amp; Analysis (due later this fall)'],
    ])
    body = f'''
    <p class="lede">The findings, each linked to its section, data and sources. Where the City's Vision 2050 work addressed the
    same question, it is cited.</p>
    {''.join(F_)}
    <h3>What we could not find, and who has it</h3>
    {gaps}
    <h3>Notes</h3>
    <p class="note"><sup>1</sup> From the spacing of the {n(F['poles']['wood'])} wood utility poles that carry City streetlights:
    {over:.0f} overhead street miles at spans of {F['poles']['traced']['200']['mean_span_ft']:.0f}–{F['poles']['traced']['250']['mean_span_ft']:.0f}
    feet. Poles along rear lot lines are additional.<br>
    <sup>2</sup> PG&amp;E's "average number of customers per residential transformer is 7" (2027 rate case, A.25-05-009, rebuttal
    Exhibit PG&amp;E-18) applied to Berkeley's {rnd(F['dof']['rows'][-1]['occupied'])}–{rnd(F['dof']['rows'][-1]['housing_units'])}
    homes; pole-top and underground units.<br>
    <sup>3</sup> At $3.25 million a mile (PG&amp;E's 2023–2025 average) to $6.1 million (the City's 2019 average, street lighting
    included), before inflation, engineering and building connections. Safety quotations: the City's 2018 Conceptual Study to
    Underground Utility Wires, citing FEMA's report on the 1991 Oakland fire.</p>
    <p class="note">Two findings note discrepancies we found in institutions' own documents: the City's 2016 undergrounding
    cost table and UC Berkeley's 2025 STARS energy entry. Both link to the documents.</p>'''
    return section('findings', 'What the numbers say', 'What we found', body)


def s_people():
    D = F['dof']['rows']
    last = D[-1]
    i = F['acs_city']['ind']
    dof_rows = [[r['year'], n(r['population']), n(r['household_population']), n(r['group_quarters']), n(r['housing_units']),
                 n(r['occupied']), f"{100 * r['vacancy_rate']:.1f}%", f"{r['persons_per_household']:.2f}"] for r in D]
    body = f'''
    <div class="grid">
      {card(n(last['population']), f"residents, January 1, {F['dof']['year']}", 'State Department of Finance (E-5).')}
      {card(n(last['housing_units']), 'homes', f"{n(last['occupied'])} occupied; vacancy {100 * last['vacancy_rate']:.1f}%.")}
      {card(n(last['group_quarters']), 'residents in group housing', f"Dorms, co-ops, fraternities, care homes: {pct(last['group_quarters'], last['population'])} of residents.")}
      {card(n(CITED['uc']['students']), f"UC Berkeley students ({CITED['uc']['term']})", f"{n(CITED['uc']['undergrads'])} undergraduates, {n(CITED['uc']['grads'])} graduate students; plus {n(CITED['uc']['staff'])} faculty and staff. {n(CITED['uc']['housed_undergrads_2026'])} undergraduates live in campus housing. Fall 2026: the official count is not yet published; {n(sum(CITED['uc']['offers_2026']))} were offered admission and over {n(CITED['uc']['convocation_2026'])} new students attended Fall Convocation.")}
    </div>
    <h3>Population and homes, 2020–2026</h3>
    {table(['Year', 'Residents', 'In households', 'In group housing', 'Homes', 'Occupied', 'Vacancy', 'Per household'], dof_rows, right=range(1, 8))}
    <p class="note">2020 is the April 1 census; other years are January 1. The 2021 drop in group housing (20,925 to
    14,527) is the campus emptying during the pandemic. Data: {dl('dof_e5_berkeley_2020_2026.csv')}</p>
    <h3>How many people Berkeley may hold</h3>
    <p class="note" style="font-size:.95rem">Berkeley's population has been flat since 2020, at about 127,600, after a pandemic dip to
    120,670 in 2021 when the campus emptied. Three plans point higher. The State requires Berkeley to plan for 8,934 new homes from
    2023 to 2031. BerkeleyBuild's pipeline counts 11,222 homes approved or proposed but not yet built<sup>1</sup>. And UC Berkeley's
    long-range plan adds up to 11,730 student and staff beds, taking campus housing from about 9,000 to 20,750. If the pipeline were
    built at today's {F['dof']['rows'][-1]['persons_per_household']:.2f} people per home, and UC built its beds, Berkeley would gain
    about {rnd(11222 * F['dof']['rows'][-1]['persons_per_household'])} residents in homes and up to about 11,700 in University
    housing: about {rnd(F['dof']['rows'][-1]['population'] + 11222 * F['dof']['rows'][-1]['persons_per_household'] + 11730)} people in
    all. That is a scenario, not a forecast; some approved projects will not be built, and many of UC's new beds will house students
    who now live in Berkeley apartments.</p>
    <p class="note"><sup>1</sup> Not yet built, excluding UC projects (BerkeleyBuild Pipeline Explorer, September 30, 2026). State
    target: the City's Annual Progress Report to the State, Table B. UC beds: UC Regents item F4, July 2021, Table 2.</p>
    <h3>Homes by type (Department of Finance, {F['dof']['year']})</h3>
    {table(['Type', 'Homes', 'Share'], [[k, n(last[c]), pct(last[c], last['housing_units'])] for k, c in
        (('Single detached', 'single_detached'), ('Single attached', 'single_attached'), ('Two to four units', 'two_to_four'),
         ('Five or more units', 'five_plus'), ('Mobile homes', 'mobile_homes'))], right={1, 2})}
    <p class="note">The Census survey ({F['acs_city']['release']}) counts {about(i['population'])} residents: a mid-2024
    survey estimate, lower than the state's January 2026 figure, mainly in group housing. The tables below use the
    survey because only it describes residents (tenure, income, age, cars); use the state's totals for counts.</p>'''
    return section('people', '1 · The people', 'Who lives in Berkeley', body)


def s_tenure():
    i = F['acs_city']['ind']
    body = f'''
    <div class="grid">
      {card(rnd(i['renter_households']), f"renter households ({pc(i['renter_household_pct'])})", f"About {rnd(i['residents_renter_occupied'])} residents live in rented homes.")}
      {card(rnd(i['owner_households']), f"owner households ({pc(100 - i['renter_household_pct'])})", f"About {rnd(i['residents_owner_occupied'])} residents live in owned homes.")}
      {card('about $' + rnd(i['median_gross_rent']), 'median gross rent a month', 'Rent plus utilities.')}
      {card(f"about ${i['median_home_value'] / 1e6:.1f} million", 'median value of an owned home', "Owners' own estimate (Census survey).")}
    </div>
    <p class="note">Households split 54/46 toward renting, yet residents split evenly, because owner households are larger.</p>
    <div class="two"><div>{acs_table('B25070', title='Rent as a share of household income (renters)')}</div>
    <div>{acs_table('B25034', title='Homes by year built')}</div></div>
    <p class="note">About {rnd(float(ACS['B25070010']['estimate']))} renter households, one in three, pay half their income
    or more in rent. Nearly half of Berkeley's homes ({pct(float(ACS['B25034011']['estimate']), float(ACS['B25034001']['estimate']))})
    were built before 1940.</p>
    <div class="two"><div>{acs_table('B25041', title='Homes by number of bedrooms')}</div>
    <div>{acs_table('B25024', title='Homes by units in the building')}</div></div>
    <div class="two"><div>{acs_table('B11001', title='Household types')}</div>
    <div>{acs_table('B25004', title='Vacant homes by reason')}</div></div>'''
    return section('tenure', '2 · Renters and owners', 'Who rents, who owns, and what they pay', body)


def s_income():
    i = F['acs_city']['ind']
    body = f'''
    <div class="grid">
      {card('about $' + rnd(i['median_household_income']), 'median household income', 'Give or take $' + rnd(F['acs_city']['cols']['B19013001'][1]) + ' (2024 dollars, survey margin).')}
      {card('about $' + rnd(i['per_capita_income']), 'income per resident', 'Includes students.')}
      {card(pc(i['below_poverty_pct']), 'of residents below the poverty line', 'Residents in households; students in dorms excluded.')}
      {card(pc(i['bachelors_or_higher_pct']), "of adults 25+ hold a bachelor's degree or more", '')}
    </div>
    <div class="two"><div>{acs_table('B19001', title='Households by income (2024 dollars)')}</div>
    <div>{acs_table('B15003', skip=tuple(f'B15003{k:03d}' for k in range(3, 16)), title='Adults 25 and over by education')}</div></div>
    <p class="note">The income distribution is a barbell: about {rnd(i['hh_income_under_50k'])} households earn under $50,000 and
    about {rnd(i['hh_income_200k_plus'])} earn $200,000 or more. Student households sit in the bottom band. Incomes are published
    for households, never individuals. Education rows for grades 1–11 are folded out of the table (they are in the data file).</p>'''
    return section('income', '3 · Income', 'Household income, poverty and education', body)


def s_age():
    i = F['acs_city']['ind']
    m = lambda a, b: sum(float(ACS[f'B01001{k:03d}']['estimate']) + float(ACS[f'B01001{k + 24:03d}']['estimate']) for k in range(a, b + 1))
    bands = [('Under 5', 3, 3), ('5–17', 4, 6), ('18–19', 7, 7), ('20–21', 8, 9), ('22–24', 10, 10), ('25–34', 11, 12),
             ('35–44', 13, 14), ('45–54', 15, 16), ('55–64', 17, 19), ('65–74', 20, 22), ('75–84', 23, 24), ('85 and over', 25, 25)]
    vals = [(b, m(a, c)) for b, a, c in bands]
    mx = max(v for _, v in vals)
    rows = [[b, rnd(v), pct(v, i['population']), bar(v, mx)] for b, v in vals]
    body = f'''
    {table(['Age', 'Residents', 'Share', ''], rows, right={1, 2})}
    <div class="two"><div>{acs_table('B03002', title='Residents by race and Hispanic origin')}</div>
    <div><p class="note" style="margin-top:2.2rem">One resident in four is 18–24. {n(m(7, 9))} residents are 18–21,
    the undergraduate years. 65 and over: about {rnd(i['age_65_plus'])} ({pct(i['age_65_plus'], i['population'])}).
    Every age column, by sex, is in {dl('acs_city_2024_1yr_all_columns.csv')}; the same bands for each block group are in
    {dl('acs_blockgroup_2020_2024_5yr.csv')}.</p></div></div>'''
    return section('age', '4 · Ages', 'A university city: ages and origins', body)


def s_tide():
    L = F['lodes']
    sec = L['sectors']
    mx = sec[0][1]
    body = f'''
    <div class="grid">
      {card(rnd(L['jobs']), 'jobs located in Berkeley', f"All jobs, {L['year']} (a worker with two jobs counts twice).")}
      {card(rnd(L['inflow']), 'commute in each workday', f"Work here, live elsewhere (about {rnd(L['aux_in'])} from out of state).")}
      {card(rnd(L['outflow'] + L['out_of_state_out']), 'residents commute out', f"About {rnd(L['outflow'])} to jobs elsewhere in California, {rnd(L['out_of_state_out'])} out of state.")}
      {card(rnd(L['interior']), 'live and work here', f"{pct(L['interior'], L['employed_residents'])} of employed residents.")}
    </div>
    <p class="note">By day Berkeley gains about {rnd(L['inflow'] - L['outflow'] - L['out_of_state_out'])} workers, before
    counting {n(CITED['uc']['students'])} students. Counts are jobs covered by unemployment insurance and federal
    employment; the self-employed are not included.</p>
    <div class="two"><div><h3>Where in-commuters live</h3>
      {table(['Home', 'Workers', 'Share'], [[esc(k), rnd(v), pct(v, L['inflow'])] for k, v in L['top_in']], right={1, 2})}
      <p class="note">All {len(csvrows('lodes_2023_inflow_by_home_place.csv'))} places: {dl('lodes_2023_inflow_by_home_place.csv')}</p></div>
    <div><h3>Where out-commuters work</h3>
      {table(['Work', 'Workers', 'Share'], [[esc(k), rnd(v), pct(v, L['outflow'])] for k, v in L['top_out']], right={1, 2})}
      <p class="note">All {len(csvrows('lodes_2023_outflow_by_work_place.csv'))} places: {dl('lodes_2023_outflow_by_work_place.csv')}</p></div></div>
    <div class="two"><div><h3>Jobs in Berkeley by industry</h3>
      {table(['Industry', 'Jobs', 'Share', ''], [[esc(k), rnd(v), pct(v, L['jobs']), bar(v, mx)] for k, v in sec], right={1, 2})}</div>
    <div><h3>Jobs by monthly earnings</h3>
      {table(['Earnings', 'Jobs', 'Share'], [[k, rnd(v), pct(v, L['jobs'])] for k, v in zip(('$1,250 or less', '$1,251–$3,333', 'More than $3,333'), L['earnings'])], right={1, 2})}
      <h3>How residents get to work</h3>
      {acs_table('B08301', skip=('B08301002',) + tuple(f'B08301{k:03d}' for k in range(5, 10)) + tuple(f'B08301{k:03d}' for k in range(11, 16)), title='Means of transportation to work')}
      <p class="note">Sub-modes (carpool sizes, bus vs rail) are in the data file.</p></div></div>
    <p class="note">Maps: jobs by census block, with coordinates and industry: {dl('lodes_2023_jobs_by_block.csv')}
    ({len(csvrows('lodes_2023_jobs_by_block.csv'))} blocks). Jobs and employed residents by block group: {dl('lodes_2023_by_blockgroup.csv')}.</p>'''
    return section('tide', '5 · The daily tide', 'Who comes in, who goes out, and what they do', body)


def s_cars():
    D = F['dmv']
    i = F['acs_city']['ind']
    z = csvrows('dmv_2026_by_zip.csv')
    fuels = [c for c in z[0] if c not in ('ZIP Code', 'total', 'zero_emission_and_plug_in', 'ev_share_pct')]
    fuels = sorted(fuels, key=lambda c: -sum(float(r[c]) for r in z))[:6]
    rows = [[r['ZIP Code'], n(r['total'])] + [n(r[c]) for c in fuels] + [r['ev_share_pct'] + '%'] for r in z]
    fm = max(D['fuel'].values())
    body = f'''
    <div class="grid">
      {card(n(D['total']), 'registered vehicles', f"DMV, as of {D['as_of'][0]}, Berkeley ZIP codes (Albany's 94706 excluded).")}
      {card(n(D['ev']), 'battery-electric, plug-in hybrid or fuel-cell', f"{pct(D['ev'], D['total'])} of vehicles.")}
      {card(rnd(i['households_no_vehicle']), f"households with no car ({pc(i['no_vehicle_pct'])})", 'Census survey 2024.')}
      {card(rnd(i['vehicles_available_min']), 'vehicles kept by households', 'At least; the survey tops out at "5 or more". Close to the DMV count.')}
    </div>
    <h3>Vehicles by ZIP code and fuel</h3>
    {table(['ZIP', 'All'] + fuels + ['Plug-in share'], rows, right=range(1, len(fuels) + 3))}
    <div class="two"><div>{table(['Fuel', 'Vehicles', 'Share', ''], [[esc(k), n(v), pct(v, D['total']), bar(v, fm)] for k, v in D['fuel'].items()], right={1, 2})}</div>
    <div>{acs_table('B25044', title='Vehicles available, by tenure (households)')}</div></div>
    <p class="note"><strong>To which addresses?</strong> Not public: the DMV releases registrations by ZIP code only, and a
    vehicle's registered address is confidential under the Vehicle Code (§1808.21). ZIP codes 94707 and 94708 include
    parts of Kensington and Albany, so ZIP totals slightly overstate Berkeley. Data: {dl('dmv_2026_by_zip.csv')},
    {dl('dmv_2026_by_zip_fuel_duty.csv')}.</p>'''
    Bk = CITED['bikes']
    capb = next(r for r in F['capital']['rows'] if r['category'].startswith('Bike'))
    i = F['acs_city']['ind']
    body += f'''
    <h3>Bikes, e-bikes and scooters</h3>
    <p class="note" style="font-size:.95rem">About {pc(i['commute_bicycle_pct'])} of employed residents bike to work in the 2024 survey, and
    about 7% of those who still commute. Berkeley ranks well above Oakland, San Francisco and Portland, but below the college towns
    it is usually compared with. Its bike share has fallen since 2008–2012, when it was {Bk['berkeley_2008_12']}%, mostly because the
    count now includes the many who work from home. No survey counts bicycles owned in Berkeley; nationally, {Bk['us_ownership']}.</p>
    <div class="two"><div>{table(['City', 'Bike to work, all workers', 'Excluding work from home'], [[c, f"{a:.1f}%", f"{b:.1f}%"] for c, a, b in Bk['compare']], right={1, 2})}</div>
    <div>{table(['Berkeley bikeways', '2017 miles', '2024 miles'], [[k, f"{a}", f"{b}"] for k, a, b in Bk['network']] + [['<strong>Total</strong>', f"<strong>{Bk['network_total'][0]}</strong>", f"<strong>{Bk['network_total'][1]}</strong>"]], right={1, 2})}</div></div>
    <p class="note" style="font-size:.95rem">Shared bikes are growing fast. Trips starting at Berkeley's {Bk['baywheels_stations']} Bay
    Wheels stations rose from {n(Bk['baywheels'][0][1])} in 2024 to {n(Bk['baywheels'][1][1])} in 2025, and {100 * Bk['baywheels'][1][2] / Bk['baywheels'][1][1]:.0f}%
    of the 2025 trips were on e-bikes. The City allows {Bk['scooters']}. {Bk['ava']}.</p>
    <p class="note" style="font-size:.95rem"><strong>What bikeways cost.</strong> Paint is cheap: a national study put the median cost
    of a painted bike lane at about ${Bk['unc_lane_median'] / 1000:.0f},000 a mile. Concrete-separated lanes cost far more, because
    they rebuild curbs, drainage and signals: the Milvia Bikeway's construction contract was ${Bk['milvia'] / 1e6:.1f} million (2021);
    the Southside project, with two-way cycle tracks on Bancroft, Dana and Fulton plus repaving and bus lanes, about
    ${Bk['southside'] / 1e6:.1f} million; and repaving 1.2 miles of Hopkins Street with bikeways is estimated at {Bk['hopkins'][0]}, against
    {Bk['hopkins'][1]} for repaving with pedestrian safety work alone. Separated bikeways grew from 0.1 to 3.6 miles between 2017 and 2024.
    The City's capital plan lists {big(capb['need'])} of bike and pedestrian need and funds {big(capb['available_5yr'])} over five years.
    Safety is the stake: {Bk['vision_zero']}.</p>
    <p class="note">Sources: {esc(Bk['src'])}.</p>'''
    return section('cars', '6 · Cars', 'Cars, bikes and scooters', body)


def s_land():
    A = F['assessor']
    g = sorted(A['by_group'], key=lambda r: -r['parcels'])
    hood = A['by_hood']
    fz = {r['fire_zone']: r for r in A['by_fire']}
    est = A['net'] * 0.012323
    body = f'''
    <div class="grid">
      {card(n(A['parcels']), 'parcels', 'Alameda County Assessor, February 2026.')}
      {card(big(A['net']), 'net taxable assessed value', f"Land {big(A['land'])} + buildings {big(A['imps'])}, less exemptions.")}
      {card(n(A['exempt']), 'parcels fully exempt', 'University, City, schools, churches and other exempt owners.')}
      {card('≈ ' + big(est), 'a year in base property tax, all agencies', 'Estimate: net value × the 1.2323% FY2025-26 rate; parcel taxes are extra.')}
    </div>
    <p class="note">Under Proposition 13, assessed value follows the purchase price plus at most 2% a year, so it sits far
    below market value, most of all for long-held homes.</p>
    <div class="two"><div><h3>By County use code group</h3>
      {table(['Use code', 'Parcels', 'Exempt', 'Net taxable'], [[r['use_group'], n(r['parcels']), n(r['exempt_parcels']), big(r['net_taxable_value'])] for r in g], right={1, 2, 3})}
      <p class="note">1xxx are single-family homes and 2xxx small multi-unit buildings; the County publishes its code list
      only as a web page that refuses automated reading, so the other groups are left unlabeled here. All
      {len(csvrows('assessor_by_usecode.csv'))} codes: {dl('assessor_by_usecode.csv')}</p></div>
    <div><h3>By hill fire zone</h3>
      {table(['Zone', 'Parcels', 'Exempt', 'Net taxable'], [[{0: 'Outside the layer', 1: 'Zone 1 (flatlands)', 2: 'Zone 2 (hills)', 3: 'Zone 3 (hills)'}[k], n(r['parcels']), n(r['exempt_parcels']), big(r['net_taxable_value'])] for k, r in sorted(fz.items())], right={1, 2, 3})}</div></div>
    <h3>By neighborhood</h3>
    {table(['Neighborhood', 'Parcels', 'Exempt', 'Land', 'Buildings', 'Net taxable', 'Per parcel'],
           [[esc(r['neighborhood']), n(r['parcels']), n(r['exempt_parcels']), big(r['land_value']), big(r['improvement_value']), big(r['net_taxable_value']), usd(r['net_taxable_value'] / r['parcels'])] for r in hood],
           right=range(1, 7))}
    <p class="note">Neighborhoods are the City's own boundaries; parcels outside every polygon are not in this table.
    Maps: {dl('assessor_by_blockgroup.csv')}, {dl('assessor_by_neighborhood.csv')}, {dl('assessor_by_fire_zone.csv')}.</p>'''
    return section('land', '7 · Land and money', 'Parcels and taxable value', body)


def s_city():
    C = CITED['city']
    K = F['capital']
    rows = sorted(K['rows'], key=lambda r: -r['need'])
    cap_rows = [[esc(r['category']), big(r['need']), big(r['available_5yr']) if r['available_5yr'] else '$0',
                 f"{100 * r['available_5yr'] / r['need']:.0f}%" if r['need'] else '—', big(r['unfunded_fy2031'])] for r in rows]
    cap_rows.append(['<strong>All categories</strong>', f"<strong>{big(K['total']['need'])}</strong>", f"<strong>{big(K['total']['available_5yr'])}</strong>",
                     f"<strong>{100 * K['total']['available_5yr'] / K['total']['need']:.0f}%</strong>", f"<strong>{big(K['total']['unfunded_fy2031'])}</strong>"])
    allf = json.load(open(os.path.join(ROOT, 'data', 'reference', 'berkeley_budget_external_facts_2026-08-15.json')))['spend_fy2027_adopted']['by_department']
    gf = dict(C['dept_gf'])
    alias = {'Health, Housing & Community Services': 'Health, Housing & Community Services', 'Parks, Recreation & Waterfront': 'Parks, Recreation & Waterfront', 'Planning & Development': 'Planning and Development'}
    dept_rows = [[esc(d), big(v), big(gf[k]) if (k := next((g for g in gf if alias.get(g, g) == d), None)) else '—'] for d, v in sorted(allf.items(), key=lambda t: -t[1])[:12]]
    fte_rows = [[esc(d), f"{a:,.2f}".rstrip('0').rstrip('.'), f"{b:,.2f}".rstrip('0').rstrip('.'), f"{b - a:+,.2f}".rstrip('0').rstrip('.') if b != a else '0'] for d, a, b in C['fte']]
    fte_rows.append(['<strong>Total</strong>', f"<strong>{C['fte_total'][0]:,.2f}</strong>", f"<strong>{C['fte_total'][1]:,.2f}</strong>", f"<strong>{C['fte_total'][1] - C['fte_total'][0]:+,.2f}</strong>"])
    body = f'''
    <div class="grid">
      {card(big(C['all_funds']), 'City spending, all funds (FY2027)', f"{big(C['general_fund'])} of it from the General Fund, the part taxes pay for.")}
      {card(f"{C['fte_total'][1]:,.0f}", 'City employees (full-time equivalent)', f"Down {C['cut_fte']:.0f} from {C['fte_total'][0]:,.0f} in FY2026; {C['fte_gf']:.0f} paid by the General Fund.")}
      {card(f"${C['deficit_fy27'] / 1e6:.1f} million", 'General Fund deficit, FY2027 (before one-time money)', f"${C['deficit_fy28'] / 1e6:.1f} million projected for FY2028.")}
      {card(big(K['total']['need']), "capital need in the City's own five-year plan", f"{big(K['total']['available_5yr'])} is funded over the five years; the unfunded gap stays above $2.1 billion every year.")}
    </div>
    <h3>Staff, by department</h3>
    {table(['Department', 'FY2026 adopted', 'FY2027 adopted', 'Change'], fte_rows, right={1, 2, 3})}
    <p class="note">The FY2027 budget cuts {C['cut_fte']:.2f} positions: 45 vacant positions frozen in FY2026, 85 more vacant and 20
    filled. Police lose 30 positions and Fire 24. Another 33 positions are carried on one-time money pending a proposed sales tax;
    without it, the cut reaches {C['cut_if_no_tax']} positions.</p>
    <div class="two"><div><h3>Spending by department (FY2027 adopted)</h3>
    {table(['Department', 'All funds', 'General Fund'], dept_rows, right={1, 2})}
    <p class="note">All funds include fee-supported services such as sewers, refuse and permits, which is why Public Works spends
    far more than its General Fund share. A dash means the department is not among the General Fund departments the budget
    summary lists; the Library, for one, runs on its own parcel tax.</p></div>
    <div><h3>General Fund deficits, as the City reports them</h3>
    {table(['Fiscal year', 'Deficit'], [[y, f"${d} million"] for y, d in C['deficits']] + [['2027 (projected)', f"${C['deficit_fy27'] / 1e6:.1f} million"], ['2028 (projected)', f"${C['deficit_fy28'] / 1e6:.1f} million"]], right={1})}
    <p class="note">Each year's budget was balanced on paper with reserves, one-time federal money, vacancy savings or deferred
    projects. The City's own presentation: "These approaches never addressed the underlying structural deficit."</p></div></div>
    <h3>Pensions and overtime</h3>
    {table(['CalPERS plan', 'Unfunded liability (6/30/2025)', 'Funded', 'A year earlier'], [[p, big(u), f"{f}%", f"{g}%"] for p, u, f, g in C['calpers']], right={1, 2, 3})}
    <p class="note" style="font-size:.95rem">The City paid CalPERS {big(C['pension_paid_fy2025'])} in FY2025, up from
    {big(C['pension_paid_fy2016'])} in FY2016; the City Auditor cites a forecast rising "from {C['pension_forecast']}." The police
    plan's employer rate is above 80% of payroll. Overtime: the Police Department expected about {big(C['ot_police_fy2025'])} in
    FY2025, 40% of it to backfill minimum staffing, and Fire about {big(C['ot_fire_fy2025'])}; the Auditor found a
    "{C['ot_increase']}," and that police overtime exceeded its budget three years running.</p>
    <h3>The capital gap, by the City's own count</h3>
    {table(['Category', 'Need', 'Funded, 5 years', 'Share funded', 'Unfunded by FY2031'], cap_rows, right={1, 2, 3, 4})}
    <p class="note" style="font-size:.95rem">The City's five-year capital plan puts its total need at {big(K['total']['need'])} and funds
    {big(K['total']['available_5yr'])}. Because the funded work only keeps pace with inflation, the unfunded gap does not shrink:
    ${K['total']['unfunded_fy2027'] / 1e9:.2f} billion in FY2027, ${K['total']['unfunded_fy2031'] / 1e9:.2f} billion in FY2031. Public Works separately reports
    "{big(C['deferred_maint'])} in deferred maintenance costs and needed improvements." Sewers are the one category close to funded,
    paid by sewer fees; undergrounding, the Veterans Building and Old City Hall get nothing. Streets average a pavement
    condition of {C['pci']}; the five-year paving plan costs ${C['paving_plan'] / 1e6:.0f} million.</p>
    <p class="note" style="font-size:.95rem"><strong>Measure U against the need.</strong> The $300 million bond on the November 2026
    ballot would fund {big(C['bond_projects'])} of projects (parks {big(C['bond_parks'])}, public works {big(C['bond_pw'])}, fire
    {big(C['bond_fire'])}) plus {big(C['bond_staffing'])} for staffing and delivery. Issued in stages from 2027 and repaid through
    FY2066–67, it costs ${C['bond_debt_service'] / 1e6:.0f} million in debt service. That is about {100 * C['bond'] / K['total']['need']:.0f}% of the need the City
    itself lists, and it includes no undergrounding. Vision 2050 had put the unfunded need at $882 million in 2020.
    Data: {dl('city_capital_needs_fy2027_2031.csv')}.</p>
    <p class="note">Sources: {esc(C['src'])}.</p>'''
    return section('city', '8 · The City\'s money', 'Staff, pensions, deficits and the capital gap', body)


def s_business():
    B = F['business']
    L = F['lodes']
    blt = json.load(open(os.path.join(ROOT, 'data', 'reference', 'berkeley_budget_external_facts_2026-08-15.json')))['revenues_fy2025_actual']['business_license_tax']
    t_rows = [[esc(r['type']), n(r['licenses']), n(r['located_in_berkeley'])] for r in B['by_type']]
    body = f'''
    <div class="grid">
      {card(n(B['licenses']), 'active business licenses (November 2025)', f"{n(B['located'])} of them at a Berkeley address; the rest are mostly contractors and firms based elsewhere that work here.")}
      {card(f"${blt / 1e6:.1f} million", 'business license tax collected (FY2025)', 'City annual financial report.')}
      {card(rnd(L['jobs']), 'jobs located in Berkeley (2023)', f"About {rnd(L['sectors'][0][1])} of them in education, mostly the University.")}
    </div>
    <div class="two"><div><h3>Licenses by type</h3>
    {table(['Type', 'Licenses', 'At a Berkeley address'], t_rows, right={1, 2})}</div>
    <div><h3>Where they are</h3>
    {table(['Neighborhood', 'Businesses'], [[esc(r['neighborhood']), n(r['all_businesses'])] for r in B['by_hood']], right={1})}
    <h3>Most common local businesses</h3>
    {table(['Kind (industry code)', 'Licenses'], [[esc(k), n(v)] for k, v in B['top_naics'][:10]], right={1})}</div></div>
    <p class="note" style="font-size:.95rem">Berkeley's licensed businesses are mostly small: {n(B['ownership'].get('Sole Ownership', 0))}
    are sole proprietorships, {n(B['ownership'].get('Corporation', 0))} corporations and {n(B['ownership'].get('LLC', 0))} limited
    liability companies. Landlords are the second-largest group ({n(next(r['licenses'] for r in B['by_type'] if r['type'].startswith('Rental')))}
    rental-property licenses). Among businesses at a Berkeley address, therapists' and counselors' offices are the most common
    kind, followed by restaurants, beauty salons, architects and lawyers: a city of services, shops and professional practices
    around a university and a national laboratory. The neighborhood and type tables exclude rental-property licenses.</p>
    <p class="note">Source: City of Berkeley open data, Business Licenses (downloaded November 15, 2025); locations from the
    Alameda County Assessor's parcels. Maps: {dl('businesses_by_blockgroup.csv')}, {dl('businesses_by_neighborhood.csv')},
    {dl('business_licenses_by_type.csv')}.</p>'''
    return section('business', '0 · Businesses', 'The businesses: what they are and where', body)


def s_innovation():
    T = F['dmv_trend']
    Bk = CITED['bikes']
    i = F['acs_city']['ind']
    body = f'''
    <p class="note" style="font-size:.95rem">Several changes already under way will reshape how Berkeley uses its streets, pipes and
    power lines.</p>
    {table(['Change', 'Where it stands', 'What it changes'], [
        ['Electric vehicles', f"{n(T['2026']['plug_in'])} plug-in vehicles in Berkeley ZIP codes (January 2026), up from {n(T['2021']['plug_in'])} five years earlier; fully electric cars nearly tripled", 'Charging load on neighborhood transformers; less gasoline sold'],
        ['Working from home', f"About a third of employed residents ({pc(i['commute_work_from_home_pct'])}) work from home", 'Fewer peak-hour trips; more daytime demand for power and water at home'],
        ['E-bikes and shared mobility', f"Bay Wheels trips from Berkeley stations up 53% in 2025, three-quarters on e-bikes; up to 1,200 shared scooters and e-bikes permitted", 'More riders on streets built for cars; demand for protected lanes'],
        ['Electric campus', 'UC Berkeley\'s Clean Energy Campus: heat-pump plant and 2-million-gallon thermal tank under North Field, 2027–2030', 'Retires a gas plant that emits about 114,000 tonnes of CO\u2082e a year'],
        ['Undergrounding', 'PG&amp;E\'s ten-year plan (September 2026): about 5,000 miles statewide, 2028–2037', 'Fewer poles to fall in a fire or earthquake, if Berkeley\'s streets are included'],
        ['Seismic and fire codes', 'Soft-story retrofits nearly complete; 2025 ember-resistant zone ordinance in the hills', 'Fewer collapses and house-to-house fire spread'],
        ['Autonomous vehicles and home delivery', 'Not counted by any public source in Berkeley', 'Curb space, traffic and parking; flagged by the City\'s 2017 Drawdown list'],
    ])}
    <p class="note" style="font-size:.95rem">Vision 2050 anticipated most of these in 2020: buildings that make and store their own
    energy, transportation that must "become electrified," ride-hailing and micro-mobility that "will become more prevalent," and
    microgrids "capable of providing electricity even when the larger grid is down." What it could not foresee was the scale of
    working from home, now about as common as driving alone to work. Sources: DMV registrations by ZIP code (January 2021 and
    January 2026); the sections above.</p>'''
    return section('innovation', '0 · Innovations to come', 'What is changing next', body)


def s_networks():
    I = F['infra']
    S = CITED['streets']
    wd = I['water_by_decade']
    wmx = max(r['miles'] for r in wd)
    sm = sorted(I['sewer_by_material'], key=lambda r: -r['miles'])[:10]
    stm = sorted(I['storm_by_material'], key=lambda r: -r['miles'])[:8]
    poles = {r['POLEMAT']: r['streetlights'] for r in I['poles']}
    P = F['poles']
    tr = P['traced']
    over = sum((a - b) for a, b in CITED['table1_ft'].values()) / 5280
    lo, hi = over * 5280 / tr['250']['mean_span_ft'], over * 5280 / tr['200']['mean_span_ft']
    body = f'''
    {table(['Network', 'Miles', 'Detail'], [
        ['Streets', n(S['centerline_mi'], 1), f"{n(S['lane_mi'], 1)} lane-miles; arterials {S['arterial_mi']} mi, collectors {S['collector_mi']}, residential {S['residential_mi']}; average pavement condition {S['pci']} of 100."],
        ['Water mains (EBMUD)', n(I['water_mi'], 1), f"Pressurized mains owned by EBMUD, not the City, in 15 of EBMUD's 120 pressure zones. Half the pipe segments were laid before {I['water_median_year']}; {n(I['water_pre1940_mi'], 1)} miles before 1940; the oldest in the {I['water_oldest'] // 10 * 10}s."],
        ['Sanitary sewer mains (City)', n(I['sewer_mi'], 1), f"{n(I['sewer_segments'])} segments, {n(I['manholes'])} manholes, {n(I['laterals'])} house laterals ({n(I['laterals_mi'], 1)} mapped miles); {CITED['ssmp']['pump_stations']} pump stations; {CITED['ssmp']['rehab_since_1986']} miles rehabilitated since 1986."],
        ['Storm drains (City)', n(I['storm_mi'], 1), f"{n(I['storm_segments'])} pipe segments."],
        ['Gas, high pressure (PG&amp;E)', '≈ 38', 'Lines at 60 psi and above only; the low-pressure mains that feed houses are not public.'],
        ['Utility poles (PG&amp;E, AT&amp;T)', f"{n(poles.get('Wood', 0))}+", f"Wood poles carrying a City streetlight; about {round(lo, -2):,.0f}–{round(hi, -2):,.0f} poles in all line the streets (below)."],
    ], right={1})}
    <p class="note">Two City-commissioned counts of street miles disagree by 5 miles: 214.2 in the 2022 pavement survey and
    219.4 in the 2016 undergrounding study. Neither report explains the difference; they were measured six years apart for
    different purposes.</p>
    <p class="note">The City's sewer map prices every segment at a planning cost per foot by diameter: {big(I['sewer_planning_cost'])}
    for the whole network, including the {n(sum(r['segments'] for r in I['sewer_by_material'] if r['MATERIAL'] == 'HDPE'))} segments
    already relined with plastic (HDPE). It is a replacement value at the City's unit costs, not a backlog.</p>
    <h3>Who owns which pipes</h3>
    {table(['System', 'Owner', 'What it covers'], [
        ['Water supply and mains', 'EBMUD', 'Reservoirs and tanks, treatment, the 269 miles of pressurized mains under Berkeley, and meters; EBMUD serves about 1.5 million people'],
        ['Sanitary sewers', 'City of Berkeley', '254 miles of mains, about 7,200 manholes, 7 pump stations, and the lower half of each house lateral, from the property-line cleanout to the main'],
        ['House sewer laterals (upper half)', 'Each property owner', 'From the house to the cleanout; a lateral certificate is required at sale (Berkeley\'s own program, separate from EBMUD\'s)'],
        ['Interceptors and treatment', 'EBMUD', 'The large pipes that collect sewage from Berkeley and six other cities, the Main Wastewater Treatment Plant at the foot of the Bay Bridge, and three wet-weather facilities'],
        ['Storm drains', 'City of Berkeley', 'About 93 miles of pipe and 5,800 structures, separate from the sewers'],
        ['Electricity and gas', 'PG&amp;E', 'Poles, wires, transformers and gas mains; Ava Community Energy, the public power provider Berkeley belongs to, buys power for customers who have not opted out'],
    ])}
    <p class="note" style="font-size:.95rem"><strong>How water reaches a tap.</strong> EBMUD's system is built on height. Its service
    area is divided into 120 pressure zones, from sea level to 1,450 feet; water is pumped up to tanks and reservoirs high in the
    hills, and flows down by gravity from zone to zone. About 60% of EBMUD's treated water reaches
    customers by gravity alone; 133 pumping plants lift the rest. Berkeley's mains fall in 15 of those zones (EBMUD 2025 Urban Water
    Management Plan; zone codes from the mapped mains).</p>
    <p class="note">Rain that leaks into old sewers is the overlap: in storms it overwhelms EBMUD's plant, and a 2014 federal consent
    decree requires the region to cut that inflow enough to end wet-weather discharges by 2035. Sources: City Sewer System
    Management Plan (2019); EBMUD 2025 Urban Water Management Plan and private sewer lateral program (2021); EBMUD consent decree
    (2014); City private sewer lateral guide; adopted FY2027–28 budget.</p>
    <h3>Overhead wire, poles and transformers</h3>
    {table(['Measure', 'Value', 'Basis'], [
        ['Street miles with overhead lines', f"{over:.1f}", 'Measured (City study, 2016)'],
        ['Lit wood poles, located', n(P['wood']), "Measured (City streetlight map)"],
        ['Distance to the nearest lit wood pole', f"median {P['nn_median_ft']} ft", 'Measured'],
        ['Pole line traced by lit poles alone', f"{tr['250']['miles']:.0f}–{tr['400']['miles']:.0f} mi", 'Measured; a floor<sup>a</sup>'],
        ['Utility poles along streets', f"≈ {round(lo, -2):,.0f}–{round(hi, -2):,.0f}", 'Estimate<sup>b</sup>'],
        ['Transformers serving homes', '≈ 7,000–8,000', 'Estimate<sup>c</sup>'],
        ['All transformers, including businesses, campus and Lab', 'not public; could approach or pass 10,000', 'Held by PG&amp;E; not public'],
        ['Aerial cable route-miles', f"≈ {4 * over:,.0f}", 'Illustration<sup>d</sup>'],
    ])}
    <p class="note"><sup>a</sup> Links between neighboring lit wood poles up to 250–400 feet apart; poles without a streetlight break
    the chain. <sup>b</sup> {over:.1f} overhead street miles divided by the traced spans of {tr['200']['mean_span_ft']:.0f}–{tr['250']['mean_span_ft']:.0f}
    feet; rear-lot pole lines are additional. <sup>c</sup> PG&amp;E's "average number of customers per residential transformer is 7"
    (2027 rate case, rebuttal testimony) over Berkeley's {rnd(F['dof']['rows'][-1]['occupied'])}–{rnd(F['dof']['rows'][-1]['housing_units'])}
    homes; pole-top and underground units. <sup>d</sup> {over:.0f} miles × four systems on a typical shared pole (electric, telephone
    copper, cable TV coax, fiber).</p>
    <p class="note" style="font-size:.95rem"><strong>The transformers.</strong> Distribution transformers are filled with mineral oil.
    Under federal rules (40 CFR 761.2), any made before July 2, 1979 whose PCB content has not been tested must be presumed
    PCB-contaminated, so the age of each unit matters, and PG&amp;E does not publish it. System-wide, PG&amp;E told regulators it is
    "tracking over 67,000 overloaded service transformers" while replacing 400 to 488 a year. Its wildfire filing counts 1,126
    leaking-transformer events, none of which started a fire: the risk is oil on the ground, not ignition.</p>
    <p class="note">What would replace the estimates with counts: PG&amp;E's pole and joint-use attachment records (its Joint Use
    Map Portal is closed to the public), which list every pole and every company attached to it. Wiring for traffic signals,
    sewer pump stations and water valves is not mapped publicly at all. Map layer: {dl('wood_pole_lines_traced.geojson')}.</p>
    <div class="two"><div><h3>Water mains by decade laid</h3>
      {table(['Decade', 'Miles', ''], [[f"{int(r['decade'])}s" if r['decade'] is not None else 'unknown', n(r['miles'], 1) if r['miles'] >= 0.05 else 'under 0.1', bar(r['miles'], wmx)] for r in wd], right={1})}</div>
    <div><h3>Water mains by diameter</h3>
      {table(['Inches', 'Miles'], [[f"{r['diameter_in']:g}", n(r['miles'], 1) if r['miles'] >= 0.05 else 'under 0.1'] for r in I['water_by_dia']], right={0, 1})}
      <p class="note">The pipe-material field is empty in the public layer.</p></div></div>
    <div class="two"><div><h3>Sewer mains by material</h3>
      {table(['Material', 'Miles', 'Segments'], [[esc(str(r['MATERIAL'])), n(r['miles'], 1), n(r['segments'])] for r in sm], right={1, 2})}
      <p class="note">HDPE and CIPP are relined pipe; VCP is the original vitrified clay.</p></div>
    <div><h3>Storm drains by material</h3>
      {table(['Material', 'Miles'], [[esc(str(r['MATERIAL'])), n(r['miles'], 1)] for r in stm], right={1})}
      <h3>Streetlights by pole material</h3>
      {table(['Pole', 'Streetlights'], [[esc(k), n(v)] for k, v in sorted(poles.items(), key=lambda t: -t[1])], right={1})}</div></div>
    <p class="note">Maps: miles of water main (and pre-1940 miles), sewer main and storm drain, and wood poles, for every
    block group and neighborhood: {dl('infrastructure_by_blockgroup.csv')}, {dl('infrastructure_by_neighborhood.csv')}.
    The segment-level layers are the City's own GIS services (PubWorks MapServer).</p>'''
    return section('networks', '8 · Under the streets', 'Streets, pipes and poles', body)


def s_ug():
    U = F['ug']
    S = U['summary']
    C = CITED['ug']
    d = U['disagree'][0] if U['disagree'] else None
    b19 = [r for r in U['bellecci'] if r['version'].startswith('FY2019')]
    b23 = {r['street']: r for r in U['bellecci'] if r['version'] == 'FY2023, programmatic'}
    bc = {r['street']: r for r in U['bellecci'] if r['version'].endswith('capital program')}
    rn = S['report_network_totals']
    T1 = CITED['table1_ft']
    over = sum(a - b for a, b in T1.values()) / 5280
    t1 = {k: (a / 5280, b / 5280, (a - b) / 5280) for k, (a, b) in T1.items()}
    tot = [sum(v[i] for v in t1.values()) for i in range(3)]
    t1rows = [[k.title(), f"{v[0]:.1f}", f"{v[1]:.1f}", f"{v[2]:.1f}", f"{100 * v[1] / v[0]:.0f}%"] for k, v in t1.items()]
    t1rows.append(['<strong>All streets</strong>', f"<strong>{tot[0]:.1f}</strong>", f"<strong>{tot[1]:.1f}</strong>",
                   f"<strong>{tot[2]:.1f}</strong>", f"<strong>{100 * tot[1] / tot[0]:.0f}%</strong>"])
    body = f'''
    <div class="grid">
      {card(f"{tot[2]:.0f} of {tot[0]:.0f} mi", 'of Berkeley streets still carry overhead wires', f"{100 * tot[2] / tot[0]:.0f}% of street miles; {tot[1]:.1f} miles are underground (2016).")}
      {card(f"{t1['residential'][2]:.0f} mi", 'of them are residential streets', f"Only {100 * t1['residential'][1] / t1['residential'][0]:.0f}% of residential street miles are underground. The cost studies price only arterials and collectors.")}
      {card(f"{S['arterial']['underground_mi'] + S['collector']['underground_mi']:.1f} mi", 'of arterials and collectors already underground', f"Arterials {S['arterial']['underground_mi']:.1f} of {S['arterial']['underground_mi'] + S['arterial']['overhead_mi']:.1f} mi; collectors {S['collector']['underground_mi']:.1f} of {S['collector']['underground_mi'] + S['collector']['overhead_mi']:.1f}.")}
      {card(f"{S['arterial']['overhead_mi'] + S['collector']['overhead_mi']:.1f} mi", 'of arterials and collectors still overhead', 'The part the cost studies price (2016).')}
      {card(big(U['total']), 'to underground them, segment by segment', 'Harris & Associates, 2016 dollars, construction only.')}
      {card(big(sum(r['total_cost'] for r in b19)), 'for 16.9 miles of evacuation routes', 'Bellecci, FY2019 dollars; ' + big(sum(r['total_cost'] for r in bc.values())) + ' as a FY2023 capital program.')}
    </div>
    <p class="note" style="font-size:.95rem"><strong>Why it matters.</strong> The City's 2018 study makes the safety case: "Undergrounded
    wires don't fall down and block roadways." In the 1991 Oakland fire, as FEMA documented, "live power lines fell from burning poles,
    blocking streets and starting new fires," and when power to pumping stations was lost, firefighters ran out of water. First
    responders "will not drive over fallen power lines" until the utility confirms they are dead. In an earthquake, "poles have a
    tendency to sway in opposite directions causing wires to snap and throw sparks." Most of the overhead miles are residential
    streets, including the narrow hill streets that are the only ways out of the fire zones.</p>
    <h3>Every street, by class: underground and overhead (miles, 2016)</h3>
    {table(['Streets', 'Total', 'Underground', 'Overhead', 'Share underground'], t1rows, right=range(1, 5))}
    <p class="note">Miles computed from the feet in Table 1 of the City's 2016 study (the table prints 149.9 overhead
    residential miles; its feet give 146.9). The study measured residential streets but priced only arterials and collectors,
    and we found no City study that prices the rest. Lines along rear lot lines are not street miles and are not counted. We
    computed the 34.6 underground miles (16%) from the study's own feet, before reading the City's 2024 hazard plan; the plan
    gives the same figures.</p>
    <h3>The 2016 segment table: what it costs, street by street</h3>
    {table(['Network', 'Segments', 'Overhead', 'Underground', 'Cost (segments)', 'Report\'s printed total'], [
        ['Arterial', S['arterial']['segments'], f"{S['arterial']['overhead_mi']:.1f} mi", f"{S['arterial']['underground_mi']:.1f} mi", usd(S['arterial']['cost']), usd(sum(rn['arterial']))],
        ['Collector', S['collector']['segments'], f"{S['collector']['overhead_mi']:.1f} mi", f"{S['collector']['underground_mi']:.1f} mi", usd(S['collector']['cost']), usd(sum(rn['collector']))],
        ['<strong>Total</strong>', S['arterial']['segments'] + S['collector']['segments'], '', '', f"<strong>{usd(U['total'])}</strong>", f"{usd(sum(rn['arterial']) + sum(rn['collector']))} (headline {big(rn['headline'])})"],
    ], right=range(1, 6))}
    <p class="note">{f"The table prices {esc(d['street'].title())}'s five residential-zone segments at {usd(d['segments_residential'])}, then leaves them out of the street's total row ({usd(d['cost_residential'])}) and the arterial total." if d else ''}
    The collector network adds up to the dollar. Costs are construction only, in 2016 dollars: no private-property trenching,
    service conversions, engineering, financing or street lighting.</p>
    <h3>The 15 costliest overhead segments</h3>
    {table(['Street', 'From', 'To', 'Feet', 'Impact (3–15)', 'Cost'], [[esc(r['street'].title()), esc(r['seg_from'].title()), esc(r['seg_to'].title()), n(r['length_ft']), r['impact_total'], usd(r['cost_total'])] for r in U['top']], right={3, 4, 5})}
    <h3>Evacuation routes, 2019: cost per street</h3>
    {table(['Street', 'Complexity (1–5)', 'Overhead mi', 'FY2019', 'FY2023 program', 'FY2023 capital plan'],
           [[esc(r['street']), r['complexity_level'] or '—', n(r['overhead_centerline_miles'], 2), usd(r['total_cost']), usd(b23[r['street']]['total_cost']), usd(bc[r['street']]['total_cost'])] for r in sorted(b19, key=lambda r: -r['total_cost'])],
           right=range(1, 6))}
    <p class="note">A mile costs $4.08 million on the simplest streets and $6.8 million on the hardest, lighting included. The
    City's 2018 Conceptual Study put its own share at {C['conceptual_per_mile']} a mile, {C['conceptual_range']} for all 37.9
    miles. PG&amp;E ratepayer credits (Rule 20A) bring Berkeley about {usd(C['harris_rule20a_per_year'])} a year; the
    {usd(C['bellecci_rule20a_balance'])} balance in 2019 was mostly committed to Underground Utility District 48 in the hills
    (Grizzly Peak, Summit, Senior, Avenida: {C['uud48_parcels']} parcels).</p>
    <h3>What comes next, and what it would cost</h3>
    <p class="note" style="font-size:.95rem">The money that paid for most past undergrounding is ending. PG&amp;E ratepayer credits
    under Rule 20A stopped accruing after 2022 under a 2021 state utilities commission decision, and unused credits expire by the
    end of 2033. Underground Utility District 48 in the hills, started in June 2023, is due to finish in 2026. The City's five-year
    capital plan budgets $0 for undergrounding each year against a $124.5 million need, and Measure U includes none. In January
    2024 the Council asked PG&amp;E to underground its lines in Berkeley's highest fire-risk zone, noting that a 2021 request
    got no reply. PG&amp;E's ten-year undergrounding plan, filed September 30, 2026, would bury about 5,000 miles statewide between
    2028 and 2037; its first projects include one in Alameda County, in Oakland, and none in Berkeley that we could identify.</p>
    <p class="note" style="font-size:.95rem">For scale only: at the per-mile costs now in use, from PG&amp;E's own recent average of
    $3.25 million to the City's 2019 average of $6.1 million (lighting included), burying the wires on all {over:.0f} overhead street
    miles would cost roughly ${over * 3.25 / 1000:.1f} to ${over * 6.1 / 1000:.1f} billion, before inflation. The evacuation routes alone,
    16.9 miles, were priced at ${sum(r['total_cost'] for r in bc.values()) / 1e6:.0f} million as a FY2023 capital program.</p>
    <p class="note">Sources: CPUC decisions D.21-06-013 and D.23-06-008; adopted FY2027–28 budget; Council item 28, January 30,
    2024; PG&amp;E 10-Year Electric Undergrounding Plan, Volume 1 (September 30, 2026).</p>
    <p class="note">Maps: {dl('undergrounding_segments_harris_2016.csv')} ({len(csvrows('undergrounding_segments_harris_2016.csv'))}
    segments, each named by street, from and to) and {dl('undergrounding_evacuation_routes_bellecci_2019.csv')}.</p>'''
    return section('undergrounding', '9 · Undergrounding', 'What it costs to bury the wires', body)


def s_water_energy():
    B = F['beso']
    E = CITED['ebmud']
    pop = F['dof']['rows'][-1]['population']
    mgd = E['potable_2025_mg'] / 365                      # district potable use, million gallons a day
    est = mgd * pop / E['served']
    y = B['years']
    bt = B['by_type']
    hh_gal = CITED['water_household']['ccf_month'] * 748 / 30.4
    body = f'''
    <div class="grid">
      {card(f'≈ {est:.0f} million', 'gallons of water a day (estimate)', f"EBMUD's {mgd:.0f} million gallons a day × Berkeley's share of its {n(E['served'])} customers. EBMUD does not publish use by city.")}
      {card(f'~{hh_gal:.0f}', 'gallons a day, a typical Berkeley household', '"About 5 CCF per month" (EBMUD to the City Council, 2019).')}
      {card(f"{y['2024']['kwh'] / 365 / 1000:,.0f} MWh", 'electricity a day, large buildings alone', f"{y['2024']['kwh'] / 1e6:,.0f} million kWh in 2024 across {y['2024']['kwh_n']} buildings over 25,000 sq ft.")}
      {card(f"{CITED['cap']['elec']}% / {CITED['cap']['gas']}%", 'citywide electricity / gas use since 2000', 'City Climate Action Plan report, April 2025.')}
    </div>
    <div class="two"><div><h3>EBMUD district water use, 2025</h3>
      {table(['Use', 'Million gallons', 'Share'], [[k, n(v), pct(v, E['potable_2025_mg'])] for k, v in E['use_2025_mg']] + [['<strong>Potable total</strong>', f"<strong>{n(E['potable_2025_mg'])}</strong>", '']], right={1, 2})}
      <p class="note">The whole district (about {n(E['served'])} people), not Berkeley: {n(E['pipe_mi'])} miles of pipe, {E['pumping']} pumping plants,
      {E['reservoirs']} distribution reservoirs (2025 Urban Water Management Plan, Table 4-1).</p></div>
    <div><h3>Water storage inside Berkeley</h3>
      {table(['Reservoir or tank', 'Where', 'Capacity', 'Source'], [[esc(a), esc(b), esc(c), esc(d)] for a, b, c, d in CITED['reservoirs']])}
      <p class="note">EBMUD publishes no list of its tanks by city; the count (about six to eight sites) awaits its confirmation.</p></div></div>
    <h3>Large buildings: energy reported under the City's Building Emissions Saving Ordinance</h3>
    {table(['Year', 'Buildings reporting electricity', 'Electricity (kWh)', 'Buildings reporting gas', 'Gas (therms)'],
           [[yy, n(y[yy]['kwh_n']), n(y[yy]['kwh']), n(y[yy]['therms_n']), n(y[yy]['therms'])] for yy in sorted(y)], right=range(1, 5))}
    {table(['Building type (2024)', 'Buildings', 'Floor area (sq ft)', 'Electricity (kWh)', 'Gas (therms)'],
           [[esc(r['property_type']), n(r['buildings']), n(r['floor_area_sqft']), n(r['electricity_kwh_2024']), n(r['gas_therms_2024'])] for r in bt], right=range(1, 5))}
    <p class="note">Year-to-year totals move with the number of buildings reporting. The City's file labels gas for 2021–2023
    as kBtu, but its own energy-intensity figures are reproduced only if those values are therms, so they are treated as
    therms here. Every building, with address, type, floor area, use 2021–2024 and ENERGY STAR score, located on its
    Assessor parcel ({n(B['located'])} of {n(B['buildings'])}): {dl('beso_large_buildings_energy.csv')}.</p>
    <h3>Can use be seen by building, block, street or neighborhood?</h3>
    {table(['Grain', 'Electricity and gas', 'Water'], [
        ['Citywide', '<span class="part">Trend public (City); totals by ZIP from PG&amp;E</span>', '<span class="no">Not published; estimate only</span>'],
        ['ZIP code / neighborhood', '<span class="yes">Yes: by ZIP, month and customer class</span>', '<span class="no">No</span>'],
        ['Street or block', '<span class="no">No: groups must have 100 homes or 15 businesses (CPUC rule)</span>', '<span class="no">No</span>'],
        ['Building', f'<span class="part">Only buildings over 25,000 sq ft (about {B["buildings"]})</span>', '<span class="no">No: accounts are confidential</span>'],
    ])}
    <p class="note">PG&amp;E's ZIP-code files sit behind a short registration form (CPUC decision D.14-05-016) and have not yet been downloaded.
    Finer grain needs a request: aggregated use by block group from PG&amp;E, or the City's metered total from EBMUD under the Public Records Act.</p>'''
    return section('water-energy', '10 · Water and power', 'What the city uses, and what can be known', body)


def s_fire():
    K = CITED['kld']
    E = F['evac']
    fz = {r['fire_zone']: r for r in F['assessor']['by_fire']}
    sc = ['summer_midweek_midday', 'summer_weekend_midday', 'summer_nighttime', 'fall_midweek_midday', 'fall_weekend_midday', 'fall_nighttime']
    rows = [[f"{r['region']} {esc(r['name'])}"] + [r[s] + ('*' if r[s + '_is_100th_pct'] in (True, 'True') else '') for s in sc] for r in E['clear']]
    body = f'''
    <div class="grid">
      {card(n(fz[2]['parcels'] + fz[3]['parcels']), 'parcels in hill Fire Zones 2 and 3', f"Our count from the City's zone map and County parcels ({pct(fz[2]['parcels'] + fz[3]['parcels'], F['assessor']['located'])} of all parcels; {big(fz[2]['net_taxable_value'] + fz[3]['net_taxable_value'])} taxable value). The City's plan counts 8,603.")}
      {card('1:45–2:20', 'to clear 90% of Fire Zones 2 and 3', 'Hours:minutes; the last vehicles take 3:25–3:40.')}
      {card('about 28,000', 'vehicles leave in a repeat of the 1923 fire', 'About 10,300 of them from households in Fire Zones 2 and 3; clearing them takes 1:35 to 4:10.')}
      {card(n(K['primary_ai'][1]), 'residential parcels with a single way out', f"{K['primary_ai'][0]} neighborhoods; {K['secondary_ai'][0]} more ({n(K['secondary_ai'][1])} parcels) have impaired secondary access.")}
    </div>
    <h3>Time to clear each area (hours:minutes)</h3>
    {table(['Region', 'Summer weekday', 'Summer weekend', 'Summer night', 'Fall weekday', 'Fall weekend', 'Fall night'], rows, right=range(1, 7))}
    <p class="note">Weekday and weekend columns are midday. Times are for the 90th-percentile vehicle; * marks the 100th percentile (the last vehicle), used where it governs. "Urgent
    mobilization" assumes residents leave within 30 minutes. KLD Table 7-4: {dl('evacuation_clearance_times_kld_2025.csv')}.</p>
    <p class="note" style="font-size:.95rem"><strong>How many cars leave the hills?</strong> The study counts vehicles, not
    parked cars: each household is assumed to drive out 1.14 vehicles, and workers, visitors and students drive out too. For the
    North and South Berkeley Hills together it counts about 17,900 evacuating vehicles at the busiest time of day (about 13,000
    and 4,900), about 11,500 of them residents'. A repeat of the 1923 fire, which burned from the hills into the neighborhoods north of campus,
    would send about 28,000 vehicles onto the roads, about 10,300 from households in Fire Zones 2 and 3; the rest come from the flats
    and the campus area inside the fire's path. The study's often-quoted "approximately 90,000 vehicles" is a citywide
    evacuation: residents' cars (about 48,000), commuters who work here (up to about 15,000), college students (about 15,000),
    visitors (about 14,000) and others, plus about 48,000 more passing through. Many hill residents work elsewhere, so at midday on a weekday
    fewer hill households are home, and more commuters' cars are in the flats.</p>
    <div class="two"><div><h3>Residents and their vehicles, by area (2024)</h3>
      {table(['Area', 'Residents', 'Vehicles'], [[esc(r['area']), rnd(r['population_2024']), rnd(r['resident_vehicles_2024'])] for r in E['pop']], right={1, 2})}
      <p class="note">Excludes students in campus housing, counted separately in the study. The Shadow Region is the
      neighboring area whose residents may leave unbidden.</p></div>
    <div><h3>How many streets jam?</h3>
      <p class="note" style="font-size:.95rem">The study does not count them; it maps every congested road and names them.
      "One hour into the evacuation, the majority of the roads within the Evacuation Zones are operating at LOS F [demand
      over capacity] conditions including Grizzly Peak Blvd, Euclid Ave, Spruce St, Marin Ave, La Loma Ave, Gayley Rd, and
      Arlington Ave." Hill streets carry at most {K['hill_capacity']} cars an hour (flatland arterials about {n(K['flat_capacity'])}),
      and "severe congestion is expected to occur in all evacuation cases studied." The choke points are intersections,
      the Marin Avenue five-way roundabout among them, so red-curbing hill streets is "unlikely to substantially improve
      evacuation flow." Hills residents leaving early, combined with a faster departure, cut the time to clear 90% of
      vehicles by up to 68% (the last vehicles, by up to 14%).</p></div></div>'''
    H = CITED['hz']
    ss = H['softstory']
    quake = f'''
    <h3>Earthquake</h3>
    <p class="note" style="font-size:.95rem">The Hayward Fault runs along the foot of the hills. The U.S. Geological Survey puts
    the chance of a magnitude 6.7 or larger earthquake on the Hayward or Rodgers Creek faults at {H['eq_hayward_pct']}% for
    {H['eq_window']}, and anywhere in the Bay Area at {H['eq_bay_pct']}%. For a large Hayward Fault earthquake (scenarios of
    magnitude 6.9 to 7.0), the City's hazard plan estimates about {H['eq_deaths']} deaths in Berkeley, {H['eq_displaced']} households displaced, {H['eq_damage']} in
    building damage, {n(H['eq_destroyed'])} buildings destroyed, {n(H['eq_no_power'])} homes without power, and
    {n(H['ebmud_breaks'])} breaks and {n(H['ebmud_leaks'])} leaks in EBMUD's pipes, with water out for {H['eq_water_out']}.
    The land west of San Pablo Avenue is in the liquefaction zone, along with {H['sewer_liq_mi']} miles ({H['sewer_liq_pct']}%) of
    the City's sewers; {H['sewer_slide_mi']} miles of sewer lie in the hills' earthquake-landslide zone.</p>
    {table(['Step taken', 'Status'], [
        ['Mandatory soft-story retrofit (apartment buildings over open ground floors)', f"{ss['retrofitted']} retrofitted, {ss['permitting']} in permitting, {ss['out_of_compliance']} out of compliance, {ss['removed']} removed from the list (as of {ss['asof']})"],
        ['Unreinforced masonry program (since 1991)', H['urm']],
        ['Transfer-tax rebate for seismic work', H['transfer_rebate']],
        ['Other potentially vulnerable buildings (not mandated)', f"{n(H['vulnerable'])} identified in a 2018 inventory, including non-ductile concrete; no retrofit requirement"],
    ])}'''
    flood = f'''
    <h3>Flood, tsunami and the rising Bay</h3>
    <p class="note" style="font-size:.95rem">The Bay has risen {H['bay_rise_since1900']} since 1900. The City's plan finds that
    {H['slr_i80']}, and that {H['gw']}. Vision 2050 cited the State's range of 1.1 to 2.7 feet of rise by 2050. A tsunami would
    reach the shoreline first: {about(H['tsu_people'])} residents in about {rnd(H['tsu_households'])} households live in the inundation zone,
    {about(H['tsu_daytime'])} people are there by day, and about {rnd(H['tsu_businesses'])} businesses employ {about(H['tsu_employees'])}; the
    Marina has {H['marina_households']} households living aboard. Inland, the storm drains were built for {H['storm_design']};
    the 2022–23 storms brought {H['storms_2223']}. The 100-year floodplain follows the shoreline, Aquatic Park, and Codornices
    and Strawberry creeks. The City's Stormwater Master Plan, due at the end of 2025, is still being prepared; no cost figure
    has been published.</p>'''
    fire_intro = f'''
    <h3>Fire</h3>
    <p class="note" style="font-size:.95rem">Hill Fire Zones 2 and 3 hold {n(H['fire_parcels'])} parcels and {about(H['fire_residents'])}
    residents. The 1923 fire destroyed {H['fire1923_structures']} structures and left about {n(H['fire1923_homeless'])} people
    homeless; {n(H['fire1923_footprint'])} buildings stand in its footprint today. The 1991 Tunnel Fire in the Oakland hills killed
    {H['tunnel_deaths']}. Measure FF (2020, {H['ff_vote']}% of the vote) funds fire prevention: ${H['ff_fy22']} million collected in
    FY2022, ${H['ff_fy23']} million in FY2023, about ${H['ff_fy26'] / 1e6:.1f} million expected in FY2026. The Fire Department
    inspects about {n(H['ff_inspections'])} hill parcels a year; a ${H['calfire_grant']} million state grant (2024–2026) funds work
    on Grizzly Peak and evacuation routes; a 2025 ordinance sets ember-resistant zones next to homes; and in January 2024 the
    Council asked PG&amp;E to underground its lines in the highest-risk zone.</p>'''
    fema = F['fema']
    recent = [r for r in fema if (r['program_fy'] or 0) >= 2018]
    plan = f'''
    <h3>The hazard plan, and the federal money it unlocks</h3>
    <p class="note" style="font-size:.95rem">A current hazard plan is required for federal mitigation grants. The City's 2024 plan
    lists {H['lhmp_actions']} mitigation actions. Its predecessor lapsed before the update was adopted:</p>
    {table(['Date', 'Step'], [['June 2023', 'City staff begin the update (Fire Department)'], ['May 2024', 'First draft published for comment'],
        ['November 2024', 'State review complete; plan sent to FEMA'], ['December 10, 2024', '2019 plan lapses; the City is "not eligible for certain mitigation grant funding"'],
        ['January 13, 2025', 'FEMA finds the plan approvable'], ['January 22, 2025', 'Disaster and Fire Safety Commission recommends adoption'],
        ['March 18, 2025', 'Council adopts the plan']])}
    <p class="note">Whether the 98-day gap cost Berkeley a grant is not on the record. FEMA's data shows one Berkeley application,
    $5 million for seismic retrofits of private buildings (DR-4699-0014), closed unfunded on December 12, 2024, two days after the
    lapse, with no reason recorded; a near-identical $5 million application under another disaster remains pending. The most
    recent approval was {usd(next(r['project_amount'] for r in recent if r['project'] == 'DR-4344-0026-R'))} for seismic
    retrofits ({usd(next(r['federal_share_obligated'] for r in recent if r['project'] == 'DR-4344-0026-R'))} federal), approved in
    March 2023. Still pending: {'; '.join(f"{usd(r['project_amount'])} ({r['project_type'].split(': ', 1)[-1].split(' - ')[0].lower()}, {r['subrecipient']}, {r['project']})" for r in recent if r['status'] == 'Pending' and r['disaster'] != 5545)}
    (the 2025 wildfire applications also appear under a second disaster number, 5545).
    All applications since 1990: {dl('fema_hazard_mitigation_berkeley.csv')}.</p>
    <p class="note">Sources: {esc('; '.join(H['src']))}; OpenFEMA Hazard Mitigation Assistance Projects (fetched 2026-10-01).</p>'''
    body = quake + fire_intro + body + flood + plan
    return section('fire', '11 · Fire, flood and earthquake', 'The dangers, and what is being done', body)


def s_campus():
    U, B = CITED['campus']['ucb'], CITED['campus']['lbnl']
    CS = F['campus_sus']
    S = CS['stars']
    last = lambda tag: next(r for r in CS[tag]['rows'] if r['year'] == 2024)
    gu, gl = last('ucb')['total'], last('lbnl')['total']
    ST = F['stars2025']
    sqft = ST['floor_m2'] * 10.7639
    wgal = ST['water_m3'] * 264.172
    gas_therms_implied = ST['implied_gas_mwh'] / 0.0293071      # 1 therm = 0.0293071 MWh
    tot_mwh = ST['total_mwh'] - ST['gas_mwh'] + ST['implied_gas_mwh']
    uc = CITED['uc']
    v = lambda t, f=n: f"{f(t[0])} <span class=\"yr\">({t[1]})</span>" if t and t[0] is not None else '<span class="no">not published</span>'
    mgd = lambda g: f"{g / 365 / 1e6:.2f} million gal/day"
    rows = [
        ['Students', f"{n(uc['students'])} <span class=\"yr\">({uc['term']})</span>", '—', f"{n(uc['students'])}"],
        ['Employees', v(U['employees']), v(B['employees']), f"≈ {n(U['employees'][0] + B['employees'][0])}"],
        ['Researchers and guests (Lab)', '—', f"{n(B['academics'][0])} academics, {n(B['affiliates'][0])} affiliates <span class=\"yr\">(spring 2024)</span>", 'overlap with UC'],
        ['Land', v(U['acres'], lambda x: f"{x:,} acres"), v(B['acres'], lambda x: f"{x:,} acres"), 'the Lab sits on University land; overlap not stated'],
        ['Floor area', f"{sqft / 1e6:.1f} million sq ft <span class=\"yr\">(2023)</span>", v(B['gsf'], lambda x: f"{x / 1e6:.1f} million sq ft"), f"≈ {(sqft + B['gsf'][0]) / 1e6:.1f} million sq ft"],
        ['Student beds', v(U['beds']) + f"; {n(U['beds_planned'][0])} more by fall 2029", 'none', v(U['beds'])],
        ['Parking spaces', v(U['parking']), v(B['parking']), f"≈ {n(U['parking'][0] + B['parking'][0])}"],
        ['Water', f"{wgal / 365 / 1e6:.2f} million gal/day <span class=\"yr\">(2023)</span>", v(B['water_gal'], mgd), f"≈ {(wgal + B['water_gal'][0]) / 365 / 1e6:.2f} million gal/day (2023)"],
        ['Buildings', 'about 100–150 on the 176-acre core campus <span class="yr">(sources differ)</span><sup>2</sup>', v(B['buildings'], lambda x: f"about {x} buildings and structures"), '—'],
        ['Energy, all sources', f"≈ {round(tot_mwh, -4):,.0f} MWh <span class=\"yr\">(2023, best estimate)</span><sup>1</sup>", '—', '—'],
        ['Electricity', f"{ST['elec_offsite_mwh']:,.0f} MWh bought + {ST['elec_solar_mwh']:,.0f} MWh solar <span class=\"yr\">(2023)</span>; most is generated by the campus gas plant, whose output is not published", v(B['elec_mwh'], lambda x: f"{x:,} MWh a year"), '—'],
        ['Natural gas', f"≈ {gas_therms_implied / 1e6:.1f} million therms <span class=\"yr\">(2023, implied by its emissions)</span>", v(B['gas_therms'], lambda x: f"{x / 1e6:.1f} million therms"), f"≈ {(gas_therms_implied + B['gas_therms'][0]) / 1e6:.1f} million therms (2023)"],
        ['Greenhouse gas (all scopes, net)', f"{gu:,.0f} t CO₂e <span class=\"yr\">(2024)</span>", f"{gl:,.0f} t CO₂e <span class=\"yr\">(2024)</span>", f"{gu + gl:,.0f} t CO₂e (2024)"],
        ['Commuting', f"{ST['commute_students']:.0f}% of students and {ST['commute_employees']:.0f}% of employees walk, bike, take transit or share rides <span class=\"yr\">(2024)</span>", f"{B['sov'][0]} of employees drive alone", '—'],
        ['Property tax', 'exempt (state constitution)', 'exempt (University land)', 'none'],
    ]
    beso = F['beso']['years']['2024']
    lab = {r['year']: r for r in CS['lbnl']['rows']}
    keep = (2009, 2012, 2015, 2018, 2019, 2020, 2021, 2022, 2023, 2024)
    ghg_rows = [[r['year'], n(r['scope1_net']), n(r['scope2']), n(r['scope3']), n(r['total'])]
                + ([n(lab[r['year']][k]) for k in ('scope1_net', 'scope2', 'scope3', 'total')] if r['year'] in lab else ['—'] * 4)
                for r in CS['ucb']['rows'] if r['year'] in keep]
    eui_rows = [[r['year'], f"{r['eui_kbtu_per_sqft']:.1f}" if r['eui_kbtu_per_sqft'] else '—',
                 f"{lab[r['year']]['eui_kbtu_per_sqft']:.1f}" if r['year'] in lab and lab[r['year']]['eui_kbtu_per_sqft'] else '—']
                for r in CS['ucb']['rows'] if r['year'] >= 2015]
    water_rows = [[k, n(v), n(CS['lbnl']['water_gal_per_person'].get(k))] for k, v in CS['ucb']['water_gal_per_person'].items()]
    ren_rows = [[esc(k), n(v.get('2018')), n(v.get('2024'))] for k, v in CS['ucb']['renewable_mwh'].items()]
    plan_rows = [['April 2023', 'Campus fact sheet', 'Gas plant retired in 2028'],
                 ['May 2024', 'Regents approve $476.6 million budget', 'Includes "geothermal heat exchange wells under the plant"'],
                 ['May 2024', 'Campus report cited by a STARS reviewer', 'Completion in 2033'],
                 ['July 2025', 'Regents approve Phase 1 design', 'Construction 2026–2030; no geothermal wells in the scope'],
                 ['2026', 'Project schedule', 'Utility work from summer 2026; plant built spring 2027 to summer 2029; buildings converted by summer 2030']]
    body = f'''
    <p class="note" style="font-size:.95rem">The University and the Lab run their own power, steam, roads and parking. The
    City's figures leave them out: its greenhouse-gas inventory excludes both, and its maps stop at their boundaries. The Lab
    straddles the city line, its western half in Berkeley and its eastern half in Oakland.</p>
    {table(['', 'UC Berkeley', 'Berkeley Lab (LBNL)', 'Together'], rows)}
    <p class="note">Together the two emitted {gu + gl:,.0f} tonnes of CO₂e in 2024, equal to {100 * (gu + gl) / CITED['cap']['ghg_2023']:.0f}%
    of the City's community inventory ({n(CITED['cap']['ghg_2023'])} tonnes, 2023); the inventories are compiled differently.
    The campus's own inventory page gives {n(U['ghg'][0])} tonnes, counting before {n(last('ucb')['compliance_offsets'])} tonnes
    of offsets.</p>
    <h3>Retiring the gas plant</h3>
    <p class="note" style="font-size:.95rem">The plant produced {n(U['ghg_cogen'][0])} of the campus's {n(U['ghg'][0])} tonnes in 2024.
    The Berkeley Clean Energy Campus project replaces it with an electric heating and cooling plant under North Field, north of
    Hearst Gym, with a playing field on its roof, a 2-million-gallon chilled-water tank, and new hot- and cold-water piping to about
    32 buildings. The State is paying $249 million of the $476.6 million first phase. The date has moved:</p>
    {table(['When', 'Document', 'What it says'], plan_rows)}
    <p class="note">The geothermal wells drew on Professor Kenichi Soga's 400-foot test borehole; the July 2025 scope was trimmed
    "to align with the approved project budget." Until the new plant runs, the gas plant does.</p>
    <h3>What the two report on their own sustainability</h3>
    <p class="note" style="font-size:.95rem">Both report every year to the UC Office of the President (the UC Annual Report on
    Sustainable Practices); the Lab also files a Site Sustainability Plan with the Department of Energy, and the campus reports
    to AASHE's STARS, the national rating for colleges: <strong>Platinum, {S['score']} points</strong> (submitted {S['submitted']},
    valid through {S['valid_through']}), the first STARS 3.0 Platinum. AASHE now shows each credit's data only after a login;
    the figures below are the UC report's own data, read from the public spreadsheets behind its charts.</p>
    {table(['Year', 'Campus Scope 1 (net)', 'Campus Scope 2', 'Campus Scope 3', 'Campus total', 'Lab Scope 1', 'Lab Scope 2', 'Lab Scope 3', 'Lab total'], ghg_rows, right=range(1, 9))}
    <p class="note">Metric tons of CO₂e. The campus's emissions are mostly Scope 1, gas burned on site; the Lab's are mostly
    Scope 2, purchased electricity. Scope 3 (commuting, air travel, waste) changed method in 2019 and fell during the pandemic.
    All years 2009–2024, with energy intensity: {dl('campus_lab_emissions_energy_2009_2024.csv')}.</p>
    <div class="two"><div>
    {table(['Year', 'Campus EUI', 'Lab EUI'], eui_rows, right={1, 2})}
    <p class="note">Energy use intensity, kBtu per square foot of building a year.</p></div><div>
    {table(['Year', 'Campus gal/person', 'Lab gal/person'], water_rows, right={1, 2})}
    <p class="note">Potable water per person a year (fiscal years; the baseline is the UC water policy's). The campus used
    {n(CS['ucb']['water_gal_per_person']['2025'])} gallons per person in 2025, against a 2025 goal of 13,105.</p>
    {table(['Campus renewable electricity (MWh)', '2018', '2024'], ren_rows, right={1, 2})}
    </div></div>
    <p class="note"><sup>1</sup> Best estimate: the gas implied by the campus's own reported emissions from burning fuel on site
    ({ST['stationary_t']:,.0f} tonnes of CO₂e in 2023, at its factor of 53.02 kg per MMBtu, about {round(ST['implied_gas_mwh'], -3):,.0f} MWh),
    plus purchased electricity, solar and heating oil. That is about {round(tot_mwh * 3412.14 / sqft, -1):.0f} kBtu per square foot, consistent with the
    {next(r['eui_kbtu_per_sqft'] for r in CS['ucb']['rows'] if r['year'] == 2023):.0f} the UC system reports for 2023. One of the several
    published figures appears about ten times too low: the campus's 2025 STARS report gives {ST['total_mwh']:,.0f} MWh, including only
    {ST['gas_mwh']:,.0f} MWh of gas, while calling the gas-fired plant "the primary source for electricity and heating." Data:
    {dl('stars_2025_ucb_operations.csv')}.</p>
    <p class="note"><sup>2</sup> About 100 (campus energy staff, ACEEE 2024 paper) or about 150 (U.S. Department of Energy Better
    Buildings partner page) on the core campus; the campus's 1,095 acres include the hill campus and outlying stations.</p>
    <p class="note">Not published: the campus's total electricity use (the plant's own generation is reported nowhere), miles of
    steam lines and tunnels, and how the campus and Lab land divides between Berkeley and Oakland. Under a 2021 settlement the
    University pays the City about $82.6 million over 16 years (press reports; the agreement itself was not available).</p>'''
    return section('campus', '12 · The University and the Lab', 'UC Berkeley and Berkeley Lab, counted on their own', body)


def s_ucpay():
    sched = [(2021 + k, 4_100_000 * 1.03 ** k) for k in range(16)]          # agreement §3.1: $4.1M, +3% compounding, 2021-2036
    total = sum(v for _, v in sched)
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, 'uc_settlement_payments_2021_2036.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['payment_year', 'scheduled_payment', 'city_acfr_actual_revenue'])
        actual = {2023: 4507873, 2024: 4480181}                           # FY2024 and FY2025 ACFR, UC Settlement Fund
        for y, v in sched:
            w.writerow([y, round(v), actual.get(y, '')])
    this_year = dict(sched)[2026]
    rows = [
        ['2021 settlement, annual payment', f"${this_year / 1e6:.2f} million in 2026 (${dict(sched)[2021] / 1e6:.1f} million in 2021, rising 3% a year to ${dict(sched)[2036] / 1e6:.2f} million in 2036)", 'City (UC Settlement Fund): $2.8 million of the base for fire and other services, $1.3 million for projects benefiting residents within half a mile of campus'],
        ['City-audited receipts', '$4,507,873 (FY2024); $4,480,181 (FY2025)', 'City annual financial reports. FY2025 matches the formula to the dollar; FY2024 is $158,183 above it, unexplained'],
        ['Sewer service fees', 'not published', 'UC pays the City\'s "public agency" sewer rate, about 40–46% of the standard rate; the agreement caps City fees at June 2021 levels and bars new ones, "including … sewer fees"'],
        ['Stormwater, street-light and business-district contributions', 'not published', 'The agreement says UC makes annual contributions to the Stormwater and Street Light Fund, the Downtown Berkeley Association and the Telegraph Improvement District'],
        ['Parking space rental tax (10%)', 'not published', 'Paid by people who park; UC collects it. A 2022 City report: "it is currently unclear how much"'],
        ['Property tax', 'none on University land', 'Exempt under the state constitution. Private tenants on campus paid "nearly $62,000" a year to the City (State Auditor, FY2014–15)'],
        ['Berkeley Lab to Alameda County Fire', '$10.6 million for 2023–2024 (about $5.3 million a year)', 'A contract for the County to staff the Lab\'s own fire station; not a payment to the City'],
    ]
    body = f'''
    <div class="grid">
      {card(f"${this_year / 1e6:.2f} million", 'scheduled UC payment to the City in 2026', 'Under the 2021 settlement: $4.1 million in 2021, rising 3% a year.')}
      {card(f"${total / 1e6:.1f} million", 'over 16 years, 2021–2036', 'The agreement ends June 30, 2037.')}
      {card('$21.4 million', 'a year: unreimbursed cost of UC to the City (reported)', 'A 2019 City-commissioned fiscal study, as reported in the press; the study itself was not found.')}
    </div>
    {table(['Payment', 'Amount', 'Notes'], rows)}
    <p class="note" style="font-size:.95rem">The University's payment to the City is about ${this_year / 1e6:.1f} million a year now,
    rising to about ${dict(sched)[2036] / 1e6:.1f} million by 2036. The agreement calls the payment "intended to be comprehensive." In return the City
    agreed not to sue over the University's development plan, its housing projects or "any enrollment decision," though it may end the
    agreement if undergraduate enrollment grows more than 1% a year. The 2005 agreement it replaced paid $1,520,124 in FY2014–15. Other payments exist but their amounts are not published. The City spends the money mainly on fire
    services: $3.4 million of the fund's $5.75 million in FY2025 spending went to public safety, and the FY2027 budget shifts two
    firefighter positions onto it.</p>
    <p class="note">Sources: City–University settlement agreement (2021), printed as Attachment D to the City's December 29, 2023
    collaborative-planning framework; City annual financial reports FY2024 and FY2025 (UC Settlement Fund); City sewer service fee
    schedule; Council item 05, April 12, 2022 (parking tax); California State Auditor report 2015-106 (March 2016); Alameda County
    Fire Department board item, December 6, 2022 (Berkeley Lab contract); Berkeley Daily Planet, August 1, 2021 (the 2019 fiscal
    study). Schedule: {dl('uc_settlement_payments_2021_2036.csv')}.</p>'''
    return section('ucpay', '14 · What the University pays', 'UC Berkeley\'s payments to the City and County', body)


def s_catalog():
    extra = [dict(file='uc_settlement_payments_2021_2036.csv', grain='year', rows=16,
                  description="UC Berkeley's scheduled payments to the City under the 2021 settlement, with the City's audited receipts where published.")]
    rows = [[dl(f['file']), esc(f['grain']), n(f['rows']), esc(f['description'])] for f in F['files'] + extra]
    M = F['sources_manifest']
    src = [[esc(k), f'<a href="{esc(v["url"])}">{esc(v["url"][:70])}{"…" if len(v["url"]) > 70 else ""}</a>', esc(v.get('fetched_at', '')[:10]), f'<code>{esc(v.get("sha256", "")[:12])}</code>']
           for k, v in M.items() if not k.startswith('unavailable') and not k.startswith('acs/blockgroup_')]
    body = f'''
    <p class="note" style="font-size:.95rem">Every table above comes from these files. Each is keyed by a geography a map
    can join on: census block group or tract (GEOID, matching the boundary files), census block with coordinates, ZIP code,
    the City's neighborhoods, the County parcel, or a named street segment. Two boundary files carry every census indicator
    already attached: {dl('berkeley_blockgroups.geojson')} and {dl('berkeley_tracts.geojson')}.</p>
    {table(['File', 'Grain', 'Rows', 'What it holds'], rows, right={2})}
    <h3>Sources, pinned</h3>
    <p class="note">Downloaded {esc(next(iter(M.values())).get('fetched_at', '')[:10])} by <code>scripts/snapshot/pull_sources.py</code>; each file's
    SHA-256 is recorded so any figure can be traced to the exact file. Census block-group tables (one request each) are
    pinned in the manifest too. Population in group housing is not published at block-group grain.</p>
    {table(['File', 'Source', 'Fetched', 'SHA-256'], src)}
    <ul class="src">
      <li>Already in the repository: Alameda County Assessor parcels (February 2026, data.acgov.org); City of Berkeley GIS
      layers for water mains, sewers, storm drains, streetlights, neighborhoods and hill fire zones (2026-08-30); City open
      data, BESO energy (5vy5-rwja).</li>
      <li>{esc(CITED['streets']['src'])}. {esc(CITED['ssmp']['src'])}. {esc(CITED['uc']['src'])}.</li>
      <li>{esc(CITED['kld']['src'])}.</li>
      <li>{esc(CITED['ug']['src_harris'])}. {esc(CITED['ug']['src_concept'])}. {esc(CITED['ug']['src_bellecci'])}. District 48: {esc(CITED['ug']['src_uud48'])}.</li>
      <li>University and Lab: {esc('; '.join(CITED['campus']['src']))}.</li>
      <li>{esc(CITED['ebmud']['src'])}. {esc(CITED['water_household']['src'])}. {esc(CITED['cap']['src'])}.</li>
      <li>Large buildings: City of Berkeley Building Emissions Saving Ordinance data. Vehicles: California DMV, Vehicle
      Fuel Type Count by ZIP Code. Commuting and jobs: U.S. Census LEHD LODES 8 (2023). Residents: U.S. Census American
      Community Survey via Census Reporter; California Department of Finance E-5.</li>
    </ul>'''
    return section('data', '13 · The data', 'Every file behind this report', body)


CSS = '''
  :root { --bg:#10202b; --panel:#162b3a; --line:#24384a; --ink:#eef3f6; --muted:#9fb8c8; --dim:#6d8496; --accent:#7ec8e3; --num:#ffd166; --bar:#7ec8e3; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; background:var(--bg); color:var(--ink); }
  header.top { max-width:72rem; margin:0 auto; padding:5vh 6vw 1rem; }
  nav.toc { max-width:72rem; margin:0 auto; padding:0 6vw 1.5rem; display:flex; flex-wrap:wrap; gap:.4rem .9rem; font-size:.9rem; }
  nav.toc a, a { color:var(--accent); }
  .page { max-width:72rem; margin:0 auto; padding:3vh 6vw 3vh; border-top:1px solid var(--line); }
  h1 { font-size:2.4rem; line-height:1.15; margin-bottom:.6rem; color:#fff; }
  h2 { font-size:1.6rem; margin:.2rem 0 .9rem; color:#fff; }
  h3 { font-size:1.08rem; margin:1.2rem 0 .45rem; color:var(--accent); }
  p, li { font-size:1rem; line-height:1.5; }
  .kicker { text-transform:uppercase; letter-spacing:.14em; font-size:.78rem; color:var(--accent); margin-bottom:.4rem; }
  .lede { color:#c9d6de; max-width:60rem; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(15rem, 1fr)); gap:.7rem; margin:.4rem 0 .6rem; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:.75rem .9rem; }
  .card .n { font-size:1.8rem; font-weight:800; color:var(--num); line-height:1.1; font-variant-numeric:tabular-nums; }
  .card .l { font-size:.95rem; margin-top:.2rem; }
  .card .s { font-size:.78rem; color:#8aa3b4; margin-top:.35rem; line-height:1.35; }
  .tw { overflow-x:auto; }
  table { border-collapse:collapse; margin:.3rem 0 .6rem; width:100%; }
  td, th { padding:.28rem .55rem; border-bottom:1px solid #2b4356; font-size:.9rem; text-align:left; vertical-align:top; }
  th { color:var(--muted); font-weight:600; }
  td.r, th.r { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
  .bar { display:inline-block; height:.65rem; background:var(--bar); border-radius:2px; vertical-align:middle; }
  .yes { color:#8fd694; font-weight:600; } .no { color:#ff9f7f; font-weight:600; } .part { color:var(--num); font-weight:600; }
  .note { font-size:.86rem; color:var(--muted); margin:.4rem 0 .5rem; line-height:1.45; }
  .two { display:grid; grid-template-columns:1fr 1fr; gap:1.4rem; }
  .two > div { min-width:0; }      /* let a wide table scroll inside its column instead of widening the page */
  a.dl { font-family: ui-monospace, Menlo, monospace; font-size:.82rem; overflow-wrap:anywhere; }
  ul.src { margin:.6rem 0 0 1.1rem; } ul.src li { font-size:.8rem; color:var(--dim); margin-bottom:.3rem; }
  code { font-size:.8rem; }
  .yr { color:var(--dim); font-size:.8em; }
  .finding { border-left:3px solid var(--num); padding:.1rem 0 .1rem .9rem; margin:1rem 0 1.2rem; max-width:60rem; }
  .finding h3 { margin-top:0; color:#fff; font-size:1.12rem; }
  .finding p { margin:.25rem 0; }
  .tw { position:relative; }
  button.full { display:none; margin:.15rem 0 .3rem; font:inherit; font-size:.8rem; color:var(--accent); background:var(--panel);
    border:1px solid var(--line); border-radius:6px; padding:.25rem .6rem; cursor:pointer; }
  .tw.wide > button.full { display:inline-block; }
  #sheet { position:fixed; inset:0; z-index:50; background:var(--bg); display:none; flex-direction:column; }
  #sheet.open { display:flex; }
  #sheet .bar2 { display:flex; align-items:center; gap:.8rem; padding:.5rem 16px; border-bottom:1px solid var(--line); }
  #sheet .bar2 .t { flex:1; font-size:.85rem; color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  #sheet .bar2 button { font:inherit; font-size:.9rem; color:var(--ink); background:var(--panel); border:1px solid var(--line);
    border-radius:6px; padding:.3rem .8rem; cursor:pointer; }
  #sheet .pane { flex:1; overflow:auto; -webkit-overflow-scrolling:touch; padding:12px 16px 40px; touch-action:pan-x pan-y pinch-zoom; }
  #sheet .pane table { width:auto; min-width:100%; }
  #sheet .pane td, #sheet .pane th { white-space:nowrap; font-size:.95rem; }
  #sheet .pane table { border-collapse:separate; border-spacing:0; }
  #sheet .pane th { position:sticky; top:-12px; background:var(--bg); z-index:2; }
  #sheet .pane td:first-child, #sheet .pane th:first-child { position:sticky; left:-16px; background:var(--bg); z-index:1;
    box-shadow:1px 0 0 var(--line); }
  #sheet .pane th:first-child { z-index:3; }
  #sheet .pane td:first-child { white-space:normal; min-width:7rem; max-width:10.5rem; }
  @media print { button.full, #sheet { display:none !important; } }
  @media (max-width: 760px) {
    header.top, nav.toc, .page { padding-left:16px; padding-right:16px; } .two { grid-template-columns:1fr; } h1 { font-size:1.7rem; }
    .grid { grid-template-columns:1fr 1fr; gap:.5rem; } .card { padding:.6rem; } .card .n { font-size:1.3rem; }
    td, th { padding:.25rem .35rem; font-size:.8rem; } .bar { display:none; }
  }
  @page { size: letter; margin: .5in; }
  @media print {
    html { font-size:9.5px; } body { background:#fff; color:#111; } nav.toc { display:none; }
    .page { border:0; max-width:none; padding:0 0 .6rem; } .card { background:#fff; border-color:#bbb; break-inside:avoid; }
    .card .n { color:#8a5a00; } h1, h2, h3, .kicker { color:#1a365d; } .note, td, th, .card .s, .lede { color:#333; }
    .bar { background:#2b6cb0; } table { break-inside:auto; } tr { break-inside:avoid; } a { color:#1a365d; }
  }'''


def main():
    sections = [s_findings(), s_people(), s_tenure(), s_income(), s_age(), s_tide(), s_cars(), s_business(), s_networks(), s_ug(),
                s_water_energy(), s_fire(), s_campus(), s_ucpay(), s_land(), s_city(), s_innovation(), s_catalog()]
    toc = [('findings', 'Findings'), ('people', 'People'), ('tenure', 'Renters and owners'), ('income', 'Income'),
           ('age', 'Ages'), ('tide', 'Daily tide'), ('cars', 'Cars and bikes'), ('business', 'Businesses'),
           ('networks', 'Under the streets'), ('undergrounding', 'Undergrounding'), ('water-energy', 'Water and power'),
           ('fire', 'Fire, flood, earthquake'), ('campus', 'University and Lab'), ('ucpay', 'What UC pays'),
           ('land', 'Land and money'), ('city', 'The City\'s money'), ('innovation', 'What is next'), ('data', 'The data')]
    old = open(PAGE).read() if os.path.exists(PAGE) else ''
    meta = ''
    if '<!-- BEGIN site_meta' in old:
        meta = old[old.index('<!-- BEGIN site_meta'):old.index('<!-- END site_meta -->') + len('<!-- END site_meta -->')]
    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Berkeley Snapshot — October 2026</title>
<style>{CSS}
</style>
{meta}
</head>
<body>
<header class="top">
  <div class="kicker">BerkeleyBuild · Berkeley Snapshot · October 2026</div>
  <h1>Our people, our buildings, our streets, our businesses: their daily flows of energy, water, income and expense</h1>
  <p class="lede">The scaffolding facts under every housing and infrastructure decision, at the finest grain each public
  source allows, with every table's data downloadable for mapping. Each figure names its source; where a fact is not
  public, or not public at the grain you would want, the report says so.</p>
</header>
<nav class="toc">{''.join(f'<a href="#{a}">{b}</a>' for a, b in toc)}</nav>
{''.join(sections)}
<div id="sheet" role="dialog" aria-modal="true" aria-label="Full table">
  <div class="bar2"><span class="t"></span><button type="button" class="close">Close</button></div>
  <div class="pane"></div>
</div>
<script>
// FULL-TABLE VIEW. A table wider than its column gets a button; the button opens the table full-screen at its natural
// width, where it scrolls in any direction and pinch-zooms. Close, Escape or the phone's Back button return to the page
// at the same place. Nothing here is needed to read the page: without script, wide tables still scroll sideways.
(function () {{
  var sheet = document.getElementById('sheet'), pane = sheet.querySelector('.pane'), title = sheet.querySelector('.t');
  function mark() {{
    document.querySelectorAll('.tw').forEach(function (w) {{
      var t = w.querySelector('table');
      w.classList.toggle('wide', t.scrollWidth > w.clientWidth + 2);
    }});
  }}
  function heading(w) {{
    for (var e = w.previousElementSibling; e; e = e.previousElementSibling)
      if (/^H[23]$/.test(e.tagName)) return e.textContent;
    var s = w.closest('section'); return s ? s.querySelector('h2').textContent : '';
  }}
  var y = 0;
  function open(w) {{
    y = window.scrollY;
    pane.innerHTML = ''; pane.appendChild(w.querySelector('table').cloneNode(true));
    title.textContent = heading(w);
    sheet.classList.add('open'); document.body.style.overflow = 'hidden';
    history.pushState({{sheet: 1}}, '');
    sheet.querySelector('.close').focus();
  }}
  function shut() {{
    if (!sheet.classList.contains('open')) return;
    sheet.classList.remove('open'); document.body.style.overflow = ''; pane.innerHTML = '';
    window.scrollTo(0, y);
  }}
  document.addEventListener('click', function (e) {{
    var b = e.target.closest('button.full'); if (b) open(b.parentElement);
    if (e.target.closest('#sheet .close')) history.back();
  }});
  document.addEventListener('keydown', function (e) {{ if (e.key === 'Escape' && sheet.classList.contains('open')) history.back(); }});
  window.addEventListener('popstate', shut);
  window.addEventListener('resize', mark); mark();
}})();
</script>
</body>
</html>
'''
    open(PAGE, 'w').write(page)
    print(f'wrote {PAGE} ({len(page):,} bytes, {len(sections)} sections)')


if __name__ == '__main__':
    main()
