"""
Report Generator Module

Functions for generating monthly reports, status summaries,
and exporting data for dashboards.
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


def generate_status_summary(
    df: pd.DataFrame,
    status_column: str = 'status',
    units_column: str = 'net_units'
) -> Dict[str, Any]:
    """
    Generate a status summary for projects.

    Parameters
    ----------
    df : pd.DataFrame
        Projects dataframe
    status_column : str
        Column with status
    units_column : str
        Column with unit counts

    Returns
    -------
    dict with summary statistics
    """
    summary = {
        'generated_at': datetime.now().isoformat(),
        'total_projects': len(df),
        'total_units': 0,
        'by_status': {},
        'by_size': {},
        'by_year': {}
    }

    # Total units
    if units_column in df.columns:
        summary['total_units'] = int(df[units_column].fillna(0).sum())

    # By status
    if status_column in df.columns:
        status_counts = df[status_column].value_counts().to_dict()
        summary['by_status'] = {str(k): int(v) for k, v in status_counts.items()}

    # By size category
    if 'project_size_category' in df.columns:
        size_counts = df['project_size_category'].value_counts().to_dict()
        summary['by_size'] = {str(k): int(v) for k, v in size_counts.items()}

    # By year
    if 'year' in df.columns:
        year_counts = df['year'].value_counts().sort_index().to_dict()
        summary['by_year'] = {str(int(k)): int(v) for k, v in year_counts.items() if pd.notna(k)}

    return summary


def generate_monthly_report(
    df: pd.DataFrame,
    month: Optional[datetime] = None,
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Generate a monthly housing report.

    Parameters
    ----------
    df : pd.DataFrame
        Projects dataframe
    month : datetime, optional
        Month to report on (default: current month)
    include_details : bool
        Include detailed project lists

    Returns
    -------
    dict with monthly report data
    """
    if month is None:
        month = datetime.now()

    month_start = month.replace(day=1)
    if month.month == 12:
        month_end = month.replace(year=month.year+1, month=1, day=1)
    else:
        month_end = month.replace(month=month.month+1, day=1)

    report = {
        'report_month': month.strftime('%B %Y'),
        'generated_at': datetime.now().isoformat(),
        'summary': generate_status_summary(df),
        'new_proposals': [],
        'new_approvals': [],
        'new_permits': [],
        'completions': [],
        'metrics': {}
    }

    # Calculate key metrics
    report['metrics'] = {
        'total_projects': len(df),
        'total_proposed_units': int(df['net_units'].fillna(0).sum()) if 'net_units' in df.columns else 0,
        'avg_project_size': round(df['net_units'].mean(), 1) if 'net_units' in df.columns else 0,
        'projects_in_review': len(df[df['status'].str.contains('Review', case=False, na=False)]) if 'status' in df.columns else 0,
        'projects_approved': len(df[df['status'].str.contains('Approved|Final Action', case=False, na=False)]) if 'status' in df.columns else 0,
    }

    return report


def export_to_html(
    report: Dict[str, Any],
    output_path: str,
    template: str = 'default'
) -> str:
    """
    Export report to HTML format.

    Parameters
    ----------
    report : dict
        Report data from generate_monthly_report
    output_path : str
        Output file path
    template : str
        HTML template to use

    Returns
    -------
    str : Path to generated file
    """
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Berkeley Housing Report - {report.get('report_month', 'Monthly')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .summary-box {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 15px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .metric-value {{ font-size: 28px; font-weight: bold; color: #3498db; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #3498db; color: white; }}
        tr:nth-child(even) {{ background: #f8f9fa; }}
        .footer {{ margin-top: 40px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>Berkeley Housing Development Report</h1>
    <p><strong>Report Period:</strong> {report.get('report_month', 'Monthly')}</p>
    <p><strong>Generated:</strong> {report.get('generated_at', '')}</p>

    <div class="summary-box">
        <h2>Summary</h2>
        <div class="metric">
            <div class="metric-value">{report['metrics'].get('total_projects', 0):,}</div>
            <div class="metric-label">Total Projects</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report['metrics'].get('total_proposed_units', 0):,}</div>
            <div class="metric-label">Proposed Units</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report['metrics'].get('projects_in_review', 0):,}</div>
            <div class="metric-label">In Review</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report['metrics'].get('projects_approved', 0):,}</div>
            <div class="metric-label">Approved</div>
        </div>
    </div>

    <h2>Projects by Status</h2>
    <table>
        <tr><th>Status</th><th>Count</th></tr>
"""

    # Add status rows
    for status, count in report['summary'].get('by_status', {}).items():
        html_content += f"        <tr><td>{status}</td><td>{count}</td></tr>\n"

    html_content += """    </table>

    <div class="footer">
        <p>Data source: City of Berkeley Open Data Portal</p>
        <p>Generated by Berkeley Housing Pipeline</p>
    </div>
</body>
</html>"""

    output_path = Path(output_path)
    output_path.write_text(html_content)

    print(f"HTML report saved: {output_path}")
    return str(output_path)


def export_to_json(
    data: Any,
    output_path: str,
    indent: int = 2
) -> str:
    """
    Export data to JSON format for dashboard consumption.

    Parameters
    ----------
    data : any
        Data to export (dict, DataFrame, etc.)
    output_path : str
        Output file path
    indent : int
        JSON indentation

    Returns
    -------
    str : Path to generated file
    """
    output_path = Path(output_path)

    if isinstance(data, pd.DataFrame):
        # Convert DataFrame to list of dicts
        json_data = data.to_dict(orient='records')
    else:
        json_data = data

    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=indent, default=str)

    print(f"JSON exported: {output_path}")
    return str(output_path)


def export_map_data(
    df: pd.DataFrame,
    output_path: str,
    lat_col: str = 'latitude',
    lon_col: str = 'longitude'
) -> str:
    """
    Export project data in format suitable for web maps.

    Parameters
    ----------
    df : pd.DataFrame
        Projects with coordinates
    output_path : str
        Output file path
    lat_col, lon_col : str
        Coordinate column names

    Returns
    -------
    str : Path to generated file
    """
    # Filter to records with coordinates
    map_df = df.dropna(subset=[lat_col, lon_col]).copy()

    # Create GeoJSON-like structure
    features = []

    for _, row in map_df.iterrows():
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(row[lon_col]), float(row[lat_col])]
            },
            'properties': {
                'address': row.get('address_display', row.get('address', '')),
                'units': int(row.get('net_units', 0)) if pd.notna(row.get('net_units')) else 0,
                'status': row.get('status', ''),
                'year': int(row.get('year', 0)) if pd.notna(row.get('year')) else None,
                'description': row.get('description', '')[:200] if pd.notna(row.get('description')) else ''
            }
        }
        features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'generated': datetime.now().isoformat(),
            'count': len(features)
        }
    }

    return export_to_json(geojson, output_path)


def generate_dashboard_data(
    df: pd.DataFrame,
    output_dir: str
) -> Dict[str, str]:
    """
    Generate all data files needed for a dashboard.

    Parameters
    ----------
    df : pd.DataFrame
        Projects dataframe
    output_dir : str
        Output directory

    Returns
    -------
    dict : Paths to generated files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {}

    # Summary statistics
    summary = generate_status_summary(df)
    files['summary'] = export_to_json(
        summary,
        output_dir / 'summary.json'
    )

    # Map data (GeoJSON)
    if 'latitude' in df.columns and 'longitude' in df.columns:
        files['map'] = export_map_data(
            df,
            output_dir / 'projects_map.json'
        )

    # Time series data by year
    if 'year' in df.columns:
        yearly = df.groupby('year').agg({
            'net_units': 'sum' if 'net_units' in df.columns else 'count',
            'address_display': 'count'
        }).reset_index()
        yearly.columns = ['year', 'units', 'projects']
        files['timeseries'] = export_to_json(
            yearly.to_dict(orient='records'),
            output_dir / 'timeseries.json'
        )

    # Projects list
    files['projects'] = export_to_json(
        df.to_dict(orient='records'),
        output_dir / 'projects.json'
    )

    print(f"\nDashboard data generated in: {output_dir}")
    return files
