"""apr_columns: both HCD spellings resolve; a new rename fails loudly. Run: python -m scripts.housing_rules.test_apr_columns"""
import sqlite3
from scripts.housing_rules.apr_columns import CO_UNIT_COLUMNS, co_unit_columns, co_units_sql


def _table(names):
    con = sqlite3.connect(':memory:')
    con.execute(f'CREATE TABLE table_a2 ({", ".join(names)}, YEAR)')
    con.execute(f'INSERT INTO table_a2 VALUES ({", ".join(["1"] * len(names))}, 2024)')
    con.execute(f'INSERT INTO table_a2 VALUES ({", ".join(["\'\'"] * len(names))}, 2024)')   # a blank row reads as 0
    return con


new = list(CO_UNIT_COLUMNS)
old = [c if c != 'CO_EXTREMELY_LOW_INCOME_NDR' else 'CO_EXTREMELY_INCOME_NDR' for c in new]
for names in (new, old):
    con = _table(names)
    assert co_unit_columns(con) == names
    assert con.execute(f'SELECT SUM({co_units_sql(con)}) FROM table_a2').fetchone()[0] == 11
try:
    co_unit_columns(_table(new[:-1]))
    raise AssertionError('a missing column must raise')
except ValueError as e:
    assert 'CO_ABOVE_MOD_INCOME' in str(e)
print('apr_columns: PASS (current spelling, 2026-06 spelling, missing column raises)')
