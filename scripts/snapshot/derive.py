#!/usr/bin/env python3
"""derive.py — turn the pinned Berkeley Snapshot sources into map-ready data files and a facts file.

Inputs: data/raw/snapshot/<date>/ (pulled by pull_sources.py, pinned in its manifest.json), plus files already in the
repo: databases/berkeley.db (Alameda County Assessor parcels, Feb 2026), data/raw/infrastructure/*_2026-08-30.geojson
(City of Berkeley GIS), data/reference/berkeley_neighborhoods.geojson and berkeley_fire_hill_zones.geojson (City GIS),
energy/beso_energy_5vy5-rwja.csv (City open data), data/raw/evacuation/*.txt (KLD 2025 study, City StoryMaps) and
data/raw/undergrounding/*.txt (Harris & Associates 2016 table inside the City's 2018 Conceptual Study).

Outputs: docs/data/snapshot/*.csv and *.geojson (one file per dataset, each keyed by a geography a map can join on:
census block group/tract GEOID, census block with coordinates, ZIP, neighborhood, parcel or street segment), and
docs/data/snapshot/facts.json, which build_report.py renders. Read-only with respect to every database.

Run: .venv/bin/python scripts/snapshot/derive.py [--date 2026-10-01]
"""
import argparse, collections, glob, json, os, re, sqlite3, sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from housing_rules.address import normalize_address  # noqa: E402  (the single address canon, CLAUDE.md rule 4)
import undergrounding  # noqa: E402

OUT = os.path.join(ROOT, 'docs', 'data', 'snapshot')
UTM = 'EPSG:26910'                  # NAD83 / UTM zone 10N: metres, for lengths and areas
M_PER_MI = 1609.344
BERKELEY_ZIPS = ['94702', '94703', '94704', '94705', '94707', '94708', '94709', '94710', '94720']  # 94706 = Albany
FACTS = {}
FILES = []                          # (file, grain, rows, description) for the report's data catalog


def write_csv(name, rows, grain, desc):
    os.makedirs(OUT, exist_ok=True)
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, name), index=False)
    FILES.append(dict(file=name, grain=grain, rows=len(df), description=desc))
    return df


def write_geojson(name, gdf, grain, desc):
    gdf.to_crs('EPSG:4326').to_file(os.path.join(OUT, name), driver='GeoJSON')
    FILES.append(dict(file=name, grain=grain, rows=len(gdf), description=desc))


# ---------------------------------------------------------------- California Department of Finance E-5
def dof(src):
    x = pd.ExcelFile(os.path.join(src, 'dof', 'E-5_2026_InternetVersion.xlsx'))
    cols = ['year', 'population', 'household_population', 'group_quarters', 'housing_units', 'single_detached',
            'single_attached', 'two_to_four', 'five_plus', 'mobile_homes', 'occupied', 'vacancy_rate',
            'persons_per_household']
    rows = []
    for sh in [s for s in x.sheet_names if s.startswith('E5CityCounty')]:
        d = pd.read_excel(x, sh, header=None)
        r = d[d[0].astype(str).str.strip() == 'Berkeley']
        assert len(r) == 1, f'{sh}: expected one Berkeley row, found {len(r)}'
        v = r.iloc[0].tolist()
        rows.append(dict(zip(cols, [int(sh[-4:])] + v[1:13])))
    df = write_csv('dof_e5_berkeley_2020_2026.csv', rows, 'city, by year',
                   'Population, household and group-quarters population, housing units by type, occupancy, vacancy '
                   'and persons per household, January 1 of each year (April 1 for 2020).')
    last = df.iloc[-1]
    FACTS['dof'] = dict(year=int(last.year), rows=df.to_dict('records'))
    return df


# ---------------------------------------------------------------- American Community Survey (via Census Reporter)
def acs_load(src, level):
    est, moe, names, release = collections.defaultdict(dict), collections.defaultdict(dict), {}, None
    for f in sorted(glob.glob(os.path.join(src, 'acs', f'{level}_*.json'))):
        d = json.load(open(f))
        release = d['release']
        for t, meta in d['tables'].items():
            for c, cm in meta['columns'].items():
                names[c] = (t, meta['title'], cm['name'])
        for geo, tables in d['data'].items():
            for t, v in tables.items():
                est[geo].update(v['estimate'])
                moe[geo].update(v['error'])
    return est, moe, names, release


def indicators(e):
    """Map-ready indicators from one geography's ACS estimates (column ids are ACS table-column codes)."""
    g = lambda c: e.get(c) or 0
    s = lambda *cs: sum(g(c) for c in cs)
    pct = lambda a, b: round(100 * a / b, 1) if b else None
    male = lambda a, b: [f'B01001{i:03d}' for i in range(a, b + 1)]
    fem = lambda a, b: [f'B01001{i + 24:03d}' for i in range(a, b + 1)]
    age = lambda a, b: s(*male(a, b), *fem(a, b))
    hh = g('B25003001')
    renters_den = g('B25070001') - g('B25070011')
    workers = g('B08301001')
    pop25 = g('B15003001')
    units = g('B25024001')
    yb = g('B25034001')
    out = dict(
        population=g('B01003001'), households=hh, owner_households=g('B25003002'), renter_households=g('B25003003'),
        renter_household_pct=pct(g('B25003003'), hh),
        residents_owner_occupied=g('B25008002'), residents_renter_occupied=g('B25008003'),
        median_household_income=e.get('B19013001'), per_capita_income=e.get('B19301001'),
        hh_income_under_50k=s(*[f'B19001{i:03d}' for i in range(2, 11)]),
        hh_income_50k_100k=s('B19001011', 'B19001012', 'B19001013'),
        hh_income_100k_200k=s('B19001014', 'B19001015', 'B19001016'),
        hh_income_200k_plus=g('B19001017'),
        age_under_18=age(3, 6), age_18_24=age(7, 10), age_25_34=age(11, 12), age_35_64=age(13, 19),
        age_65_plus=age(20, 25),
        households_no_vehicle=s('B25044003', 'B25044010'),
        no_vehicle_pct=pct(s('B25044003', 'B25044010'), hh),
        vehicles_available_min=sum(k * s(f'B25044{3 + k:03d}', f'B25044{10 + k:03d}') for k in range(1, 6)),
        median_gross_rent=e.get('B25064001'), median_home_value=e.get('B25077001'),
        rent_burdened_30pct=pct(s('B25070007', 'B25070008', 'B25070009', 'B25070010'), renters_den),
        rent_burdened_50pct=pct(g('B25070010'), renters_den),
        workers=workers,
        commute_drive_alone_pct=pct(g('B08301003'), workers), commute_carpool_pct=pct(g('B08301004'), workers),
        commute_transit_pct=pct(g('B08301010'), workers), commute_bicycle_pct=pct(g('B08301018'), workers),
        commute_walk_pct=pct(g('B08301019'), workers), commute_work_from_home_pct=pct(g('B08301021'), workers),
        housing_units=g('B25001001'), vacant_units=g('B25004001'),
        units_1_detached_pct=pct(g('B25024002'), units), units_1_attached_pct=pct(g('B25024003'), units),
        units_2_4_pct=pct(s('B25024004', 'B25024005'), units), units_5_19_pct=pct(s('B25024006', 'B25024007'), units),
        units_20_plus_pct=pct(s('B25024008', 'B25024009'), units),
        built_before_1940_pct=pct(g('B25034011'), yb), built_2010_or_later_pct=pct(s('B25034002', 'B25034003'), yb),
        hispanic_pct=pct(g('B03002012'), g('B03002001')), white_nh_pct=pct(g('B03002003'), g('B03002001')),
        black_nh_pct=pct(g('B03002004'), g('B03002001')), asian_nh_pct=pct(g('B03002006'), g('B03002001')),
        bachelors_or_higher_pct=pct(s('B15003022', 'B15003023', 'B15003024', 'B15003025'), pop25),
        below_poverty_pct=pct(g('B17021002'), g('B17021001')),
    )
    return out


def acs(src):
    # city: ACS 2024 1-year, every column in long form, plus the same indicators
    est, moe, names, rel = acs_load(src, 'city')
    geo = next(iter(est))
    long = [dict(table=names[c][0], table_title=names[c][1], column=c, label=names[c][2], estimate=v,
                 margin_of_error=moe[geo].get(c)) for c, v in sorted(est[geo].items())]
    write_csv('acs_city_2024_1yr_all_columns.csv', long, 'city',
              f'Every column of the {len(set(r["table"] for r in long))} ACS tables used, Berkeley city, '
              f'{rel["name"]}, with margins of error.')
    FACTS['acs_city'] = dict(release=rel['name'], ind=indicators(est[geo]),
                             cols={c: [est[geo][c], moe[geo].get(c)] for c in est[geo]})
    # tracts and block groups: ACS 2020-2024 5-year, indicators + geometry
    tiger = {'tract': 'tl_2024_06_tract.zip', 'blockgroup': 'tl_2024_06_bg.zip'}
    for level in ('tract', 'blockgroup'):
        est, moe, names, rel = acs_load(src, level)
        rows = []
        for geoid, e in est.items():
            r = dict(GEOID=geoid.split('US')[1], **indicators(e))
            r['median_household_income_moe'] = moe[geoid].get('B19013001')
            r['population_moe'] = moe[geoid].get('B01003001')
            rows.append(r)
        df = write_csv(f'acs_{level}_2020_2024_5yr.csv', rows, f'census {level} (GEOID)',
                       f'{len(rows)} {level}s within Berkeley: population, tenure, income, age, cars, rents, rent burden, '
                       f'commute mode, housing type and age, race/ethnicity, education, poverty ({rel["name"]}).')
        shp = gpd.read_file('zip://' + os.path.join(src, 'tiger', tiger[level]))
        shp = shp[shp.GEOID.isin(df.GEOID)][['GEOID', 'ALAND', 'AWATER', 'geometry']]
        assert len(shp) == len(df), f'{level}: {len(shp)} boundaries for {len(df)} rows'
        gdf = shp.merge(df, on='GEOID')
        gdf['geometry'] = gdf.geometry.simplify(0.00003)
        write_geojson(f'berkeley_{level}s.geojson', gdf, f'census {level} polygons',
                      f'TIGER 2024 {level} boundaries with every indicator above, ready to map.')
        FACTS[f'acs_{level}'] = dict(release=rel['name'], n=len(df))
        if level == 'blockgroup':
            FACTS['acs_blockgroup']['extremes'] = {
                k: dict(min=float(df[k].min()), max=float(df[k].max()), median=float(df[k].median()))
                for k in ('renter_household_pct', 'median_household_income', 'no_vehicle_pct', 'age_18_24',
                          'median_gross_rent', 'rent_burdened_30pct') if df[k].notna().any()}
    return gpd.read_file(os.path.join(OUT, 'berkeley_blockgroups.geojson'))


# ---------------------------------------------------------------- LEHD LODES 2023
def lodes(src):
    L = os.path.join(src, 'lodes')
    xw = pd.read_csv(os.path.join(L, 'ca_xwalk.csv.gz'), dtype=str,
                     usecols=['tabblk2020', 'stplcname', 'ctyname', 'blklatdd', 'blklondd'])
    berk = set(xw.loc[xw.stplcname.fillna('').str.startswith('Berkeley city'), 'tabblk2020'])
    place = dict(zip(xw.tabblk2020, xw.stplcname.fillna('').str.replace(r', CA$', '', regex=True)))
    county = dict(zip(xw.tabblk2020, xw.ctyname.str.replace(', CA', '', regex=False)))
    lab = lambda b: place.get(b) or f'{county.get(b, "?")} (unincorporated)'
    inflow, outflow, interior, aux_in = collections.Counter(), collections.Counter(), 0, 0
    for chunk in pd.read_csv(os.path.join(L, 'ca_od_main_JT00_2023.csv.gz'), dtype={'w_geocode': str, 'h_geocode': str},
                             usecols=['w_geocode', 'h_geocode', 'S000'], chunksize=2_000_000):
        w, h = chunk.w_geocode.isin(berk), chunk.h_geocode.isin(berk)
        interior += int(chunk.loc[w & h, 'S000'].sum())
        for b, n in chunk.loc[w & ~h].groupby('h_geocode').S000.sum().items():
            inflow[lab(b)] += int(n)
        for b, n in chunk.loc[h & ~w].groupby('w_geocode').S000.sum().items():
            outflow[lab(b)] += int(n)
    for chunk in pd.read_csv(os.path.join(L, 'ca_od_aux_JT00_2023.csv.gz'), dtype={'w_geocode': str},
                             usecols=['w_geocode', 'S000'], chunksize=2_000_000):
        aux_in += int(chunk.loc[chunk.w_geocode.isin(berk), 'S000'].sum())
    inflow['Outside California'] += aux_in
    tin, tout = sum(inflow.values()), sum(outflow.values())
    write_csv('lodes_2023_inflow_by_home_place.csv',
              [dict(home_place=k, workers=v, share_pct=round(100 * v / tin, 2)) for k, v in inflow.most_common()],
              'place (city or unincorporated county)', 'People who work in Berkeley and live elsewhere, by where they live.')
    write_csv('lodes_2023_outflow_by_work_place.csv',
              [dict(work_place=k, workers=v, share_pct=round(100 * v / tout, 2)) for k, v in outflow.most_common()],
              'place (city or unincorporated county)', 'Berkeley residents who work elsewhere in California, by where they work.')
    sectors = {'CNS01': 'Agriculture', 'CNS02': 'Mining', 'CNS03': 'Utilities', 'CNS04': 'Construction',
               'CNS05': 'Manufacturing', 'CNS06': 'Wholesale trade', 'CNS07': 'Retail trade',
               'CNS08': 'Transportation and warehousing', 'CNS09': 'Information', 'CNS10': 'Finance and insurance',
               'CNS11': 'Real estate', 'CNS12': 'Professional, scientific and technical services',
               'CNS13': 'Management of companies', 'CNS14': 'Administrative and waste services',
               'CNS15': 'Educational services', 'CNS16': 'Health care and social assistance',
               'CNS17': 'Arts, entertainment and recreation', 'CNS18': 'Accommodation and food services',
               'CNS19': 'Other services', 'CNS20': 'Public administration'}
    wac = pd.read_csv(os.path.join(L, 'ca_wac_S000_JT00_2023.csv.gz'), dtype={'w_geocode': str})
    wac = wac[wac.w_geocode.isin(berk)]
    rac = pd.read_csv(os.path.join(L, 'ca_rac_S000_JT00_2023.csv.gz'), dtype={'h_geocode': str})
    rac = rac[rac.h_geocode.isin(berk)]
    ll = xw.set_index('tabblk2020')[['blklatdd', 'blklondd']]
    blk = wac[['w_geocode', 'C000', 'CE01', 'CE02', 'CE03'] + list(sectors)].rename(
        columns={'w_geocode': 'block', 'C000': 'jobs', 'CE01': 'jobs_earning_under_1250_mo',
                 'CE02': 'jobs_earning_1251_3333_mo', 'CE03': 'jobs_earning_over_3333_mo', **sectors})
    blk = blk.join(ll, on='block').rename(columns={'blklatdd': 'lat', 'blklondd': 'lon'})
    write_csv('lodes_2023_jobs_by_block.csv', blk, 'census block (with internal-point lat/lon)',
              'Jobs located in each Berkeley census block, by earnings band and industry sector.')
    bg = pd.DataFrame({'GEOID': wac.w_geocode.str[:12], 'jobs': wac.C000}).groupby('GEOID').jobs.sum().to_frame()
    bg['employed_residents'] = rac.groupby(rac.h_geocode.str[:12]).C000.sum()
    write_csv('lodes_2023_by_blockgroup.csv', bg.fillna(0).astype(int).reset_index(), 'census block group (GEOID)',
              'Jobs located in, and employed residents living in, each block group.')
    FACTS['lodes'] = dict(
        year=2023, jobs=int(wac.C000.sum()), interior=interior, inflow=tin, outflow=tout, aux_in=aux_in,
        employed_residents=int(rac.C000.sum()), blocks=len(berk), job_blocks=int((wac.C000 > 0).sum()),
        top_in=inflow.most_common(12), top_out=outflow.most_common(12),
        sectors=sorted(((sectors[c], int(wac[c].sum())) for c in sectors), key=lambda t: -t[1]),
        earnings=[int(wac.CE01.sum()), int(wac.CE02.sum()), int(wac.CE03.sum())])
    assert FACTS['lodes']['jobs'] == interior + tin, 'jobs in Berkeley != live-and-work + inflow'
    # The residence file counts every job a Berkeley resident holds, including jobs in other states; California's
    # flow file has only in-state jobs. The difference is residents working outside California (it cannot be negative).
    FACTS['lodes']['out_of_state_out'] = FACTS['lodes']['employed_residents'] - (interior + tout)
    assert FACTS['lodes']['out_of_state_out'] >= 0, 'more in-state flows than employed residents'


# ---------------------------------------------------------------- DMV registrations, January 1, 2026
def dmv(src):
    d = pd.read_csv(os.path.join(src, 'dmv', 'vehicle-fuel-type-counts-2025.csv'), dtype={'ZIP Code': str})
    d = d[d['ZIP Code'].isin(BERKELEY_ZIPS)]
    as_of = sorted(d.Date.unique())
    g = d.groupby(['ZIP Code', 'Fuel', 'Duty']).Vehicles.sum().reset_index()
    write_csv('dmv_2026_by_zip_fuel_duty.csv', g, 'ZIP code',
              'Registered vehicles by ZIP code, fuel type and light/heavy duty (DMV, as of ' + ', '.join(as_of) + ').')
    z = d.pivot_table(index='ZIP Code', columns='Fuel', values='Vehicles', aggfunc='sum', fill_value=0)
    z['total'] = z.sum(axis=1)
    ev = [c for c in z.columns if c in ('Battery Electric', 'Plug-in Hybrid', 'Hydrogen Fuel Cell')]
    z['zero_emission_and_plug_in'] = z[ev].sum(axis=1)
    z['ev_share_pct'] = (100 * z['zero_emission_and_plug_in'] / z.total).round(1)
    write_csv('dmv_2026_by_zip.csv', z.reset_index(), 'ZIP code', 'Registered vehicles by ZIP code and fuel type, with totals.')
    my = pd.to_numeric(d['Model Year'], errors='coerce')
    FACTS['dmv'] = dict(as_of=as_of, total=int(d.Vehicles.sum()), by_zip=z.total.astype(int).to_dict(),
                        fuel=d.groupby('Fuel').Vehicles.sum().sort_values(ascending=False).astype(int).to_dict(),
                        duty=d.groupby('Duty').Vehicles.sum().astype(int).to_dict(),
                        ev=int(z['zero_emission_and_plug_in'].sum()),
                        older_than_2010=int(d.loc[my < 2010, 'Vehicles'].sum()))


# ---------------------------------------------------------------- Assessor parcels (Feb 2026)
def parcels(bg, hoods, fire):
    con = sqlite3.connect(f"file:{os.path.join(ROOT, 'databases', 'berkeley.db')}?mode=ro", uri=True)
    p = pd.read_sql('SELECT APN, UseCode, Land, Imps, TotalNetValue, Latitude, Longitude, SitusAddre, '
                    'SitusStree, SitusStr_1 FROM parcels', con)
    for c in ('Land', 'Imps', 'TotalNetValue'):
        p[c] = pd.to_numeric(p[c], errors='coerce')
    p['exempt'] = p.TotalNetValue.fillna(0) <= 0
    p['use_group'] = p.UseCode.astype(str).str[:1] + 'xxx'
    gp = gpd.GeoDataFrame(p, geometry=[Point(xy) if xy[0] == xy[0] else None for xy in zip(p.Longitude, p.Latitude)],
                          crs='EPSG:4326')
    gp = gp[gp.geometry.notna()]
    gp = gpd.sjoin(gp, bg[['GEOID', 'geometry']], how='left', predicate='within').drop(columns='index_right')
    gp = gpd.sjoin(gp, hoods[['neighborhood', 'geometry']], how='left', predicate='within').drop(columns='index_right')
    gp = gpd.sjoin(gp, fire[['fire_zone', 'geometry']], how='left', predicate='within').drop(columns='index_right')
    gp['fire_zone'] = gp.fire_zone.fillna(0).astype(int)
    agg = lambda df: pd.Series(dict(parcels=len(df), exempt_parcels=int(df.exempt.sum()),
                                    land_value=int(df.Land.sum()), improvement_value=int(df.Imps.sum()),
                                    net_taxable_value=int(df.TotalNetValue.clip(lower=0).sum())))
    by_use = gp.groupby('UseCode').apply(agg).reset_index().sort_values('parcels', ascending=False)
    write_csv('assessor_by_usecode.csv', by_use, 'County use code',
              'Parcels, exempt parcels, land, improvement and net taxable value by County use code (labels not '
              'published in machine-readable form).')
    for key, grain, name in (('GEOID', 'census block group (GEOID)', 'assessor_by_blockgroup.csv'),
                             ('neighborhood', 'neighborhood (City boundaries)', 'assessor_by_neighborhood.csv'),
                             ('fire_zone', 'City hill fire zone (0-3)', 'assessor_by_fire_zone.csv')):
        df = gp.groupby(key).apply(agg).reset_index()
        df['net_value_per_parcel'] = (df.net_taxable_value / df.parcels).round(0)
        write_csv(name, df, grain, 'Parcels and assessed value: land, buildings, net taxable, exempt parcels.')
    FACTS['assessor'] = dict(parcels=len(p), located=len(gp), exempt=int(p.exempt.sum()),
                             land=int(p.Land.sum()), imps=int(p.Imps.sum()),
                             net=int(p.TotalNetValue.clip(lower=0).sum()),
                             by_group=gp.groupby('use_group').apply(agg).reset_index().to_dict('records'),
                             by_fire=gp.groupby('fire_zone').apply(agg).reset_index().to_dict('records'),
                             by_hood=gp.groupby('neighborhood').apply(agg).reset_index()
                                       .sort_values('net_taxable_value', ascending=False).to_dict('records'))
    return gp


# ---------------------------------------------------------------- Infrastructure (City GIS, 2026-08-30)
def infra(bg, hoods):
    I = os.path.join(ROOT, 'data', 'raw', 'infrastructure')
    rd = lambda n: gpd.read_file(os.path.join(I, f'berkeley_{n}_2026-08-30.geojson')).to_crs(UTM)
    water, sewer, storm, lights = rd('ebmud_water_mains'), rd('sanitary_sewer_mains'), rd('storm_sewer_mains'), rd('streetlights')
    water['mi'] = water.length / M_PER_MI
    sewer['mi'] = sewer.length / M_PER_MI
    storm['mi'] = storm.length / M_PER_MI
    water['decade'] = (water.INSTALLATI // 10 * 10).astype('Int64')
    sewer['install_year'] = pd.to_datetime(sewer.INSTALLDATE, unit='ms', errors='coerce').dt.year
    # tables
    t = water.groupby('decade').mi.sum().round(2).reset_index().rename(columns={'mi': 'miles'})
    write_csv('water_mains_by_install_decade.csv', t, 'city', 'EBMUD water mains in Berkeley, miles by decade installed.')
    t2 = water.groupby('NOMINALDIA').mi.sum().round(2).reset_index().rename(columns={'NOMINALDIA': 'diameter_in', 'mi': 'miles'})
    write_csv('water_mains_by_diameter.csv', t2, 'city', 'EBMUD water mains in Berkeley, miles by nominal diameter (inches).')
    s1 = sewer.groupby('MATERIAL').agg(miles=('mi', 'sum'), segments=('mi', 'size'), planning_cost=('Planning_Cost', 'sum')).round(2).reset_index()
    write_csv('sewer_mains_by_material.csv', s1, 'city',
              'City sanitary sewer mains by pipe material: miles, segments, and the City\'s planning cost.')
    s2 = sewer.groupby('DIAMETER').mi.sum().round(2).reset_index().rename(columns={'DIAMETER': 'diameter_in', 'mi': 'miles'})
    write_csv('sewer_mains_by_diameter.csv', s2, 'city', 'City sanitary sewer mains, miles by diameter (inches).')
    st = storm.groupby('MATERIAL').mi.sum().round(2).reset_index().rename(columns={'mi': 'miles'})
    write_csv('storm_drains_by_material.csv', st, 'city', 'City storm drain mains, miles by material.')
    pm = lights.groupby('POLEMAT').size().reset_index(name='streetlights')
    write_csv('streetlights_by_pole_material.csv', pm, 'city',
              'City streetlights by the material of the pole they hang on (wood = PG&E/AT&T joint-use poles).')
    # by area
    def by_area(areas, key):
        rows = {}
        for name, layer, cols in (('water', water, ['mi', 'INSTALLATI']), ('sewer', sewer, ['mi', 'Planning_Cost']),
                                  ('storm', storm, ['mi'])):
            x = gpd.overlay(layer[['geometry'] + [c for c in cols if c != 'mi']], areas[[key, 'geometry']].to_crs(UTM),
                            how='intersection', keep_geom_type=True)
            x['mi'] = x.length / M_PER_MI
            for k, df in x.groupby(key):
                r = rows.setdefault(k, {key: k})
                r[f'{name}_main_miles'] = round(df.mi.sum(), 2)
                if name == 'water':
                    r['water_main_pre_1940_miles'] = round(df.loc[df.INSTALLATI < 1940, 'mi'].sum(), 2)
                    r['water_main_median_install_year'] = int(df.INSTALLATI.median()) if df.INSTALLATI.notna().any() else None
                if name == 'sewer':
                    r['sewer_planning_cost_on_segments'] = int(df.Planning_Cost.fillna(0).sum())
        wl = gpd.sjoin(lights[lights.POLEMAT == 'Wood'][['geometry']], areas[[key, 'geometry']].to_crs(UTM),
                       predicate='within')
        for k, n in wl.groupby(key).size().items():
            rows.setdefault(k, {key: k})['wood_utility_poles_with_streetlight'] = int(n)
        return pd.DataFrame(rows.values())
    write_csv('infrastructure_by_blockgroup.csv', by_area(bg, 'GEOID'), 'census block group (GEOID)',
              'Miles of water main (and pre-1940 miles, median install year), sewer main, storm drain, and wood '
              'utility poles carrying a streetlight, in each block group.')
    write_csv('infrastructure_by_neighborhood.csv', by_area(hoods, 'neighborhood'), 'neighborhood (City boundaries)',
              'The same measures by neighborhood.')
    FACTS['infra'] = dict(
        water_mi=round(water.mi.sum(), 1), water_segments=len(water),
        water_pre1960_seg_pct=round(100 * (water.INSTALLATI < 1960).sum() / water.INSTALLATI.notna().sum(), 1),
        water_pre1940_mi=round(water.loc[water.INSTALLATI < 1940, 'mi'].sum(), 1),
        water_oldest=int(water.INSTALLATI.min()), water_median_year=int(water.INSTALLATI.median()),
        water_by_decade=t.to_dict('records'), water_by_dia=t2.to_dict('records'),
        sewer_mi=round(sewer.mi.sum(), 1), sewer_segments=len(sewer), sewer_by_material=s1.to_dict('records'),
        sewer_planning_cost=int(sewer.Planning_Cost.fillna(0).sum()),
        sewer_rehab_dated=int(sewer.REHAB_YEAR.notna().sum()),
        storm_mi=round(storm.mi.sum(), 1), storm_segments=len(storm), storm_by_material=st.to_dict('records'),
        poles=pm.to_dict('records'),
        wood_util_pn=int(lights.loc[lights.POLEMAT == 'Wood', 'UTIL_PN'].notna().sum()),
        wood_util_pn_distinct=int(lights.loc[lights.POLEMAT == 'Wood', 'UTIL_PN'].nunique()))
    # POLE LINES traced from the lit wood poles (the only located utility poles that are public). Two streetlight
    # records have no geometry but carry LATITUDE/LONGITUDE, so points are built from those attributes. A minimum
    # spanning tree over each pole's 7 nearest neighbors, keeping links no longer than a plausible span, traces the
    # pole lines; unlit poles break the chain, so the traced length is a FLOOR on overhead pole-line miles.
    import numpy as np
    from scipy.spatial import cKDTree
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import minimum_spanning_tree
    wl = lights[lights.POLEMAT == 'Wood']
    wl = gpd.GeoDataFrame(wl.drop(columns='geometry'), geometry=gpd.points_from_xy(wl.LONGITUDE, wl.LATITUDE),
                          crs='EPSG:4326').to_crs(UTM)
    xy = np.c_[wl.geometry.x, wl.geometry.y]
    dist, idx = cKDTree(xy).query(xy, k=8)
    g = coo_matrix((dist[:, 1:].ravel() / 0.3048, (np.repeat(np.arange(len(xy)), 7), idx[:, 1:].ravel())),
                   shape=(len(xy), len(xy))).tocsr()
    t = minimum_spanning_tree(g).tocoo()
    traced = {cap: dict(links=int((t.data <= cap).sum()), miles=round(float(t.data[t.data <= cap].sum()) / 5280, 1),
                        mean_span_ft=round(float(t.data[t.data <= cap].mean()), 0)) for cap in (150, 200, 250, 300, 400)}
    from shapely.geometry import LineString
    keep = t.data <= 250
    lines = gpd.GeoDataFrame(dict(span_ft=np.round(t.data[keep], 0)),
                             geometry=[LineString([xy[a], xy[b]]) for a, b in zip(t.row[keep], t.col[keep])], crs=UTM)
    write_geojson('wood_pole_lines_traced.geojson', lines, 'pole-to-pole link (line)',
                  'Links between neighboring lit wood utility poles (spans up to 250 ft): the traced overhead pole '
                  'lines. A floor: poles without a streetlight are not in the public data.')
    nn = dist[:, 1] / 0.3048
    FACTS['poles'] = dict(wood=len(wl), nn_median_ft=round(float(np.median(nn))), nn_p25=round(float(np.percentile(nn, 25))),
                          nn_p75=round(float(np.percentile(nn, 75))), traced=traced)
    laterals = gpd.read_file(os.path.join(I, 'berkeley_sanitary_sewer_laterals_2026-08-30.geojson'))
    manholes = gpd.read_file(os.path.join(I, 'berkeley_sanitary_sewer_manholes_2026-08-30.geojson'))
    FACTS['infra'].update(laterals=len(laterals), laterals_mi=round(laterals.to_crs(UTM).length.sum() / M_PER_MI, 1),
                          manholes=len(manholes))


# ---------------------------------------------------------------- Evacuation (KLD 2025)
def evacuation():
    txt = open(glob.glob(os.path.join(ROOT, 'data', 'raw', 'evacuation', 'kld_*.txt'))[0]).read().split('\n')
    i = next(k for k, l in enumerate(txt) if 'Table 7-4. Time to Clear the Indicated Area for Response Plans' in l)
    scen = ['summer_midweek_midday', 'summer_weekend_midday', 'summer_nighttime', 'fall_midweek_midday',
            'fall_weekend_midday', 'fall_nighttime']
    rows = []
    for l in txt[i:i + 40]:
        m = re.match(r'^\s*(R\d\d) - (.*?)\s{2,}((?:\d:\d\d\*?\s+){5}\d:\d\d\*?)\s*$', l)
        if m:
            vals = m.group(3).split()
            rows.append(dict(region=m.group(1), name=m.group(2).strip(),
                             **{s: v.rstrip('*') for s, v in zip(scen, vals)},
                             **{s + '_is_100th_pct': v.endswith('*') for s, v in zip(scen, vals)}))
    assert len(rows) == 21, f'Table 7-4: parsed {len(rows)} rows, expected 21 (R01-R14 with their urgent and phase variants)'
    write_csv('evacuation_clearance_times_kld_2025.csv', rows, 'evacuation region (KLD R01-R14)',
              'Hours:minutes to clear each region, six scenarios (KLD Table 7-4; 90th-percentile vehicle unless flagged 100th).')
    j = next(k for k, l in enumerate(txt) if l.strip().startswith('Table 3-4. Permanent Resident Population and Vehicles')
             and k > i - 5000 and 'Table 3-3' not in l and k > 2000)
    pop = []
    for l in txt[j:j + 14]:
        m = re.match(r'^\s*([A-Za-z][A-Za-z .]+?)(?:\d\d)?\s+([\d,]+)\s+([\d,]+)\s*$', l)
        if m and 'TOTAL' not in m.group(1):
            pop.append(dict(area=m.group(1).strip(), population_2024=int(m.group(2).replace(',', '')),
                            resident_vehicles_2024=int(m.group(3).replace(',', ''))))
    write_csv('evacuation_population_by_area_kld_2025.csv', pop, 'KLD study area',
              'Permanent residents (2024, extrapolated) and resident vehicles by area (KLD Table 3-4; excludes students in dorms).')
    FACTS['evac'] = dict(clear=rows, pop=pop)


# ---------------------------------------------------------------- Undergrounding (Harris & Associates 2016)
def undergrounding_tables():
    rows, totals = undergrounding.parse(glob.glob(os.path.join(ROOT, 'data', 'raw', 'undergrounding', 'Conceptual-Study*.txt'))[0])
    write_csv('undergrounding_segments_harris_2016.csv', rows, 'street segment (street, from, to)',
              'Every arterial and collector street segment: already undergrounded or overhead, with length, three '
              '1-5 impact ratings and the planning-level cost to underground (2016 dollars).')
    seg = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        k = (r['network'], r['street_no'])
        seg[k][0] += r['cost_m_cb_cdmu_sp_zones']; seg[k][1] += r['cost_mur_r_zones']
    disagree = [dict(t, segments_commercial=seg[(t['network'], t['street_no'])][0],
                     segments_residential=seg[(t['network'], t['street_no'])][1]) for t in totals
                if (t['cost_commercial'], t['cost_residential']) != tuple(seg[(t['network'], t['street_no'])])]
    s = {}
    for net in ('arterial', 'collector'):
        R = [r for r in rows if r['network'] == net]
        s[net] = dict(overhead_mi=round(sum(r['length_ft'] for r in R if r['status'] == 'overhead') / 5280, 2),
                      underground_mi=round(sum(r['length_ft'] for r in R if r['status'] == 'undergrounded') / 5280, 2),
                      cost=sum(r['cost_total'] for r in R), segments=len(R),
                      overhead_segments=sum(r['status'] == 'overhead' for r in R),
                      printed_commercial=sum(t['cost_commercial'] for t in totals if t['network'] == net),
                      printed_residential=sum(t['cost_residential'] for t in totals if t['network'] == net))
    # the report's own network totals (TOTAL COST lines), for the check printed on the page
    s['report_network_totals'] = dict(arterial=[11379500, 31549650], collector=[15096700, 76761450], headline=134800000)
    assert s['collector']['cost'] == sum(s['report_network_totals']['collector']), 'collector segments != report total'
    top = sorted(rows, key=lambda r: -r['cost_total'])[:15]
    brows, btot = undergrounding.parse_bellecci(
        glob.glob(os.path.join(ROOT, 'data', 'raw', 'undergrounding', '2020-01-16_Agenda_Packet*.txt'))[0])
    write_csv('undergrounding_evacuation_routes_bellecci_2019.csv', brows, 'street (evacuation route)',
              'Overhead miles, construction complexity (1-5), cost per mile and total cost to underground each '
              'evacuation route, in three versions: FY2019 baseline, FY2023 programmatic, FY2023 capital program.')
    FACTS['ug'] = dict(summary=s, disagree=disagree, top=top, total=sum(r['cost_total'] for r in rows),
                       bellecci=brows, bellecci_totals=btot)


# ---------------------------------------------------------------- Large-building energy (BESO)
def beso(parcel_gdf):
    b = pd.read_csv(os.path.join(ROOT, 'energy', 'beso_energy_5vy5-rwja.csv'), dtype=str)
    b = b[b.beso_id != '0000']                                   # the file's example row ("BUILDING NAME")
    num = lambda c: pd.to_numeric(b[c].str.replace(',', ''), errors='coerce')
    out = pd.DataFrame(dict(beso_id=b.beso_id, name=b.property_building_name, address=b.building_address,
                            property_type=b.beso_property_type, floor_area_sqft=num('floor_area')))
    for y in (2021, 2022, 2023, 2024):
        kwh = [c for c in b.columns if c.startswith(f'_{y}_electricity')][0]
        gas = [c for c in b.columns if c.startswith(f'_{y}_natural_gas')][0]
        out[f'electricity_kwh_{y}'] = num(kwh)
        # Gas is in THERMS in every year. The City's 2021-2023 columns are NAMED "..._kbtu_", but the file's own site
        # EUI is reproduced only if they are therms: (kWh x 3.412 + gas x 100) / floor area / EUI has a median of 1.000
        # for each year 2021-2024 (and about 0.40 if the gas were kBtu). Checked 2026-10-01.
        out[f'gas_therms_{y}'] = num(gas)
        out[f'energy_star_{y}'] = num([c for c in b.columns if c.startswith(f'_{y}_energy_star')][0])
        out[f'site_eui_{y}'] = num([c for c in b.columns if c.startswith(f'_{y}_site_eui')][0])
    # locate each building on the Assessor's parcel by the address canon (house number + street must agree)
    key = lambda a: '|'.join(normalize_address(a)) if isinstance(a, str) and all(normalize_address(a)) else None
    pk = {}
    for a, lat, lon in zip(parcel_gdf.SitusAddre, parcel_gdf.Latitude, parcel_gdf.Longitude):
        k = key(a)
        if k and k not in pk:
            pk[k] = (lat, lon)
    loc = [pk.get(key(a)) for a in out.address]
    out['lat'] = [l[0] if l else None for l in loc]
    out['lon'] = [l[1] if l else None for l in loc]
    write_csv('beso_large_buildings_energy.csv', out, 'building (address; lat/lon from the Assessor parcel)',
              'Every building in the City\'s Building Emissions Saving Ordinance data: type, floor area, electricity '
              '(kWh) and gas (therms) 2021-2024, ENERGY STAR score and energy intensity.')
    bt = out.groupby('property_type').agg(buildings=('beso_id', 'size'), floor_area_sqft=('floor_area_sqft', 'sum'),
                                          electricity_kwh_2024=('electricity_kwh_2024', 'sum'),
                                          gas_therms_2024=('gas_therms_2024', 'sum')).reset_index() \
           .sort_values('electricity_kwh_2024', ascending=False)
    write_csv('beso_by_property_type.csv', bt, 'building type', '2024 electricity and gas by building type.')
    FACTS['beso'] = dict(buildings=len(out), located=int(out.lat.notna().sum()),
                         years={y: dict(kwh=float(out[f'electricity_kwh_{y}'].sum()), kwh_n=int(out[f'electricity_kwh_{y}'].notna().sum()),
                                        therms=float(out[f'gas_therms_{y}'].sum()), therms_n=int(out[f'gas_therms_{y}'].notna().sum()))
                                for y in (2021, 2022, 2023, 2024)},
                         by_type=bt.head(12).to_dict('records'))


def campus_sustainability():
    """UC Berkeley and Berkeley Lab, from the UC Annual Report on Sustainable Practices 2025: the report's charts read
    public Google Sheets (one per chart), fetched 2026-10-01 into data/raw/campus/ucop2025_sheets_{ucb,lbnl}.json.
    Emissions are the report's own series (Scope 1 NET of compliance offsets); EUI is kBtu per square foot; water is
    gallons per person; renewable electricity is MWh."""
    C = os.path.join(ROOT, 'data', 'raw', 'campus')
    num = lambda x: float(str(x).replace(',', '').strip()) if str(x).strip() not in ('', None) else None
    out, facts = [], {}
    for tag, name in (('ucb', 'UC Berkeley'), ('lbnl', 'Berkeley Lab')):
        sh = json.load(open(os.path.join(C, f'ucop2025_sheets_{tag}.json')))
        get = lambda pred: next(v['values'] for k, v in sh.items() if pred(k, v.get('values') or [[]]))
        em = get(lambda k, v: v[0][:2] == ['Calendar year', 'Scope 1 net emissions'])
        eui = {r[0]: num(r[1]) for r in get(lambda k, v: len(v[0]) > 1 and 'EUI' in v[0][1])[1:]}
        wat = {r[0].rstrip('*'): num(r[1]) for r in get(lambda k, v: v[0][:1] == ['Year'])[1:]}
        for r in em[1:]:
            y = r[0].rstrip('*')
            if not y.isdigit() or int(y) > 2026 or len(r) < 4 or not r[1]:
                continue
            row = dict(institution=name, year=int(y), scope1_net=num(r[1]), scope2=num(r[2]), scope3=num(r[3]),
                       compliance_offsets=num(r[4]) if len(r) > 4 else None, eui_kbtu_per_sqft=eui.get(y))
            row['total'] = sum(v or 0 for v in (row['scope1_net'], row['scope2'], row['scope3']))
            out.append(row)
        facts[tag] = dict(rows=[r for r in out if r['institution'] == name], water_gal_per_person=wat)
        if tag == 'ucb':
            ren = get(lambda k, v: v[0][:1] == ['Supply Option Type'])
            facts[tag]['renewable_mwh'] = {r[0]: {ren[0][i]: num(x) for i, x in enumerate(r[1:], 1)} for r in ren[1:]}
    write_csv('campus_lab_emissions_energy_2009_2024.csv', out, 'institution × year',
              'UC Berkeley and Berkeley Lab greenhouse-gas emissions by scope (metric tons CO2e; Scope 1 net of compliance '
              'offsets) and energy use intensity (kBtu per sq ft), from the UC Annual Report on Sustainable Practices 2025.')
    s = open(os.path.join(C, 'stars_ucb_2025-02-19_summary.html')).read()
    facts['stars'] = dict(rating='Platinum', score=86.76, valid_through='April 20, 2028', submitted='February 19, 2025')
    assert 'Platinum 86.76' in re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)), 'STARS summary no longer reads Platinum 86.76'
    FACTS['campus_sus'] = facts


def stars_2025():
    """Fields from UC Berkeley's 2025 AASHE STARS report (performance year 2023 unless stated), read from the credit pages
    saved by fetch_stars.py (data/raw/campus/stars_2025/, pinned in its manifest). Each field is the line after its label."""
    D = os.path.join(ROOT, 'data', 'raw', 'campus', 'stars_2025')
    want = {'OP-5': ['Performance year for energy use:', 'Gross floor area of building space:',
                     'Electricity generated by on-site renewable systems:', 'Electricity from off-site sources:',
                     'Natural gas:', 'Heating oil:', 'Total electricity consumption:', 'Total annual energy consumption:',
                     'Annual energy consumption per unit of floor area:', 'Percentage of energy from renewable sources:'],
            'OP-6': ['Performance year for scope 1 and 2 GHG emissions:', 'Scope 1 GHG emissions from stationary combustion:',
                     'Scope 1 GHG emissions from mobile combustion:', 'Scope 1 GHG fugitive emissions:',
                     'Scope 2 GHG emissions from off-site sources of electricity (market-based):',
                     'Annual scope 1 and 2 GHG emissions:', 'Scope 3 GHG emissions from business travel:',
                     'Scope 3 GHG emissions from commuting:'],
            'OP-3': ['Performance year for water use:', 'Annual potable water use:', 'Level of physical water quantity risk for the institution’s main campus:'],
            'OP-14': ['Performance year for commute modal split:', 'Percentage of students that use more sustainable commuting options:',
                      'Percentage of employees that use more sustainable commuting options:'],
            'PRE-3': ['Full-time equivalent student enrollment:', 'Full-time equivalent of employees:',
                      'Percentage of students that live in campus housing:']}
    rows, f = [], {}
    for credit, labels in want.items():
        lines = [l.strip() for l in open(os.path.join(D, f'{credit}.txt')).read().split('\n') if l.strip()]
        for lab in labels:
            i = lines.index(lab)
            val = lines[i + 1]
            rows.append(dict(credit=credit, field=lab.rstrip(':'), value=val))
            f[(credit, lab.rstrip(':'))] = val
    write_csv('stars_2025_ucb_operations.csv', rows, 'credit field',
              'UC Berkeley 2025 AASHE STARS report, operations fields as submitted (performance year 2023 unless stated).')
    num = lambda k: float(re.match(r'[\d,.]+', f[k]).group(0).replace(',', ''))
    stat = num(('OP-6', 'Scope 1 GHG emissions from stationary combustion'))
    # Gas implied by the reported stationary-combustion emissions, at the campus's own factor of 53.02 kg CO2 per MMBtu
    # (2021 LRDP EIR GHG appendix). CO2 only, so it slightly overstates the gas; 1 MMBtu = 0.29307 MWh.
    implied_mwh = stat / 0.05302 * 0.29307
    FACTS['stars2025'] = dict(fields={f'{a}|{b}': v for (a, b), v in f.items()}, stationary_t=stat,
                              implied_gas_mwh=implied_mwh, gas_mwh=num(('OP-5', 'Natural gas')),
                              total_mwh=num(('OP-5', 'Total annual energy consumption')),
                              elec_offsite_mwh=num(('OP-5', 'Electricity from off-site sources')),
                              elec_solar_mwh=num(('OP-5', 'Electricity generated by on-site renewable systems')),
                              floor_m2=num(('OP-5', 'Gross floor area of building space')),
                              water_m3=num(('OP-3', 'Annual potable water use')),
                              commute_students=num(('OP-14', 'Percentage of students that use more sustainable commuting options')),
                              commute_employees=num(('OP-14', 'Percentage of employees that use more sustainable commuting options')),
                              housed_pct=num(('PRE-3', 'Percentage of students that live in campus housing')))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--date', default='2026-10-01')
    src = os.path.join(ROOT, 'data', 'raw', 'snapshot', ap.parse_args().date)
    manifest = json.load(open(os.path.join(src, 'manifest.json')))
    hoods = gpd.read_file(os.path.join(ROOT, 'data', 'reference', 'berkeley_neighborhoods.geojson')).rename(columns={'Name': 'neighborhood'})
    fire = gpd.read_file(os.path.join(ROOT, 'data', 'reference', 'berkeley_fire_hill_zones.geojson')).rename(columns={'PLN_HILL_Z': 'fire_zone'})
    hoods, fire = hoods.to_crs('EPSG:4326'), fire.to_crs('EPSG:4326')
    dof(src)
    bg = acs(src)
    lodes(src)
    dmv(src)
    pg = parcels(bg, hoods, fire)
    infra(bg, hoods)
    evacuation()
    undergrounding_tables()
    beso(pg)
    campus_sustainability()
    stars_2025()
    FACTS['files'] = FILES
    FACTS['sources_manifest'] = {k: {kk: v[kk] for kk in ('url', 'fetched_at', 'sha256') if kk in v} for k, v in manifest.items()}
    json.dump(FACTS, open(os.path.join(OUT, 'facts.json'), 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print(f'{len(FILES)} data files + facts.json in {OUT}')
    for f in FILES:
        print(f"  {f['rows']:7,}  {f['file']}")


if __name__ == '__main__':
    main()
