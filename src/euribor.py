"""
Main module for the Euribor API.
Fetches and processes Euribor rate data.
"""
from datetime import datetime
import requests
import os
import json
import calendar

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
    Process daily Euribor rates and prepare data for JSON files.
    
    Args:
        data (list): JSON data from the API
        
    Returns:
        dict: Statistics about the processing and daily data organized by year/month
    """
    if not data:
        return {"days_processed": 0, "daily_data": {}}
    
    days_processed = 0
    # Track daily data for each month to generate monthly JSON files
    monthly_daily_data = {}
        
    for series in data:
        for point in series['Data']:
            timestamp, value = point
            date_str = milliseconds_to_datetime(timestamp)

            # Extract date from datetime string (YYYY-MM-DD)
            date = extract_date(date_str)
            
            # Parse date components
            year, month, day = date.split('-')
            
            # Add data to monthly_daily_data for JSON files
            if year not in monthly_daily_data:
                monthly_daily_data[year] = {}
            if month not in monthly_daily_data[year]:
                monthly_daily_data[year][month] = {}
            
            monthly_daily_data[year][month][day] = value
            days_processed += 1
    
    # Generate JSON files for each month
    for year in monthly_daily_data:
        for month in monthly_daily_data[year]:
            daily_data = monthly_daily_data[year][month]
            if daily_data:  # Only process if there's data
                generate_monthly_json(year, month, daily_data)
    
    return {"days_processed": days_processed, "daily_data": monthly_daily_data}

def process_monthly_data(data):
    """
    Process and calculate monthly average Euribor rates.
    
    Args:
        data (list): JSON data from the API
        
    Returns:
        dict: Statistics about the processing and monthly averages
    """
    if not data:
        return {"months_processed": 0, "monthly_averages": {}}
        
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
    monthly_average_values = {}
    for month_key, values in monthly_averages.items():
        average = sum(values) / len(values)
        average = round(average, 3)
        monthly_average_values[month_key] = average
        months_processed += 1
    
    # Process monthly averages for JSON files
    for month_key, average in monthly_average_values.items():
        # Extract year and month from the key (YYYY-MM format)
        year, month = month_key.split('-')
        
        # Update or create the year's JSON file
        generate_yearly_json(year, month, average)
    
    return {"months_processed": months_processed, "monthly_averages": monthly_average_values}

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
    
    # Sort the data by month number before writing to file
    # Create a new ordered dictionary
    ordered_data = {}
    
    # Get all months and sort them numerically
    months = sorted(data.keys(), key=int)
    
    # Add each month to the ordered dictionary
    for m in months:
        ordered_data[m] = data[m]
    
    # Write ordered data to JSON file
    with open(json_file, 'w') as f:
        json.dump(ordered_data, f, indent=2)
    
    # Only print message if the data was actually updated or added
    if is_new_data:
        print(f'Added new data for {year}-{month} to {json_file}')
    elif should_update_date:
        print(f'Updated value for {year}-{month} in {json_file}')

def generate_monthly_json(year: str, month: str, daily_data: dict) -> None:
    """
    Generate or update a JSON file with all daily data for a specific month.
    The JSON structure contains daily rates with value and metadata.
    Days without data (weekends, holidays) are included with a null value.
    """
    # Create directory if not exists
    os.makedirs(os.path.join("api", year, month), exist_ok=True)
    
    # Define the output file
    output_file = os.path.join("api", year, month, "index.json")
    
    # Prepare new data
    current_data = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, "r") as f:
                current_data = json.load(f)
        except json.JSONDecodeError:
            current_data = {}
    
    updated = False
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    # Determine the number of days in this month
    year_int = int(year)
    month_int = int(month)
    _, num_days = calendar.monthrange(year_int, month_int)
    
    # Process all days in the month
    for day_int in range(1, num_days + 1):
        day = f"{day_int:02d}"  # Format day as "01", "02", etc.
        
        # If we have data for this day, use it
        if day in daily_data:
            value = daily_data[day]
            value_str = str(value)
            
            # Only update if the value is different or the day doesn't exist yet
            if day not in current_data or current_data[day]["value"] != value_str:
                updated = True
                current_data[day] = {
                    "value": value_str,
                    "_meta": {
                        "full_date": f"{year}-{month}-{day}",
                        "last_modified": now_str
                    }
                }
        else:
            # For days without data, add them with null value if they don't exist
            # or if they exist but have a non-null value
            if day not in current_data or current_data[day]["value"] is not None:
                updated = True
                current_data[day] = {
                    "value": None,
                    "_meta": {
                        "full_date": f"{year}-{month}-{day}",
                        "last_modified": now_str
                    }
                }
    
    # Write the updated data if needed
    if updated:
        # Sort the days numerically
        ordered_data = {k: current_data[k] for k in sorted(current_data.keys(), key=int)}
        
        with open(output_file, "w") as f:
            json.dump(ordered_data, f, indent=2)
            
        # Print a message only if we've actually updated something
        print(f"Updated daily JSON data for {year}/{month}")

def send_request_per_day(year=2025, month=4):
    """
    Fetch daily Euribor rates and generate JSON files.
    
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
    by fetching and processing data directly.
    """
    current_year = datetime.now().year
    
    # Generate yearly JSON files for the past years that we want to track
    start_year = 1999  # Start from 1999 or any other year you want
    
    # Track statistics for reporting
    years_processed = 0
    months_processed = 0
    earliest_year = None
    latest_year = None
    
    for year in range(start_year, current_year + 1):
        result = send_request_per_month(year)
        
        if result["months_processed"] > 0:
            years_processed += 1
            months_processed += result["months_processed"]
            
            # Track earliest and latest years
            if earliest_year is None or year < earliest_year:
                earliest_year = year
            if latest_year is None or year > latest_year:
                latest_year = year
    
    # Report statistics if any work was done
    if years_processed > 0:
        year_range = f"from {earliest_year} to {latest_year}" if earliest_year and latest_year else ""
        print(f"JSON files processed for {years_processed} years ({year_range}).")
        print(f"Processed {months_processed} months of data.")
    else:
        print("No data found to process.")

def generate_all_monthly_json():
    """
    Generate JSON files with daily data for all months by fetching and processing data.
    """
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Generate monthly JSON files for the past years that we want to track
    start_year = 1999  # Start from 1999 or any other year you want
    
    # Track statistics for reporting
    years_processed = 0
    months_processed = 0
    days_processed = 0
    earliest_year = None
    latest_year = None
    
    for year in range(start_year, current_year + 1):
        year_has_data = False
        
        # Determine how many months to process for this year
        max_month = 12
        if year == current_year:
            max_month = current_month
        
        for month in range(1, max_month + 1):
            result = send_request_per_day(year, month)
            
            if result["days_processed"] > 0:
                months_processed += 1
                days_processed += result["days_processed"]
                year_has_data = True
        
        if year_has_data:
            years_processed += 1
            
            # Track earliest and latest years
            if earliest_year is None or year < earliest_year:
                earliest_year = year
            if latest_year is None or year > latest_year:
                latest_year = year
    
    # Report statistics if any work was done
    if years_processed > 0:
        year_range = f"from {earliest_year} to {latest_year}" if earliest_year and latest_year else ""
        print(f"Monthly JSON files processed for {years_processed} years ({year_range}).")
        print(f"Processed {months_processed} months with {days_processed} days of data.")
    else:
        print("No data found to process.")

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
    
    # Generate JSON files for all months
    generate_all_monthly_json()
    
    print(f"Process completed.")
