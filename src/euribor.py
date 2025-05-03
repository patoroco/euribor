"""
Main module for the Euribor API.
Fetches and processes Euribor rate data.
"""
from datetime import datetime
import requests
import os
from pprint import pprint

from src.date_utils import (
    date_to_timestamp,
    milliseconds_to_datetime,
    extract_date,
    extract_month
)

def send_request_per_day(year=2025, month=4):
    """
    Fetch daily Euribor rates and save them to files.
    Each rate is saved in a file named by the date (YYYY-MM-DD).
    
    Args:
        year (int): The year to fetch data for
        month (int): The month to fetch data for
    """
    # get euribor rate
    # GET https://www.euribor-rates.eu/umbraco/api/euriborpageapi/highchartsdata

    min_date = f"{year}-{month:02d}-01"
    min_date_timestamp = date_to_timestamp(min_date)

    # Calculate next month
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    max_date = f"{next_year}-{next_month:02d}-01"
    max_date_timestamp = date_to_timestamp(max_date)
    
    try:
        response = requests.get(
            url="https://www.euribor-rates.eu/umbraco/api/euriborpageapi/highchartsdata",
            params={
                "series[0]": "4", # series[0] = 4 -> 12-months
                "minticks": min_date_timestamp,
                "maxticks": max_date_timestamp,
            },
            headers={
                "Referer": "https://www.euribor-rates.eu/en/current-euribor-rates/4/euribor-rate-12-months/",
                "Sec-Fetch-Mode": "cors",
            },
        )
                
        if response.status_code == 200:
            data = response.json()
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
                    
                    # Write value to file
                    with open(file_path, 'w') as f:
                        f.write(str(value))
                        print(f'File {file_path} created')

    except requests.exceptions.RequestException:
        print('HTTP Request failed')
def send_request_per_month(year=2025):
    """
    Fetch Euribor rates for a specific year and calculate monthly averages.
    Each monthly average is saved in a file named by year and month (YYYY-MM).
    
    Args:
        year (int): The year to fetch data for
    """
    # get euribor rate
    # GET https://www.euribor-rates.eu/umbraco/api/euriborpageapi/highchartsdata

    min_date = f"{year}-01-01"
    min_date_timestamp = date_to_timestamp(min_date)

    max_date = f"{year+1}-01-01"
    max_date_timestamp = date_to_timestamp(max_date)
    
    try:
        response = requests.get(
            url="https://www.euribor-rates.eu/umbraco/api/euriborpageapi/highchartsdata",
            params={
                "series[0]": "4", # series[0] = 4 -> 12-months
                "minticks": min_date_timestamp,
                "maxticks": max_date_timestamp,
            },
            headers={
                "Referer": "https://www.euribor-rates.eu/en/current-euribor-rates/4/euribor-rate-12-months/",
                "Sec-Fetch-Mode": "cors",
            },
        )
                
        if response.status_code == 200:
            data = response.json()
            # Initialize dictionary to store monthly averages
            monthly_averages = {}

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
                    
            # Print monthly averages
            pprint(monthly_averages)
            
            # Process and write monthly averages
            for month_key, average in monthly_averages.items():
                # Extract year and month from the key (YYYY-MM format)
                year, month = month_key.split('-')
                
                # Create directory structure
                directory = os.path.join("api", "monthly", year)
                os.makedirs(directory, exist_ok=True)
                
                # Create file path
                file_path = os.path.join(directory, month)
                
                # Write average to file
                with open(file_path, 'w') as f:
                    f.write(str(average))
                    print(f'File {file_path} created')

    except requests.exceptions.RequestException:
        print('HTTP Request failed')

# Only run this if the script is executed directly
if __name__ == "__main__":
    for year in range(2024, 2026):
        send_request_per_month(year) 
        
    current_year = datetime.now().year
    current_month = datetime.now().month

    for month in range(1, current_month):
        send_request_per_day(current_year, month)
