"""
Data Loader Module

Functions for loading permit data from Berkeley Open Data API,
CSV files, and SQLite databases.
"""

import pandas as pd
import sqlite3
import os
from pathlib import Path
from typing import Optional, Dict, List, Any

# Try to import sodapy, handle if not installed
try:
    from sodapy import Socrata
    SODAPY_AVAILABLE = True
except ImportError:
    SODAPY_AVAILABLE = False
    print("Warning: sodapy not installed. API fetching disabled.")

# Berkeley Open Data Portal configuration
BERKELEY_DOMAIN = "data.cityofberkeley.info"

# Dataset IDs for Berkeley Open Data Portal
DATASETS = {
    'business_licenses': 'rwnf-bu3w',
    'building_permits': 'ydr8-5enu',
    'zoning_permits': 'vkhm-tsvp',  # Use Permits - Zoning
    'planning_records': 'rk4r-58ys',  # Planning records
    'crime_incidents': 'k2nh-s5h5',
    'restaurant_inspections': 'b47j-kakm',
}

# Default paths
DEFAULT_DATA_DIR = Path(__file__).parent.parent
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "berkeley_housing_map.db"


def get_socrata_client(app_token: Optional[str] = None) -> Optional[Any]:
    """
    Initialize Socrata client for Berkeley Open Data API.

    Parameters
    ----------
    app_token : str, optional
        API app token. If not provided, tries to load from environment.

    Returns
    -------
    Socrata client or None if not available
    """
    if not SODAPY_AVAILABLE:
        print("Error: sodapy not installed. Run: pip install sodapy")
        return None

    # Try environment variable if no token provided
    if app_token is None:
        app_token = os.environ.get('BERKELEY_APP_TOKEN')

    if app_token:
        print(f"Using app token: {app_token[:8]}...")
    else:
        print("Warning: No app token. API requests may be rate-limited.")

    return Socrata(BERKELEY_DOMAIN, app_token)


def load_permits_from_api(
    dataset_name: str,
    limit: int = 10000,
    filters: Optional[Dict] = None,
    app_token: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    Fetch permit data from Berkeley Open Data Portal.

    Parameters
    ----------
    dataset_name : str
        Name of dataset (e.g., 'building_permits', 'zoning_permits')
    limit : int
        Maximum records to fetch (default 10000)
    filters : dict, optional
        SoQL filters (e.g., {'status': 'Approved'})
    app_token : str, optional
        API app token

    Returns
    -------
    pd.DataFrame or None if error

    Example
    -------
    >>> df = load_permits_from_api('building_permits', limit=5000)
    >>> print(f"Loaded {len(df)} permits")
    """
    client = get_socrata_client(app_token)
    if client is None:
        return None

    dataset_id = DATASETS.get(dataset_name)
    if not dataset_id:
        print(f"Error: Unknown dataset '{dataset_name}'")
        print(f"Available: {list(DATASETS.keys())}")
        return None

    try:
        print(f"Fetching {dataset_name} from Berkeley Open Data...")

        params = {"$limit": limit}
        if filters:
            where_clauses = [f"{k}='{v}'" for k, v in filters.items()]
            params["$where"] = " AND ".join(where_clauses)

        results = client.get(dataset_id, **params)
        df = pd.DataFrame.from_records(results)

        print(f"Fetched {len(df):,} records")
        return df

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


def load_csv(
    filepath: str,
    encoding: str = 'utf-8',
    date_columns: Optional[List[str]] = None,
    dtype: Optional[Dict] = None
) -> Optional[pd.DataFrame]:
    """
    Load CSV file with common preprocessing.

    Parameters
    ----------
    filepath : str
        Path to CSV file
    encoding : str
        File encoding (default utf-8)
    date_columns : list, optional
        Columns to parse as dates
    dtype : dict, optional
        Column data types

    Returns
    -------
    pd.DataFrame or None if error
    """
    try:
        filepath = Path(filepath)

        if not filepath.exists():
            print(f"Error: File not found: {filepath}")
            return None

        df = pd.read_csv(
            filepath,
            encoding=encoding,
            dtype=dtype,
            parse_dates=date_columns or []
        )

        print(f"Loaded {len(df):,} rows from {filepath.name}")
        return df

    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None


def load_database(
    query: str,
    db_path: str = None
) -> Optional[pd.DataFrame]:
    """
    Execute SQL query on SQLite database.

    Parameters
    ----------
    query : str
        SQL query to execute
    db_path : str, optional
        Path to database (default: berkeley_housing_map.db)

    Returns
    -------
    pd.DataFrame or None if error

    Example
    -------
    >>> df = load_database("SELECT * FROM projects WHERE net_units > 50")
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()

        print(f"Query returned {len(df):,} rows")
        return df

    except Exception as e:
        print(f"Database error: {e}")
        return None


def save_to_database(
    df: pd.DataFrame,
    table_name: str,
    db_path: str = None,
    if_exists: str = 'replace'
) -> bool:
    """
    Save DataFrame to SQLite database.

    Parameters
    ----------
    df : pd.DataFrame
        Data to save
    table_name : str
        Target table name
    db_path : str, optional
        Database path
    if_exists : str
        How to handle existing table ('replace', 'append', 'fail')

    Returns
    -------
    bool : Success status
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        # Convert datetime columns to strings for SQLite
        df_copy = df.copy()
        for col in df_copy.select_dtypes(include=['datetime64']).columns:
            df_copy[col] = df_copy[col].astype(str)

        conn = sqlite3.connect(db_path)
        df_copy.to_sql(table_name, conn, if_exists=if_exists, index=False)
        conn.close()

        print(f"Saved {len(df):,} rows to '{table_name}'")
        return True

    except Exception as e:
        print(f"Error saving to database: {e}")
        return False


def get_table_info(db_path: str = None) -> Dict[str, List[str]]:
    """
    Get list of tables and their columns from database.

    Returns
    -------
    dict : {table_name: [column_names]}
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        result = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            result[table] = columns

        conn.close()
        return result

    except Exception as e:
        print(f"Error getting table info: {e}")
        return {}
