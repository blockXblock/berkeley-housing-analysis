"""
Berkeley Housing Data Pipeline Modules

Reusable functions for data loading, address normalization,
geocoding, timeline calculations, and report generation.
"""

from .data_loader import (
    load_permits_from_api,
    load_csv,
    load_database,
    get_socrata_client,
    DATASETS
)

from .address_normalizer import (
    normalize_address,
    get_street_name_variations,
    get_street_type_variations,
    parse_address,
    standardize_address
)

from .geocoder import (
    geocode_address,
    geocode_batch,
    load_lookup_table,
    validate_berkeley_coords
)

from .timeline_calculator import (
    calculate_days_between,
    get_project_timeline,
    classify_project_status,
    calculate_progress_percent
)

from .report_generator import (
    generate_monthly_report,
    generate_status_summary,
    export_to_html,
    export_to_json
)

__version__ = "1.0.0"
__author__ = "Berkeley Housing Pipeline"
