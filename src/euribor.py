"""
Main module for the Euribor API.
Fetches and processes Euribor rate data.
"""
from datetime import datetime
import requests
import os
import json
import calendar
import argparse
import sys

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

def process_daily_data(year, month):
    """
    Process daily Euribor rates for a specific year and month.
    
    Args:
        year (int or str): The year to process
        month (int or str): The month to process
        
    Returns:
        dict: Statistics about the processing and daily data organized by year/month
    """
    # Calculate date range
    year_str = str(year)
    month_str = f"{int(month):02d}"
    
    # Calculate date range
    min_date = f"{year_str}-{month_str}-01"
    
    # Calculate next month for end date
    if int(month_str) == 12:
        next_month = 1
        next_year = int(year_str) + 1
    else:
        next_month = int(month_str) + 1
        next_year = int(year_str)

    max_date = f"{next_year}-{next_month:02d}-01"
    
    # Fetch data
    data = fetch_euribor_data(min_date, max_date)
    
    if not data:
        return {"days_processed": 0, "daily_data": {}}
    
    days_processed = 0
    # Track daily data for this month to generate monthly JSON files
    daily_data = {}
        
    for series in data:
        for point in series['Data']:
            timestamp, value = point
            date_str = milliseconds_to_datetime(timestamp)

            # Extract date from datetime string (YYYY-MM-DD)
            date = extract_date(date_str)
            
            # Parse date components
            date_year, date_month, day = date.split('-')
            
            # Only include data for the requested year and month
            if date_year == year_str and date_month == month_str:
                daily_data[day] = value
                days_processed += 1
    
    return {"days_processed": days_processed, "daily_data": daily_data}

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
        update_yearly_json(year, month, average)
    
    return {"months_processed": months_processed, "monthly_averages": monthly_average_values}

def update_yearly_json(year, month, value):
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
    result = process_daily_data(year, month)
    
    # Generate the monthly JSON file if we have daily data
    if result["days_processed"] > 0:
        generate_monthly_json(str(year), f"{month:02d}", result["daily_data"])
    
    return result

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

def generate_all_yearly_json(years=None):
    """
    Generate JSON files with monthly averages for specified years
    by ensuring they are properly formatted and sorted.
    
    Args:
        years (list, optional): List of years to process. If None, process all years from 1999 to current.
    """
    current_year = datetime.now().year
    
    # If years not specified, default to historical range
    if years is None:
        years = list(range(1999, current_year + 1))
    
    # Create sorted JSON files for each year
    for year in years:
        create_yearly_json(str(year))
    
    if years:
        print(f"Ensured all yearly JSON files are properly formatted for {len(years)} years")
    else:
        print("No yearly JSON files to process")

def generate_all_monthly_json(months_to_process=None):
    """
    Generate JSON files with daily data for specified years and months by fetching and processing data.
    
    Args:
        months_to_process (dict, optional): Dictionary mapping year -> list of months to process.
                                           If None, defaults to current year/month.
    """
    if months_to_process is None:
        today = datetime.now()
        months_to_process = {today.year: [today.month]}
    
    # Track statistics for reporting
    total_months = 0
    total_days = 0
    
    for year, months in months_to_process.items():
        for month in months:
            result = send_request_per_day(year, month)
            if result["days_processed"] > 0:
                total_months += 1
                total_days += result["days_processed"]
    
    # Report statistics if any data was found
    if total_months > 0:
        print(f"Monthly JSON files processed for {len(months_to_process)} years (from {min(months_to_process.keys())} to {max(months_to_process.keys())}).")
        print(f"Processed {total_months} months with {total_days} days of data.")
    else:
        print("No daily data found to process.")

def parse_args():
    parser = argparse.ArgumentParser(description='Process Euribor data')
    parser.add_argument('--year', type=int, help='Year to process (defaults to current year and previous year if currently in January)')
    parser.add_argument('--month', type=int, help='Month to process (defaults to current month and previous month if in first week)')
    parser.add_argument('--all', action='store_true', help='Process all years from 1999 to current')
    args = parser.parse_args()
    
    # Get current year and month
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    current_day = today.day  # Actual current day
    
    # Determine which years and months to process
    months_to_process = {}
    
    if args.all:
        # Process from 1999 to current year
        for year in range(1999, current_year + 1):
            months_to_process[year] = list(range(1, 13)) if year != current_year else list(range(1, current_month + 1))
    elif args.year is not None:
        # Process a specific year
        year = args.year
        if args.month is not None:
            # Process a specific month in a specific year
            months_to_process[year] = [args.month]
        else:
            # Process all months in the specific year (up to current month if it's the current year)
            months_to_process[year] = list(range(1, 13)) if year != current_year else list(range(1, current_month + 1))
    else:
        # Default: process current month
        if args.month is not None:
            # Process a specific month in the current year
            months_to_process[current_year] = [args.month]
        else:
            # Process current month and possibly previous month
            if current_day <= 7:  # First week of the month
                if current_month == 1:
                    # If January, also process December of previous year
                    months_to_process[current_year] = [current_month]
                    months_to_process[current_year - 1] = [12]
                else:
                    # Process current and previous month of the same year
                    months_to_process[current_year] = [current_month, current_month - 1]
            else:
                # Just process current month
                months_to_process[current_year] = [current_month]
    
    return args, months_to_process

def create_yearly_json(year):
    """
    Create or update yearly JSON file with all monthly data for the specified year.
    
    Args:
        year (int or str): The year to process
    """
    # Convert year to string if it's an integer
    year_str = str(year)
    
    # Create directory if not exists
    api_dir = os.path.join("api", year_str)
    os.makedirs(api_dir, exist_ok=True)
    
    # JSON file path
    json_file = os.path.join(api_dir, "index.json")
    
    # Read existing file if it exists
    data = {}
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    
    # Sort the data by month number
    ordered_data = {}
    months = sorted(data.keys(), key=int)
    for m in months:
        ordered_data[m] = data[m]
    
    # Write ordered data to JSON file
    with open(json_file, 'w') as f:
        json.dump(ordered_data, f, indent=2)
    
    return data

# Only run this if the script is executed directly
if __name__ == "__main__":
    args, months_to_process = parse_args()
    
    # Process data for each selected year and month
    years = sorted(months_to_process.keys())
    for year in years:
        specific_months = sorted(months_to_process[year])
        
        # Process monthly data for the year
        print(f"Updating monthly data for {year}...")
        monthly_result = send_request_per_month(year)
        
        # Process daily data for the specific months of this year
        for month in specific_months:
            print(f"Processing {year}/{month:02d}...")
            daily_result = send_request_per_day(year, month)
        
        # Create yearly JSON file (with monthly averages)
        create_yearly_json(year)
                
    # Print summary
    total_years = len(years)
    total_months = sum(len(months) for months in months_to_process.values())
    print(f"JSON files processed for {total_years} years (from {min(years) if years else 'none'} to {max(years) if years else 'none'}).")
    print(f"Processed {total_months} months of data.")
    
    # Generate all required JSON files
    generate_all_yearly_json(years)
    generate_all_monthly_json(months_to_process)
    
    print(f"Process completed.")
