#!/usr/bin/env python3
"""
Test script to verify Oracle configuration and quarter selection logic.
Run this with: python test_oracle.py
"""

import json
import os
from datetime import datetime

def test_oracle_without_dependencies():
    """Test Oracle configuration without importing config_manager (for GCP environment)."""
    print("Testing Oracle Configuration (Standalone)...")
    print("=" * 60)
    
    # Load config directly
    config_file = 'config/company_config.json'
    if not os.path.exists(config_file):
        print(f"ERROR: Config file {config_file} not found!")
        return False
    
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    # Get Oracle data
    oracle = config_data.get('companies', {}).get('orcl')
    if not oracle:
        print("ERROR: Oracle not found in configuration!")
        return False
    
    print(f"Company: {oracle['name']} ({oracle['ticker']})")
    print(f"IR Site: {oracle['ir_site']}")
    print()
    
    # Show all releases
    releases = oracle.get('releases', {})
    print("All Oracle Releases:")
    for year, year_data in releases.items():
        print(f"  {year}:")
        for quarter, quarter_data in year_data.items():
            date = quarter_data.get('date', quarter_data.get('expected_date', 'No date'))
            print(f"    {quarter}: {date}")
            if 'earnings_release' in quarter_data and quarter_data['earnings_release']:
                print(f"      Earnings: {quarter_data['earnings_release'][:60]}...")
            if 'call_transcript' in quarter_data and quarter_data['call_transcript']:
                print(f"      Transcript: {quarter_data['call_transcript'][:60]}...")
    print()
    
    # Simulate get_latest_release logic
    print("Simulating get_latest_release logic:")
    
    # Find the most recent year
    years = sorted(releases.keys(), reverse=True)
    print(f"Available years (sorted newest first): {years}")
    
    if not years:
        print("No years found!")
        return False
    
    latest_year = years[0]
    quarters = releases[latest_year]
    print(f"Using latest year: {latest_year}")
    print(f"Quarters in {latest_year}: {list(quarters.keys())}")
    
    # Find the most recent quarter with actual date
    latest_quarter = None
    latest_date = None
    latest_data = None
    
    print("\nAnalyzing quarters with dates:")
    for quarter, data in quarters.items():
        if "date" in data and data["date"]:
            try:
                # Parse the date to compare chronologically
                quarter_date = datetime.strptime(data["date"], "%B %d, %Y")
                print(f"  {quarter}: {data['date']} -> {quarter_date}")
                
                if latest_date is None or quarter_date > latest_date:
                    latest_date = quarter_date
                    latest_quarter = quarter
                    latest_data = data
                    print(f"    ^ This is now the latest")
                else:
                    print(f"    (older than current latest)")
            except (ValueError, TypeError) as e:
                print(f"  {quarter}: {data['date']} -> ERROR parsing: {e}")
                continue
        else:
            print(f"  {quarter}: No actual date (skipping)")
    
    print()
    print("FINAL RESULT:")
    print(f"  Year: {latest_year}")
    print(f"  Quarter: {latest_quarter}")
    print(f"  Date: {latest_data.get('date', 'No date') if latest_data else 'No data'}")
    
    # Check if this matches expected Q4 2025
    expected_quarter = "Q4"
    expected_year = "FY25"
    
    success = (latest_year == expected_year and latest_quarter == expected_quarter)
    
    print()
    print("=" * 60)
    if success:
        print("✅ SUCCESS: Correctly selected Q4 FY25 as latest release")
        print("The issue is NOT in the quarter selection logic.")
        print("Check where 'Q3 2024' appears in your report - it might be:")
        print("  1. In the document content itself (from Oracle's PDF)")
        print("  2. A caching issue")
        print("  3. Looking at an old report file")
    else:
        print(f"❌ FAILURE: Expected {expected_quarter} {expected_year}, got {latest_quarter} {latest_year}")
        print("There is a bug in the quarter selection logic.")
    
    return success

if __name__ == "__main__":
    test_oracle_without_dependencies() 