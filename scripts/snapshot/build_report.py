#!/usr/bin/env python3
"""build_report.py — render the Berkeley Snapshot report (docs/berkeley-snapshot-2026-10.html) from derive.py's output.

Every number comes from docs/data/snapshot/facts.json or the data files beside it, except the figures in CITED below,
which come from documents rather than data files; each carries its source. Nothing else is typed by hand.

Run: .venv/bin/python scripts/snapshot/derive.py && .venv/bin/python scripts/snapshot/build_report.py
"""
import csv, html, json, os

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
             src='KLD Associates, City of Berkeley Evacuation Time Estimate Study, TR-1296, July 1, 2025; City of '
                 'Berkeley Evacuation StoryMaps (text version, July 2025); Community Wildfire Protection Plan (2023)'),
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


def section(id_, kicker, title, body):
    return f'<section class="page" id="{id_}"><div class="kicker">{kicker}</div><h2>{title}</h2>{body}</section>'


# ============================================================================================ sections
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
    <h3>Homes by type (Department of Finance, {F['dof']['year']})</h3>
    {table(['Type', 'Homes', 'Share'], [[k, n(last[c]), pct(last[c], last['housing_units'])] for k, c in
        (('Single detached', 'single_detached'), ('Single attached', 'single_attached'), ('Two to four units', 'two_to_four'),
         ('Five or more units', 'five_plus'), ('Mobile homes', 'mobile_homes'))], right={1, 2})}
    <p class="note">The Census survey ({F['acs_city']['release']}) counts {n(i['population'])} residents: a mid-2024
    survey estimate, lower than the state's January 2026 figure, mainly in group housing. The tables below use the
    survey because only it describes residents (tenure, income, age, cars); use the state's totals for counts.</p>'''
    return section('people', '1 · The people', 'Who lives in Berkeley', body)


def s_tenure():
    i = F['acs_city']['ind']
    body = f'''
    <div class="grid">
      {card(n(i['renter_households']), f"renter households ({i['renter_household_pct']}%)", f"{n(i['residents_renter_occupied'])} residents live in rented homes.")}
      {card(n(i['owner_households']), f"owner households ({100 - i['renter_household_pct']:.1f}%)", f"{n(i['residents_owner_occupied'])} residents live in owned homes.")}
      {card(usd(i['median_gross_rent']), 'median gross rent a month', 'Rent plus utilities.')}
      {card(usd(i['median_home_value']), 'median value of an owned home', "Owners' own estimate (Census survey).")}
    </div>
    <p class="note">Households split 54/46 toward renting, yet residents split evenly, because owner households are larger.</p>
    <div class="two"><div>{acs_table('B25070', title='Rent as a share of household income (renters)')}</div>
    <div>{acs_table('B25034', title='Homes by year built')}</div></div>
    <p class="note">{n(float(ACS['B25070010']['estimate']))} renter households, about one in three, pay half their income
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
      {card(usd(i['median_household_income']), 'median household income', '±$' + n(F['acs_city']['cols']['B19013001'][1]) + ' (2024 dollars).')}
      {card(usd(i['per_capita_income']), 'income per resident', 'Includes students.')}
      {card(f"{i['below_poverty_pct']}%", 'of residents below the poverty line', 'Residents in households; students in dorms excluded.')}
      {card(f"{i['bachelors_or_higher_pct']}%", "of adults 25+ hold a bachelor's degree or more", '')}
    </div>
    <div class="two"><div>{acs_table('B19001', title='Households by income (2024 dollars)')}</div>
    <div>{acs_table('B15003', skip=tuple(f'B15003{k:03d}' for k in range(3, 16)), title='Adults 25 and over by education')}</div></div>
    <p class="note">The income distribution is a barbell: {n(i['hh_income_under_50k'])} households earn under $50,000 and
    {n(i['hh_income_200k_plus'])} earn $200,000 or more. Student households sit in the bottom band. Incomes are published
    for households, never individuals. Education rows for grades 1–11 are folded out of the table (they are in the data file).</p>'''
    return section('income', '3 · Income', 'Household income, poverty and education', body)


def s_age():
    i = F['acs_city']['ind']
    m = lambda a, b: sum(float(ACS[f'B01001{k:03d}']['estimate']) + float(ACS[f'B01001{k + 24:03d}']['estimate']) for k in range(a, b + 1))
    bands = [('Under 5', 3, 3), ('5–17', 4, 6), ('18–19', 7, 7), ('20–21', 8, 9), ('22–24', 10, 10), ('25–34', 11, 12),
             ('35–44', 13, 14), ('45–54', 15, 16), ('55–64', 17, 19), ('65–74', 20, 22), ('75–84', 23, 24), ('85 and over', 25, 25)]
    vals = [(b, m(a, c)) for b, a, c in bands]
    mx = max(v for _, v in vals)
    rows = [[b, n(v), pct(v, i['population']), bar(v, mx)] for b, v in vals]
    body = f'''
    {table(['Age', 'Residents', 'Share', ''], rows, right={1, 2})}
    <div class="two"><div>{acs_table('B03002', title='Residents by race and Hispanic origin')}</div>
    <div><p class="note" style="margin-top:2.2rem">One resident in four is 18–24. {n(m(7, 9))} residents are 18–21,
    the undergraduate years. 65 and over: {n(i['age_65_plus'])} ({pct(i['age_65_plus'], i['population'])}).
    Every age column, by sex, is in {dl('acs_city_2024_1yr_all_columns.csv')}; the same bands for each block group are in
    {dl('acs_blockgroup_2020_2024_5yr.csv')}.</p></div></div>'''
    return section('age', '4 · Ages', 'A university city: ages and origins', body)


def s_tide():
    L = F['lodes']
    sec = L['sectors']
    mx = sec[0][1]
    body = f'''
    <div class="grid">
      {card(n(L['jobs']), 'jobs located in Berkeley', f"All jobs, {L['year']} (a worker with two jobs counts twice).")}
      {card(n(L['inflow']), 'commute in each workday', f"Work here, live elsewhere ({n(L['aux_in'])} from out of state).")}
      {card(n(L['outflow'] + L['out_of_state_out']), 'residents commute out', f"{n(L['outflow'])} to jobs elsewhere in California, {n(L['out_of_state_out'])} out of state.")}
      {card(n(L['interior']), 'live and work here', f"{pct(L['interior'], L['employed_residents'])} of employed residents.")}
    </div>
    <p class="note">By day Berkeley gains about {n(L['inflow'] - L['outflow'] - L['out_of_state_out'], 0)} workers, before
    counting {n(CITED['uc']['students'])} students. Counts are jobs covered by unemployment insurance and federal
    employment; the self-employed are not included.</p>
    <div class="two"><div><h3>Where in-commuters live</h3>
      {table(['Home', 'Workers', 'Share'], [[esc(k), n(v), pct(v, L['inflow'])] for k, v in L['top_in']], right={1, 2})}
      <p class="note">All {len(csvrows('lodes_2023_inflow_by_home_place.csv'))} places: {dl('lodes_2023_inflow_by_home_place.csv')}</p></div>
    <div><h3>Where out-commuters work</h3>
      {table(['Work', 'Workers', 'Share'], [[esc(k), n(v), pct(v, L['outflow'])] for k, v in L['top_out']], right={1, 2})}
      <p class="note">All {len(csvrows('lodes_2023_outflow_by_work_place.csv'))} places: {dl('lodes_2023_outflow_by_work_place.csv')}</p></div></div>
    <div class="two"><div><h3>Jobs in Berkeley by industry</h3>
      {table(['Industry', 'Jobs', 'Share', ''], [[esc(k), n(v), pct(v, L['jobs']), bar(v, mx)] for k, v in sec], right={1, 2})}</div>
    <div><h3>Jobs by monthly earnings</h3>
      {table(['Earnings', 'Jobs', 'Share'], [[k, n(v), pct(v, L['jobs'])] for k, v in zip(('$1,250 or less', '$1,251–$3,333', 'More than $3,333'), L['earnings'])], right={1, 2})}
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
      {card(n(i['households_no_vehicle']), f"households with no car ({i['no_vehicle_pct']}%)", 'Census survey 2024.')}
      {card(n(i['vehicles_available_min']), 'vehicles kept by households', 'At least; the survey tops out at "5 or more". Close to the DMV count.')}
    </div>
    <h3>Vehicles by ZIP code and fuel</h3>
    {table(['ZIP', 'All'] + fuels + ['Plug-in share'], rows, right=range(1, len(fuels) + 3))}
    <div class="two"><div>{table(['Fuel', 'Vehicles', 'Share', ''], [[esc(k), n(v), pct(v, D['total']), bar(v, fm)] for k, v in D['fuel'].items()], right={1, 2})}</div>
    <div>{acs_table('B25044', title='Vehicles available, by tenure (households)')}</div></div>
    <p class="note"><strong>To which addresses?</strong> Not public: the DMV releases registrations by ZIP code only, and a
    vehicle's registered address is confidential under the Vehicle Code (§1808.21). ZIP codes 94707 and 94708 include
    parts of Kensington and Albany, so ZIP totals slightly overstate Berkeley. Data: {dl('dmv_2026_by_zip.csv')},
    {dl('dmv_2026_by_zip_fuel_duty.csv')}.</p>'''
    return section('cars', '6 · Cars', 'Vehicles, by ZIP code and fuel', body)


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
        ['Water mains (EBMUD)', n(I['water_mi'], 1), f"{n(I['water_segments'])} pipe segments; median year laid {I['water_median_year']}; {n(I['water_pre1940_mi'], 1)} miles laid before 1940; the oldest from {I['water_oldest']}."],
        ['Sanitary sewer mains (City)', n(I['sewer_mi'], 1), f"{n(I['sewer_segments'])} segments, {n(I['manholes'])} manholes, {n(I['laterals'])} house laterals ({n(I['laterals_mi'], 1)} mapped miles); {CITED['ssmp']['pump_stations']} pump stations; {CITED['ssmp']['rehab_since_1986']} miles rehabilitated since 1986."],
        ['Storm drains (City)', n(I['storm_mi'], 1), f"{n(I['storm_segments'])} pipe segments."],
        ['Gas, high pressure (PG&amp;E)', '≈ 38', 'Lines at 60 psi and above only; the low-pressure mains that feed houses are not public.'],
        ['Utility poles (PG&amp;E, AT&amp;T)', f"{n(poles.get('Wood', 0))}+", f"Wood poles carrying a City streetlight, {n(I['wood_util_pn_distinct'])} with PG&amp;E pole numbers: a floor (estimate of all street poles below). Ages and transformers are not public."],
    ], right={1})}
    <p class="note">Two City-commissioned counts of street miles disagree by 5 miles: 214.2 in the 2022 pavement survey and
    219.4 in the 2016 undergrounding study. Neither report explains the difference; they were measured six years apart for
    different purposes.</p>
    <p class="note">The City's sewer map prices every segment at a planning cost per foot by diameter: {big(I['sewer_planning_cost'])}
    for the whole network, including the {n(sum(r['segments'] for r in I['sewer_by_material'] if r['MATERIAL'] == 'HDPE'))} segments
    already relined with plastic (HDPE). It is a replacement value at the City's unit costs, not a backlog.</p>
    <h3>Overhead wire: an estimate from the poles</h3>
    {table(['Measure', 'Value', 'How it is known'], [
        ['Street miles with overhead lines', f"{over:.1f}", 'Measured: City-commissioned 2016 study, Table 1 (all street classes)'],
        ['Lit wood poles, located', n(P['wood']), "Measured: the City's streetlight layer (pole material = wood)"],
        ['Distance to the nearest lit wood pole', f"median {P['nn_median_ft']} ft (half within {P['nn_p25']}–{P['nn_p75']} ft)", 'Measured from those poles'],
        ['Pole line traced by lit poles alone', f"{tr['250']['miles']:.0f}–{tr['400']['miles']:.0f} mi", 'Measured: links between neighboring lit poles up to 250–400 ft; a floor'],
        ['Utility poles along streets', f"≈ {round(lo, -2):,.0f}–{round(hi, -2):,.0f}", f"Estimate: {over:.1f} overhead street miles ÷ a span of {tr['200']['mean_span_ft']:.0f}–{tr['250']['mean_span_ft']:.0f} ft (the traced links); rear-lot pole lines are extra"],
        ['Aerial cable route-miles', f"≈ {4 * over:,.0f}", f"Illustration: {over:.0f} miles × 4 systems on a typical joint-use pole (electric, telephone copper, cable TV coax, fiber); each electric line carries several conductors"],
    ])}
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
    <h3>Every street, by class: underground and overhead (miles, 2016)</h3>
    {table(['Streets', 'Total', 'Underground', 'Overhead', 'Share underground'], t1rows, right=range(1, 5))}
    <p class="note">From Table 1 of the 2016 Harris study, computed from its feet. The table prints 149.9 overhead residential
    miles, but its own 775,399 feet is 146.9 miles. Residential streets are measured but not costed in any City study.
    Overhead lines that run behind houses, along rear lot lines, are not counted as street miles.</p>
    <h3>The 2016 segment table: what it costs, street by street</h3>
    {table(['Network', 'Segments', 'Overhead', 'Underground', 'Cost (segments)', 'Report\'s printed total'], [
        ['Arterial', S['arterial']['segments'], f"{S['arterial']['overhead_mi']:.1f} mi", f"{S['arterial']['underground_mi']:.1f} mi", usd(S['arterial']['cost']), usd(sum(rn['arterial']))],
        ['Collector', S['collector']['segments'], f"{S['collector']['overhead_mi']:.1f} mi", f"{S['collector']['underground_mi']:.1f} mi", usd(S['collector']['cost']), usd(sum(rn['collector']))],
        ['<strong>Total</strong>', S['arterial']['segments'] + S['collector']['segments'], '', '', f"<strong>{usd(U['total'])}</strong>", f"{usd(sum(rn['arterial']) + sum(rn['collector']))} (headline {big(rn['headline'])})"],
    ], right=range(1, 6))}
    <p class="note"><strong>A discrepancy in the City's table.</strong> {f"{esc(d['street'].title())}'s five residential-zone segments are priced in the table at {usd(d['segments_residential'])}, but its total row prints {usd(d['cost_residential'])}, and the arterial network's TOTAL COST leaves out all {usd(d['segments_residential'])}." if d else ''}
    Summed segment by segment, the arterial and collector program costs {usd(U['total'])}, not the {big(rn['headline'])} quoted in the
    2016 study and every report since. The collector network reproduces the report's totals to the dollar.
    The costs exclude trenching on private property, service conversions, financing, engineering, construction management and street lighting.</p>
    <h3>The 15 costliest overhead segments</h3>
    {table(['Street', 'From', 'To', 'Feet', 'Impact (3–15)', 'Cost'], [[esc(r['street'].title()), esc(r['seg_from'].title()), esc(r['seg_to'].title()), n(r['length_ft']), r['impact_total'], usd(r['cost_total'])] for r in U['top']], right={3, 4, 5})}
    <h3>Evacuation routes, 2019: cost per street</h3>
    {table(['Street', 'Complexity (1–5)', 'Overhead mi', 'FY2019', 'FY2023 program', 'FY2023 capital plan'],
           [[esc(r['street']), r['complexity_level'] or '—', n(r['overhead_centerline_miles'], 2), usd(r['total_cost']), usd(b23[r['street']]['total_cost']), usd(bc[r['street']]['total_cost'])] for r in sorted(b19, key=lambda r: -r['total_cost'])],
           right=range(1, 6))}
    <p class="note">Cost per mile rises with construction complexity, from $4.08 million (level 1) to $6.8 million (level 5), street lighting included.
    The 2018 Conceptual Study put the City's cost at {C['conceptual_per_mile']} a mile and {C['conceptual_range']} for all 37.9 miles.
    <strong>Rule 20A</strong> (PG&amp;E ratepayer credits): about {usd(C['harris_rule20a_per_year'])} a year to Berkeley; the balance was
    {usd(C['harris_rule20a_balance'])} in 2016 and {usd(C['bellecci_rule20a_balance'])} in 2019, most of it committed to
    <strong>Underground Utility District 48</strong> (Grizzly Peak, Summit, Senior, Avenida: {C['uud48_parcels']} parcels along about {n(C['uud48_feet'])} feet of road).</p>
    <p class="note">Maps: {dl('undergrounding_segments_harris_2016.csv')} ({len(csvrows('undergrounding_segments_harris_2016.csv'))} segments, each with street, from and to,
    so it can be drawn on the City's street centerlines) and {dl('undergrounding_evacuation_routes_bellecci_2019.csv')}.</p>'''
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
    <p class="note">PG&amp;E's ZIP-code files sit behind a short registration form (CPUC decision D.14-05-016); they are the next pull.
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
      {card(n(fz[2]['parcels'] + fz[3]['parcels']), 'parcels in hill Fire Zones 2 and 3', f"{pct(fz[2]['parcels'] + fz[3]['parcels'], F['assessor']['located'])} of the city's parcels; {big(fz[2]['net_taxable_value'] + fz[3]['net_taxable_value'])} taxable value.")}
      {card('1:45–2:20', 'to clear 90% of Fire Zones 2 and 3', 'Hours:minutes; the last vehicles take 3:25–3:40.')}
      {card(f"~{n(K['vehicles'])}", 'vehicles that may need to leave the city', f"Plus {n(K['through'])} passing through. {K['zones']} evacuation zones.")}
      {card(n(K['primary_ai'][1]), 'residential parcels with a single way out', f"{K['primary_ai'][0]} neighborhoods; {K['secondary_ai'][0]} more ({n(K['secondary_ai'][1])} parcels) have impaired secondary access.")}
    </div>
    <h3>Time to clear each area (hours:minutes)</h3>
    {table(['Region', 'Summer weekday', 'Summer weekend', 'Summer night', 'Fall weekday', 'Fall weekend', 'Fall night'], rows, right=range(1, 7))}
    <p class="note">Weekday and weekend columns are midday. Times are for the 90th-percentile vehicle; * marks the 100th percentile (the last vehicle), used where it governs. "Urgent
    mobilization" assumes residents leave within 30 minutes. KLD Table 7-4: {dl('evacuation_clearance_times_kld_2025.csv')}.</p>
    <div class="two"><div><h3>Residents and their vehicles, by area (2024)</h3>
      {table(['Area', 'Residents', 'Vehicles'], [[esc(r['area']), n(r['population_2024']), n(r['resident_vehicles_2024'])] for r in E['pop']], right={1, 2})}
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
      vehicles by up to 68% (the last vehicles, by up to 14%). The Fire Department inspects about {n(K['fire_inspections'])} hill parcels a year.</p></div></div>'''
    return section('fire', '11 · Fire evacuation', 'Leaving the hills', body)


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
        ['Electricity', f"{ST['elec_offsite_mwh']:,.0f} MWh bought + {ST['elec_solar_mwh']:,.0f} MWh solar <span class=\"yr\">(2023)</span>; the gas plant's own output is not reported", v(B['elec_mwh'], lambda x: f"{x:,} MWh a year"), '—'],
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
    body = f'''
    <p class="note" style="font-size:.95rem">The University and the Lab run their own power, steam, roads and parking, and the
    City's figures leave them out: the City's community greenhouse-gas inventory excludes both, and the City's maps stop at
    their boundaries. The Lab straddles the city line: "the western half of the Lab campus is within the City of Berkeley;
    the eastern half is within the city of Oakland."</p>
    {table(['', 'UC Berkeley', 'Berkeley Lab (LBNL)', 'Together'], rows)}
    <p class="note"><strong>The campus's national sustainability report leaves out its power plant.</strong> In its 2025 STARS
    report the campus gives its 2023 energy use as {ST['total_mwh']:,.0f} MWh, including {ST['gas_mwh']:,.0f} MWh of natural gas, while
    describing the gas-fired cogeneration plant as "the primary source for electricity and heating for campus buildings." The same
    report's emissions credit gives {ST['stationary_t']:,.0f} tonnes of CO₂e from burning fuel on site in 2023, which at the campus's
    own factor (53.02 kg of CO₂ per MMBtu) means about {round(ST['implied_gas_mwh'], -3):,.0f} MWh of gas (the CO₂ factor alone slightly overstates it), some {ST['implied_gas_mwh'] / ST['gas_mwh']:.0f} times the
    energy credit's figure. With that gas, the campus used roughly {(ST['total_mwh'] - ST['gas_mwh'] + ST['implied_gas_mwh']) / 1000:,.0f} thousand MWh,
    about {(ST['total_mwh'] - ST['gas_mwh'] + ST['implied_gas_mwh']) * 3412.14 / sqft:.0f} kBtu per square foot, which matches the
    {next(r['eui_kbtu_per_sqft'] for r in CS['ucb']['rows'] if r['year'] == 2023):.0f} the UC system report gives for 2023. The STARS energy figure
    ({ST['total_mwh'] * 3412.14 / sqft:.0f} kBtu per square foot) understates the campus's energy use about tenfold. For scale, the campus's gas, about
    {gas_therms_implied / 1e6:.0f} million therms, is six times the {beso['therms'] / 1e6:.1f} million therms reported by all of the City's large
    buildings in 2024. Data: {dl('stars_2025_ucb_operations.csv')}.</p>
    <p class="note"> Its gas-fired
    cogeneration plant produced {n(U['ghg_cogen'][0])} of the campus's {n(U['ghg'][0])} tonnes of CO₂e in 2024; the Berkeley
    Clean Energy Campus project replaces it with an electric heating and cooling plant serving about 32 buildings in its first
    phase. The Regents approved a Phase 1 budget of $476.6 million in May 2024
    ($249 million of it from the State, through debt service, and the rest from renewable-energy tax credits and campus funds).
    That budget item included "geothermal heat exchange wells under the plant," the grid of boreholes Professor Kenichi Soga's
    research tested; the scope the Regents approved in July 2025, after the campus "refined the design and scope… to align
    with the approved project budget," mentions a 2-million-gallon chilled-water tank but no geothermal wells. The plant goes
    under North Field, the recreation field north of Hearst Gym, with a grass field on its roof. The retirement date has slid:
    2028 in the campus's 2023 fact sheet, "by 2030" in the Regents' 2025 approval (utility relocation from summer 2026, plant
    construction spring 2027 to summer 2029, building conversions to summer 2030), and 2033 in a May 2024 campus report a
    STARS reviewer cited. Until then the gas plant runs. The two institutions' {gu + gl:,.0f} tonnes equal
    {100 * (gu + gl) / CITED['cap']['ghg_2023']:.0f}% of the City's own community inventory
    ({n(CITED['cap']['ghg_2023'])} tonnes, 2023), which does not include them; the inventories are compiled differently.
    (The campus's own inventory page gives {n(U['ghg'][0])} tonnes for 2024, counting Scope 1 before its
    {n(last('ucb')['compliance_offsets'])} tonnes of compliance offsets.)</p>
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
    <p class="note">Not published: the campus's total electricity use, miles of steam lines and utility tunnels, and how the
    campus and Lab acreage divide between Berkeley and Oakland. Several campus figures date from the 2018-19 baseline of the
    2021 Long Range Development Plan, the most recent the University has published. The 2021 settlement with the City has
    the University paying about $82.6 million over 16 years (press reports; the signed agreement was not available).</p>'''
    return section('campus', '12 · The University and the Lab', 'UC Berkeley and Berkeley Lab, counted on their own', body)


def s_catalog():
    rows = [[dl(f['file']), esc(f['grain']), n(f['rows']), esc(f['description'])] for f in F['files']]
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
  a.dl { font-family: ui-monospace, Menlo, monospace; font-size:.82rem; overflow-wrap:anywhere; }
  ul.src { margin:.6rem 0 0 1.1rem; } ul.src li { font-size:.8rem; color:var(--dim); margin-bottom:.3rem; }
  code { font-size:.8rem; }
  .yr { color:var(--dim); font-size:.8em; }
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
    sections = [s_people(), s_tenure(), s_income(), s_age(), s_tide(), s_cars(), s_land(), s_networks(), s_ug(),
                s_water_energy(), s_fire(), s_campus(), s_catalog()]
    toc = [('people', 'People'), ('tenure', 'Renters and owners'), ('income', 'Income'), ('age', 'Ages'),
           ('tide', 'Daily tide'), ('cars', 'Cars'), ('land', 'Land and money'), ('networks', 'Under the streets'),
           ('undergrounding', 'Undergrounding'), ('water-energy', 'Water and power'), ('fire', 'Fire evacuation'),
           ('campus', 'University and Lab'), ('data', 'The data')]
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
  <h1>Berkeley in numbers: the people, the daily tide, the ground and the pipes</h1>
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
