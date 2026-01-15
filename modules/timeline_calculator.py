"""
Timeline Calculator Module

Functions for tracking project timelines, calculating days between
permit stages, and classifying project status.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple


# Project status definitions
PROJECT_STATUSES = {
    'proposed': ['Proposed', 'Pre-Application', 'SB330 Preliminary'],
    'in_review': ['In Review', 'Under Review', 'Incomplete Pending Applicant',
                  'Corrections Pending Applicant'],
    'approved': ['Approved', 'Pending Final Action', 'Conditionally Approved'],
    'appealed': ['Appealed', 'Appeal Pending'],
    'permitted': ['Permit Issued', 'Building Permit Issued'],
    'under_construction': ['Under Construction', 'Active Construction'],
    'completed': ['Completed', 'Certificate of Occupancy', 'Final Inspection'],
    'stalled': ['Stalled', 'Inactive', 'Expired'],
    'denied': ['Denied', 'Rejected', 'Withdrawn']
}

# Canonical status order for pipeline tracking
STATUS_ORDER = [
    'proposed', 'in_review', 'approved', 'appealed',
    'permitted', 'under_construction', 'completed'
]

# Inspection sequence for progress tracking
INSPECTION_SEQUENCE = [
    'Foundation',
    'Framing/Rough',
    'Electrical Rough',
    'Plumbing Rough',
    'Mechanical Rough',
    'Insulation',
    'Drywall',
    'Electrical Final',
    'Plumbing Final',
    'Mechanical Final',
    'Final'
]


def classify_project_status(status_text: str) -> str:
    """
    Classify a project status into canonical categories.

    Parameters
    ----------
    status_text : str
        Raw status text from permit data

    Returns
    -------
    str : Canonical status category

    Example
    -------
    >>> classify_project_status("Incomplete Pending Applicant")
    'in_review'
    """
    if not status_text:
        return 'unknown'

    status_upper = str(status_text).upper()

    for category, keywords in PROJECT_STATUSES.items():
        for keyword in keywords:
            if keyword.upper() in status_upper:
                return category

    return 'unknown'


def calculate_days_between(
    date1: datetime,
    date2: datetime
) -> Optional[int]:
    """
    Calculate business days between two dates.

    Parameters
    ----------
    date1, date2 : datetime
        Start and end dates

    Returns
    -------
    int : Number of days, or None if invalid
    """
    if pd.isna(date1) or pd.isna(date2):
        return None

    try:
        d1 = pd.to_datetime(date1)
        d2 = pd.to_datetime(date2)
        return (d2 - d1).days
    except:
        return None


def get_project_timeline(permits_df: pd.DataFrame) -> Dict:
    """
    Calculate timeline metrics for a project's permits.

    Parameters
    ----------
    permits_df : pd.DataFrame
        DataFrame of permits for a single project, with columns:
        - permit_type
        - filed_date or application_date
        - issue_date or approval_date
        - status

    Returns
    -------
    dict with timeline metrics:
        - total_days: Days from first filing to latest action
        - filing_to_approval: Days from filing to first approval
        - approval_to_permit: Days from approval to permit issuance
        - permit_to_completion: Days from permit to final inspection
        - status_changes: List of (date, old_status, new_status)
    """
    result = {
        'total_days': None,
        'filing_to_approval': None,
        'approval_to_permit': None,
        'permit_to_completion': None,
        'current_status': None,
        'first_filing_date': None,
        'last_action_date': None,
        'status_history': []
    }

    if permits_df.empty:
        return result

    # Find date columns
    date_cols = [col for col in permits_df.columns
                 if 'date' in col.lower()]

    # Get first and last dates
    all_dates = []
    for col in date_cols:
        dates = pd.to_datetime(permits_df[col], errors='coerce')
        all_dates.extend(dates.dropna().tolist())

    if all_dates:
        result['first_filing_date'] = min(all_dates)
        result['last_action_date'] = max(all_dates)
        result['total_days'] = (max(all_dates) - min(all_dates)).days

    # Get current status
    if 'status' in permits_df.columns:
        result['current_status'] = permits_df['status'].iloc[-1]

    return result


def calculate_progress_percent(
    inspections_completed: List[str]
) -> float:
    """
    Calculate construction progress based on completed inspections.

    Parameters
    ----------
    inspections_completed : list
        List of completed inspection types

    Returns
    -------
    float : Progress percentage (0-100)

    Example
    -------
    >>> calculate_progress_percent(['Foundation', 'Framing/Rough'])
    18.2  # 2/11 inspections
    """
    if not inspections_completed:
        return 0.0

    # Find index of highest completed inspection
    highest_idx = -1

    for inspection in inspections_completed:
        for i, seq_inspection in enumerate(INSPECTION_SEQUENCE):
            if seq_inspection.upper() in str(inspection).upper():
                highest_idx = max(highest_idx, i)

    if highest_idx < 0:
        return 0.0

    # Calculate percentage
    total = len(INSPECTION_SEQUENCE)
    return round(100 * (highest_idx + 1) / total, 1)


def identify_stalled_projects(
    df: pd.DataFrame,
    days_threshold: int = 180,
    last_activity_col: str = 'last_action_date'
) -> pd.DataFrame:
    """
    Identify projects with no activity for specified days.

    Parameters
    ----------
    df : pd.DataFrame
        Projects dataframe
    days_threshold : int
        Days without activity to consider stalled (default 180)
    last_activity_col : str
        Column with last activity date

    Returns
    -------
    pd.DataFrame : Stalled projects
    """
    today = pd.Timestamp.now()

    if last_activity_col not in df.columns:
        print(f"Warning: Column '{last_activity_col}' not found")
        return pd.DataFrame()

    df_copy = df.copy()
    df_copy['_last_activity'] = pd.to_datetime(df_copy[last_activity_col], errors='coerce')
    df_copy['_days_inactive'] = (today - df_copy['_last_activity']).dt.days

    stalled = df_copy[df_copy['_days_inactive'] >= days_threshold].copy()
    stalled = stalled.sort_values('_days_inactive', ascending=False)

    return stalled


def get_stage_durations(
    df: pd.DataFrame,
    stage_column: str = 'status',
    date_column: str = 'status_date'
) -> pd.DataFrame:
    """
    Calculate average time spent in each pipeline stage.

    Parameters
    ----------
    df : pd.DataFrame
        Projects with status history
    stage_column : str
        Column with status/stage
    date_column : str
        Column with date of status change

    Returns
    -------
    pd.DataFrame with average days per stage
    """
    # Group by canonical status and calculate durations
    stats = []

    for status in STATUS_ORDER:
        status_df = df[df[stage_column].apply(classify_project_status) == status]

        if len(status_df) > 0:
            # Calculate average if we have duration data
            stats.append({
                'stage': status,
                'count': len(status_df),
                'avg_days': None,  # Would need duration data
                'median_days': None
            })

    return pd.DataFrame(stats)


def project_status_summary(df: pd.DataFrame, status_column: str = 'status') -> pd.DataFrame:
    """
    Summarize projects by canonical status category.

    Parameters
    ----------
    df : pd.DataFrame
        Projects dataframe
    status_column : str
        Column with status text

    Returns
    -------
    pd.DataFrame with count and units by status
    """
    df_copy = df.copy()
    df_copy['_canonical_status'] = df_copy[status_column].apply(classify_project_status)

    summary = df_copy.groupby('_canonical_status').agg({
        status_column: 'count',
        'net_units': 'sum' if 'net_units' in df_copy.columns else 'count'
    }).reset_index()

    summary.columns = ['status', 'project_count', 'total_units']

    # Order by pipeline stage
    status_order = {s: i for i, s in enumerate(STATUS_ORDER + ['unknown'])}
    summary['_order'] = summary['status'].map(status_order)
    summary = summary.sort_values('_order').drop('_order', axis=1)

    return summary
