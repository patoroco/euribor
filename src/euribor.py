"""
Main module for the Euribor API.
Fetches and processes Euribor rate data.
"""
from datetime import datetime
import requests
import os
import json

from src.date_utils import (
    date_to_timestamp,
    milliseconds_to_datetime,
    extract_date,
    extract_month
)

def fetch_euribor_data(start_date, end_date):
    """
    Fetch Euribor data from the API for a specific date range.
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        
    Returns:
        list: JSON data from the API or None if request failed
    """
    start_timestamp = date_to_timestamp(start_date)
    end_timestamp = date_to_timestamp(end_date)
    
    try:
        response = requests.get(
            url="https://www.euribor-rates.eu/umbraco/api/euriborpageapi/highchartsdata",
            params={
                "series[0]": "4", # series[0] = 4 -> 12-months
                "minticks": start_timestamp,
                "maxticks": end_timestamp,
            },
            headers={
                "Referer": "https://www.euribor-rates.eu/en/current-euribor-rates/4/euribor-rate-12-months/",
                "Sec-Fetch-Mode": "cors",
            },
        )
                
        if response.status_code == 200:
            return response.json()
        else:
            print(f"HTTP request failed with status code: {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f'HTTP Request failed: {e}')
        return None

def process_daily_data(data):
    """
    Process and save daily Euribor rates.
    
    Args:
        data (list): JSON data from the API
        
    Returns:
        dict: Statistics about the processing (files created/updated)
    """
    if not data:
        return {"days_processed": 0}
    
    days_processed = 0
        
    for series in data:
        for point in series['Data']:
            timestamp, value = point
            date_str = milliseconds_to_datetime(timestamp)

            # Extract date from datetime string (YYYY-MM-DD)
            date = extract_date(date_str)
            
            # Parse date components
            year, month, day = date.split('-')
            
            # Create directory structure
            directory = os.path.join('api', 'daily', year, month)
            os.makedirs(directory, exist_ok=True)
            
            # Create file path
            file_path = os.path.join(directory, day)
            
            # Check if the file exists and has the same content
            content_changed = True
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        existing_value = f.read().strip()
                        content_changed = (existing_value != str(value))
                except:
                    pass
            
            # Write value to file
            with open(file_path, 'w') as f:
                f.write(str(value))
                
            if content_changed:
                print(f'{"Created" if not os.path.exists(file_path) else "Updated"} daily rate for {date} ({value})')
                days_processed += 1
    
    return {"days_processed": days_processed}

def process_monthly_data(data):
    """
    Process and save monthly average Euribor rates.
    
    Args:
        data (list): JSON data from the API
        
    Returns:
        dict: Statistics about the processing (months processed)
    """
    if not data:
        return {"months_processed": 0}
        
    # Initialize dictionary to store monthly averages
    monthly_averages = {}
    months_processed = 0

    for series in data:
        for point in series['Data']:
            timestamp, value = point
            date_str = milliseconds_to_datetime(timestamp)

            # Extract date from datetime string (YYYY-MM-DD)
            date = extract_date(date_str)
            
            # Extract year and month from date
            year_month = extract_month(date)
            
            # Initialize list for this month if not exists
            if year_month not in monthly_averages:
                monthly_averages[year_month] = []
            
            # Add value to the month's list
            monthly_averages[year_month].append(value)
            
    # Calculate average for each month
    for month, values in monthly_averages.items():
        average = sum(values) / len(values)
        average = round(average, 3)
        monthly_averages[month] = average
    
    # Process and write monthly averages
    for month_key, average in monthly_averages.items():
        # Extract year and month from the key (YYYY-MM format)
        year, month = month_key.split('-')
        
        # Create directory structure
        directory = os.path.join("api", "monthly", year)
        os.makedirs(directory, exist_ok=True)
        
        # Create file path
        file_path = os.path.join(directory, month)
        
        # Check if content would change
        content_changed = True
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    existing_value = f.read().strip()
                    content_changed = (existing_value != str(average))
            except:
                pass
        
        # Write average to file
        with open(file_path, 'w') as f:
            f.write(str(average))
            
        if content_changed:
            print(f'{"Created" if not os.path.exists(file_path) else "Updated"} monthly average for {month_key} ({average})')
            months_processed += 1
        
        # Update or create the year's JSON file
        generate_yearly_json(year, month, average)
    
    return {"months_processed": months_processed}

def generate_yearly_json(year, month, value):
    """
    Generate or update JSON file with monthly averages for a specific year.
    
    Args:
        year (str): The year
        month (str): The month (01-12)
        value (float): The average Euribor rate for the month
    """
    # Create directory if not exists
    api_dir = os.path.join("api", year)
    os.makedirs(api_dir, exist_ok=True)
    
    # JSON file path
    json_file = os.path.join(api_dir, "index.json")
    
    # Initialize data structure
    data = {}
    
    # Read existing file if it exists
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # If file exists but is not valid JSON, initialize as empty
            data = {}
    
    # Check if we need to update the last_modified date
    # Only update if the month doesn't exist or if the value has changed
    should_update_date = False
    is_new_data = False
    
    if month not in data:
        should_update_date = True
        is_new_data = True
    elif data[month]["value"] != str(value):
        should_update_date = True
    
    # Current datetime in ISO format for last_modified
    current_datetime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    # If entry exists and we don't need to update the date, keep the old last_modified
    last_modified = current_datetime
    if month in data and not should_update_date and "_meta" in data[month] and "last_modified" in data[month]["_meta"]:
        last_modified = data[month]["_meta"]["last_modified"]
    
    # Update data for this month
    data[month] = {
        "value": str(value),
        "_meta": {
            "full_date": f"{year}-{month}",
            "last_modified": last_modified
        }
    }
    
    # Write updated data to JSON file
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Only print message if the data was actually updated or added
    if is_new_data:
        print(f'Added new data for {year}-{month} to {json_file}')
    elif should_update_date:
        print(f'Updated value for {year}-{month} in {json_file}')

def send_request_per_day(year=2025, month=4):
    """
    Fetch daily Euribor rates and save them to files.
    Each rate is saved in a file named by the date (YYYY-MM-DD).
    
    Args:
        year (int): The year to fetch data for
        month (int): The month to fetch data for
        
    Returns:
        dict: Statistics about the processing
    """
    # Calculate date range
    min_date = f"{year}-{month:02d}-01"
    
    # Calculate next month for end date
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    max_date = f"{next_year}-{next_month:02d}-01"
    
    # Fetch and process data
    data = fetch_euribor_data(min_date, max_date)
    return process_daily_data(data)

def send_request_per_month(year=2025):
    """
    Fetch Euribor rates for a specific year and calculate monthly averages.
    Each monthly average is saved in a file named by year and month (YYYY-MM).
    
    Args:
        year (int): The year to fetch data for
        
    Returns:
        dict: Statistics about the processing
    """
    # Calculate date range for the year
    min_date = f"{year}-01-01"
    max_date = f"{year+1}-01-01"
    
    # Fetch and process data
    data = fetch_euribor_data(min_date, max_date)
    return process_monthly_data(data)

def generate_all_yearly_json():
    """
    Generate JSON files with monthly averages for all years
    by reading data from existing files.
    """
    monthly_dir = os.path.join("api", "monthly")
    
    if not os.path.exists(monthly_dir):
        print("No monthly data found. Run send_request_per_month first.")
        return
    
    # List all year directories
    year_dirs = [d for d in os.listdir(monthly_dir) 
                if os.path.isdir(os.path.join(monthly_dir, d))]
    
    # Track statistics for reporting
    years_processed = 0
    months_added = 0
    months_updated = 0
    
    for year in year_dirs:
        year_path = os.path.join(monthly_dir, year)
        
        # List all month files in this year directory
        month_files = [f for f in os.listdir(year_path) 
                      if os.path.isfile(os.path.join(year_path, f))]
        
        if month_files:  # Only count year if it has months
            years_processed += 1
            
        for month in month_files:
            # Read the monthly average
            with open(os.path.join(year_path, month), 'r') as f:
                value = float(f.read().strip())
            
            # Keep track of previous state
            json_file = os.path.join("api", year, "index.json")
            had_month_before = False
            previous_value = None
            
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        if month in data:
                            had_month_before = True
                            previous_value = data[month]["value"]
                except (json.JSONDecodeError, FileNotFoundError):
                    pass
            
            # Generate or update the JSON file
            generate_yearly_json(year, month, value)
            
            # Update statistics based on what changed
            if not had_month_before:
                months_added += 1
            elif previous_value != str(value):
                months_updated += 1
    
    # Report statistics if any work was done
    if years_processed > 0:
        print(f"JSON files processed for {years_processed} years.")
        if months_added > 0:
            print(f"Added {months_added} new month entries.")
        if months_updated > 0:
            print(f"Updated {months_updated} existing month entries.")
    else:
        print("No monthly data found to process.")

# Only run this if the script is executed directly
if __name__ == "__main__":
    current_year = datetime.now().year
    current_month = datetime.now().month

    print(f"Updating Euribor rates for {current_year}/{current_month:02d}...")
    
    # Process monthly data for the current year
    monthly_result = send_request_per_month(current_year)
    
    # Process daily data for the current month
    daily_result = send_request_per_day(current_year, current_month)
    
    # Generate JSON files for all years
    generate_all_yearly_json()
    
    print(f"Process completed.")
