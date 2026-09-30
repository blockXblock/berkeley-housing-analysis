# ============================ SEQUESTERED 2026-09-29 ============================
# DO NOT RUN. Original path: scripts/convert_boundaries.py
# WHY: February one-off boundary conversion; nothing live calls it.
raise SystemExit('SEQUESTERED 2026-09-29 -- see header; original path scripts/convert_boundaries.py')
# ================================================================================
import json
import csv

with open('corridor_boundaries.json', 'r') as f:
    data = json.load(f)

features = data.get('features', [])

if features:
    fieldnames = list(features[0]['attributes'].keys())
    
    with open('corridor_boundaries.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for feature in features:
            writer.writerow(feature['attributes'])
    
    print(f"Converted {len(features)} corridor boundaries")
    
    # Show what corridors exist
    for feature in features:
        attrs = feature['attributes']
        print(f"  - {attrs.get('Corridor', 'Unknown')}: {attrs.get('Area_ac', 0)} acres")
else:
    print("No features found")
