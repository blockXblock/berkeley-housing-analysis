"""Cases for housing_rules.address.normalize_address (2026-10-13). Run: .venv/bin/python -m scripts.housing_rules.test_address"""
from scripts.housing_rules.address import normalize_address

CASES = {  # raw -> expected (house, street)
    '2811 KELSEY ST, BERKELEY CA 94705 United States': ('2811', 'kelsey'),
    '1471 SCENIC AVE, Berkeley CA': ('1471', 'scenic'),
    '901 GILMAN St, 94702 United States': ('901', 'gilman'),
    '1670 UNIVERSITY AVE  3 BERKELEY 94703': ('1670', 'university'),
    '2615 TELEGRAPH AVE  101 BERKELEY 94704': ('2615', 'telegraph'),
    '1330 HASKELL St, Rear': ('1330', 'haskell'),
    '1345 PARKER St REAR': ('1345', 'parker'),
    '901 GILMAN St, Suite C, BERKELEY CA 94710': ('901', 'gilman'),
    '1800 HARMON ST LOWER, BERKELEY, CA 94703': ('1800', 'harmon'),
    '1431 ALLSTON UNIT 1, BERKELEY, CA 94702': ('1431', 'allston'),
    '1817 Carleton St B': ('1817', 'carleton'),
    '739 Channing Way Vacant Lot': ('739', 'channing'),
    '2108 Berkeley Way, Berkeley, CA 94704': ('2108', 'berkeley'),
    '2108 BERKELEY WAY': ('2108', 'berkeley'),
    '1828 BERKELEY Way': ('1828', 'berkeley'),
    '1222 SIXTY-SIXTH St': ('1222', '66th'),
    '2010 5TH ST, BERKELEY, CA 94710': ('2010', '5th'),
    '2010 FIFTH ST': ('2010', '5th'),
    '7TH ST': ('', '7th'),
    '2099 M L KING JR WAY': ('2099', 'martin luther king jr'),
    '2099 Martin Luther King Jr Way': ('2099', 'martin luther king jr'),
    '2099 MLK Way': ('2099', 'martin luther king jr'),
    '2099 M.L.K. Jr. Way': ('2099', 'martin luther king jr'),
    '2765.5 Wallace St': ('2765.5', 'wallace'),
    '10 Rose Walk': ('10', 'rose walk'),
    '10 Rose St': ('10', 'rose'),
    '10 Rose WK': ('10', 'rose walk'),
    '100 Indian Rock Path': ('100', 'indian rock path'),
    '100 Indian Rock Ave': ('100', 'indian rock'),
    '2811 Benvenue AV': ('2811', 'benvenue'),
    '1000 THE ALAMEDA BERKELEY 94707': ('1000', 'the alameda'),
    '50 THE UPLANDS': ('50', 'the uplands'),
    '1500 EL CAMINO REAL BERKELEY 94705': ('1500', 'el camino real'),
    ' UNIVERSITY AVE BERKELEY 94710': ('', 'university'),
    '2600 St Charles St': ('2600', 'st charles'),
    '1 Terrace WK': ('1', 'terrace walk'),
    '1 Court St': ('1', 'court'),
    '1400 CALIFORNIA, BERKELEY, CA 94703': ('1400', 'california'),
    '1427 California': ('1427', 'california'),
    '1427 California St Berkeley California 94703': ('1427', 'california'),
    '1 Main St, Berkeley, California 94703': ('1', 'main'),
    '1231 HENRY ST  1/2 BERKELEY 94709': ('1231.5', 'henry'),
}


def test_cases():
    bad = {raw: (normalize_address(raw), want) for raw, want in CASES.items() if normalize_address(raw) != want}
    assert not bad, bad


if __name__ == "__main__":
    test_cases()
    print(f"{len(CASES)} address cases pass")
