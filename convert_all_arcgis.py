import json
import csv

def convert_to_csv(json_file, csv_file):
    """Convert ArcGIS FeatureServer JSON to CSV"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        
        if not features:
            print(f"No features in {json_file}")
            return 0
        
        # Get field names
        fieldnames = list(features[0]['attributes'].keys())
        
        # Write CSV
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for feature in features:
                writer.writerow(feature['attributes'])
        
        print(f"✓ {csv_file}: {len(features)} records")
        return len(features)
        
    except FileNotFoundError:
        print(f"✗ {json_file} not found - skipping")
        return 0
    except Exception as e:
        print(f"✗ Error with {json_file}: {e}")
        return 0

# Convert all files
convert_to_csv('rent_control.json', 'rent_control.csv')
convert_to_csv('corridor_ownership.json', 'corridor_ownership.csv')
convert_to_csv('corridor_far.json', 'corridor_far.csv')
