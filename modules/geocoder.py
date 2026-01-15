"""
Geocoding module for Berkeley housing project addresses
Uses Alameda County address lookup table with proper normalization
"""

import pandas as pd
import os
import re


# Berkeley bounds constant
BERKELEY_BOUNDS = {
    'lat_min': 37.84,
    'lat_max': 37.91,
    'lon_min': -122.32,
    'lon_max': -122.23
}


def normalize_street_name(name):
    """
    Convert between word and number forms of street names
    FIFTH ↔ 5th, SIXTH ↔ 6th, etc.
    """
    # Uppercase for consistency
    name_upper = str(name).upper().strip()
    
    # Word to number conversions
    word_to_num = {
        'FIRST': '1ST', 'SECOND': '2ND', 'THIRD': '3RD',
        'FOURTH': '4TH', 'FIFTH': '5TH', 'SIXTH': '6TH',
        'SEVENTH': '7TH', 'EIGHTH': '8TH', 'NINTH': '9TH',
        'TENTH': '10TH', 'ELEVENTH': '11TH', 'TWELFTH': '12TH'
    }
    
    # If it's a word form, convert to number
    if name_upper in word_to_num:
        return word_to_num[name_upper]
    
    # If it's already a number form (5TH, 6TH), keep it
    return name_upper


def normalize_address_for_lookup(address):
    """
    Normalize address to match Alameda County format:
    - Parse street number, name, type
    - Convert FIFTH → 5th
    - Convert to format: "1914 5th St" (lowercase 'th', title case type)
    """
    # Parse address
    parts = str(address).strip().split()
    
    if len(parts) < 3:
        return None
    
    street_num = parts[0]
    street_name = parts[1]
    street_type = parts[2]
    
    # Normalize street name (FIFTH → 5TH)
    normalized_name = normalize_street_name(street_name)
    
    # Convert to Alameda format: "1914 5th St"
    # Alameda has: lowercase ordinal (5th), title case type (St)
    
    # Handle ordinals: 5TH → 5th, 1ST → 1st
    pattern = r'^\d+(ST|ND|RD|TH)$'
    if re.match(pattern, normalized_name):
        # Extract number and suffix
        match_obj = re.match(r'^(\d+)(ST|ND|RD|TH)$', normalized_name)
        if match_obj:
            num = match_obj.group(1)
            suffix = match_obj.group(2).lower()  # Convert TH → th
            normalized_name = f"{num}{suffix}"
    
    # Normalize street type (AV → Av, ST → St, etc.)
    # Alameda uses title case
    type_map = {
        'ST': 'St', 'AV': 'Av', 'AVE': 'Av', 'AVENUE': 'Av',
        'WY': 'Wy', 'WAY': 'Wy',
        'BL': 'Bl', 'BLVD': 'Bl', 'BOULEVARD': 'Bl',
        'RD': 'Rd', 'ROAD': 'Rd',
        'DR': 'Dr', 'DRIVE': 'Dr',
        'PL': 'Pl', 'PLACE': 'Pl',
        'CT': 'Ct', 'COURT': 'Ct',
        'LN': 'Ln', 'LANE': 'Ln',
        'SQ': 'Sq', 'SQUARE': 'Sq',
        'TE': 'Te', 'TER': 'Te', 'TERRACE': 'Te',
        'CI': 'Ci', 'CIR': 'Ci', 'CIRCLE': 'Ci',
    }
    
    street_type_upper = street_type.upper()
    normalized_type = type_map.get(street_type_upper, street_type.title())
    
    # Build normalized address
    normalized = f"{street_num} {normalized_name} {normalized_type}"
    
    return normalized


def load_lookup_table(lookup_file):
    """Load the address lookup table"""
    if not os.path.exists(lookup_file):
        raise FileNotFoundError(f"Lookup table not found: {lookup_file}")
    
    df = pd.read_csv(lookup_file)
    return df


def geocode_from_lookup(address, lookup_file='/Users/johngage/berkeley-data/alameda_lookup_complete.csv'):
    """
    Geocode an address using the lookup table
    Handles: FIFTH → 5th, case conversion, float street numbers
    """
    # Normalize the input address to Alameda format
    normalized = normalize_address_for_lookup(address)
    
    if not normalized:
        return None
    
    # Load lookup table
    df_lookup = pd.read_csv(lookup_file)
    
    # Search for exact match in original_address
    match = df_lookup[df_lookup['original_address'] == normalized]
    
    if len(match) > 0:
        return {
            'latitude': float(match.iloc[0]['latitude']),
            'longitude': float(match.iloc[0]['longitude']),
            'apn': str(match.iloc[0]['APN']) if pd.notna(match.iloc[0]['APN']) else None,
            'original_address': match.iloc[0]['original_address'],
            'normalized_input': normalized
        }
    
    return None


def geocode_dataframe(df, address_column='address_display', 
                     lookup_file='/Users/johngage/berkeley-data/alameda_lookup_complete.csv'):
    """Geocode all addresses in a dataframe"""
    if 'latitude' not in df.columns:
        df['latitude'] = None
    if 'longitude' not in df.columns:
        df['longitude'] = None
    
    geocoded_count = 0
    
    for idx, row in df.iterrows():
        if pd.notna(row.get('latitude')):
            continue
        
        address = row[address_column]
        result = geocode_from_lookup(address, lookup_file)
        
        if result:
            df.at[idx, 'latitude'] = result['latitude']
            df.at[idx, 'longitude'] = result['longitude']
            if 'APN' in df.columns:
                df.at[idx, 'APN'] = result['apn']
            geocoded_count += 1
    
    return df, geocoded_count


def validate_coordinates(latitude, longitude, city='Berkeley'):
    """Validate coordinates are within bounds"""
    if city == 'Berkeley':
        return (BERKELEY_BOUNDS['lat_min'] <= latitude <= BERKELEY_BOUNDS['lat_max'] and
                BERKELEY_BOUNDS['lon_min'] <= longitude <= BERKELEY_BOUNDS['lon_max'])
    return False


def add_manual_geocode(address, latitude, longitude, apn=None,
                       lookup_file='/Users/johngage/berkeley-data/alameda_lookup_complete.csv'):
    """Add a manually geocoded address to the lookup table"""
    if not validate_coordinates(latitude, longitude):
        print(f"WARNING: Coordinates outside Berkeley bounds")
        return False
    
    df_lookup = pd.read_csv(lookup_file)
    
    # Normalize address before adding
    normalized = normalize_address_for_lookup(address)
    
    new_entry = pd.DataFrame([{
        'original_address': normalized if normalized else address,
        'latitude': float(latitude),
        'longitude': float(longitude),
        'APN': str(apn) if apn else ''
    }])
    
    df_lookup = pd.concat([df_lookup, new_entry], ignore_index=True)
    df_lookup.to_csv(lookup_file, index=False)
    
    print(f"Added {address} to lookup table")
    return True


def get_unmatched_addresses(df, address_column='address_display'):
    """Get list of addresses without coordinates"""
    if 'latitude' not in df.columns:
        return df[address_column].tolist()
    
    unmatched = df[df['latitude'].isna()]
    return unmatched[address_column].tolist()


# Aliases for notebook compatibility
def geocode_address(address, lookup_file='/Users/johngage/berkeley-data/alameda_lookup_complete.csv'):
    return geocode_from_lookup(address, lookup_file)


def geocode_batch(df, address_column='address_display', 
                 lookup_file='/Users/johngage/berkeley-data/alameda_lookup_complete.csv'):
    return geocode_dataframe(df, address_column, lookup_file)


def validate_berkeley_coords(latitude, longitude):
    return validate_coordinates(latitude, longitude, city='Berkeley')


def manual_geocode_entry(address, latitude, longitude, apn=None,
                        lookup_file='/Users/johngage/berkeley-data/alameda_lookup_complete.csv'):
    return add_manual_geocode(address, latitude, longitude, apn, lookup_file)
