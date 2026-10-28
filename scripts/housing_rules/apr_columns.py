"""THE reader for HCD APR Table A2 column names (lifted 2026-10-28).

HCD renames columns between pulls. The CO extremely-low non-deed-restricted column was
`CO_EXTREMELY_INCOME_NDR` in the 2026-06-17 pull and is `CO_EXTREMELY_LOW_INCOME_NDR` on the portal
now (found by the San Francisco test run, notes/2026-10-28_sf_test_run.md). Five scripts and notebooks
each typed the old name, so a fresh pull failed with `no such column`. Read the table's own columns
instead: each canonical name resolves to whichever spelling the table carries.

    from housing_rules.apr_columns import co_unit_columns, co_units_sql
    cols = co_unit_columns(con)            # the 11 CO tier columns as THIS table spells them
    con.execute(f"SELECT YEAR, SUM({co_units_sql(con)}) FROM table_a2 ...")
"""

# canonical name -> older spellings HCD has used
CO_UNIT_COLUMNS = {
    'CO_ACUTELY_LOW_INCOME_DR': [],
    'CO_ACUTELY_LOW_INCOME_NDR': [],
    'CO_EXTREMELY_LOW_INCOME_DR': [],
    'CO_EXTREMELY_LOW_INCOME_NDR': ['CO_EXTREMELY_INCOME_NDR'],
    'CO_VLOW_INCOME_DR': [],
    'CO_VLOW_INCOME_NDR': [],
    'CO_LOW_INCOME_DR': [],
    'CO_LOW_INCOME_NDR': [],
    'CO_MOD_INCOME_DR': [],
    'CO_MOD_INCOME_NDR': [],
    'CO_ABOVE_MOD_INCOME': [],
}


def co_unit_columns(con, table='table_a2'):
    """The CO unit columns as `table` spells them. Raises if a canonical column has no spelling
    present (a NEW rename), rather than silently summing fewer tiers."""
    have = {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}
    if not have:
        raise ValueError(f'no table {table!r} in this database')
    out, missing = [], []
    for name, aliases in CO_UNIT_COLUMNS.items():
        hit = next((c for c in [name] + aliases if c in have), None)
        (out.append(hit) if hit else missing.append(name))
    if missing:
        raise ValueError(f'{table}: no column for {missing}; HCD may have renamed it again '
                         f'(add the new spelling to CO_UNIT_COLUMNS)')
    return out


def co_units_sql(con, table='table_a2'):
    """A SQL expression summing the CO unit columns, blanks read as 0."""
    return '+'.join(f"COALESCE(CAST(NULLIF(\"{c}\",'') AS INT),0)" for c in co_unit_columns(con, table))
