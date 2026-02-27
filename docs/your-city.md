# Use This for Your City

This project was built for Berkeley, but the methodology works for **any California city**—and with some adaptation, any city anywhere.

## Quick Start

### Step 1: Fork or Clone the Repository

```bash
git clone https://github.com/blockXblock/berkeley-housing-analysis.git
cd berkeley-housing-analysis
```

Or click "Use this template" on GitHub to create your own copy.

### Step 2: Create Your City Configuration

Copy the template and customize it:

```bash
cp city_template.yaml city_oakland.yaml  # Replace with your city
```

Edit the file with your city's information:
- Data source URLs
- Geocoding strategy
- RHNA allocation
- Status code mappings

### Step 3: Run the City Profile Builder

Open [A9_city_profile_builder.ipynb](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/01_collection/A9_city_profile_builder.ipynb) and:
1. Update the config file path to your city's file
2. Run the notebook
3. Review your city profile and setup checklist

### Step 4: Work Through the Checklist

The notebook generates a checklist for adapting each series:

**A-Series: Data Collection**
- [ ] Test your city's open data portal
- [ ] Configure geocoding for your county
- [ ] Set up APN matching

**B-Series: Timeline Tracking**
- [ ] Map your permit status codes
- [ ] Configure stalled project thresholds

**C-Series: Analysis**
- [ ] Update RHNA targets
- [ ] Adjust date ranges

**D-Series: Reporting**
- [ ] Verify APR field mappings
- [ ] Test report generation

## What You'll Need to Customize

### Data Sources

| Component | Berkeley | Your City |
|-----------|----------|-----------|
| Open Data Portal | data.cityofberkeley.info | Your city's portal |
| Permit System | Accela | Your permit system |
| Assessor | Alameda County | Your county |
| Geocoding | Alameda address DB | Your county's data |

### Status Code Mapping

Every permit system uses different status codes. In `city_<yourCity>.yaml`:

```yaml
status_mappings:
  in_review:
    - "Under Review"        # Your code
    - "Plan Check"          # Your code
    - "Pending"             # Your code
  approved:
    - "Approved"            # Your code
    - "Ready to Issue"      # Your code
```

### Geographic Bounds

Update the bounds for validation:

```yaml
bounds:
  lat_min: 37.7    # Your city's southern boundary
  lat_max: 37.9    # Your city's northern boundary
  lon_min: -122.3  # Your city's western boundary
  lon_max: -122.1  # Your city's eastern boundary
```

## Common Challenges

### "My city's API is blocked by a firewall"
This happened to us too! See `A1_data_sources_setup.ipynb` for workarounds using manual downloads.

### "Address formats are different"
Modify `modules/address_normalizer.py` to handle your city's conventions.

### "We don't have a county address database"
Options:
- Census TIGER geocoding (free, less accurate)
- Google Maps API (paid, very accurate)
- Mapbox API (paid, accurate)

### "Our permit system is different"
The core methodology still applies—you just need to map your system's data to our schema.

## Contributing Your City

If you adapt this to your city, please consider contributing back:

1. Add your `city_<name>.yaml` to the repo
2. Document any unique challenges you solved
3. Share improvements to the core notebooks

**Pull requests welcome!**

## Resources

- [City Template](https://github.com/blockXblock/berkeley-housing-analysis/blob/main/city_template.yaml)
- [A9 City Profile Builder](https://colab.research.google.com/github/blockXblock/berkeley-housing-analysis/blob/main/01_collection/A9_city_profile_builder.ipynb)
- [Course README](https://github.com/blockXblock/berkeley-housing-analysis/blob/main/README_COURSE.md)

## California Cities We'd Love to See

- Oakland
- San Francisco
- San Jose
- Los Angeles
- Sacramento
- San Diego
- Fresno
- Long Beach

**Help us build a statewide housing transparency network!**
