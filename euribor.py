import requests
from datetime import datetime, timezone
import os
from pprint import pprint
import calendar

def date_to_timestamp(date_str):
    """
    Convert a date string in format YYYY-MM-DD to UTC timestamp in milliseconds
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    # Force the date to be interpreted as UTC
    date_obj = date_obj.replace(tzinfo=timezone.utc)
    return calendar.timegm(date_obj.utctimetuple()) * 1000

def milliseconds_to_datetime(milliseconds):
    """
    Convert milliseconds to datetime string in format YYYY-mm-dd HH:mm:ss +timezone
    
    Args:
        milliseconds (int): Timestamp in milliseconds
        
    Returns:
        str: Formatted datetime string with timezone
    """
    # Convert milliseconds to seconds
    seconds = milliseconds / 1000
    
    # Create datetime object
    dt = datetime.fromtimestamp(seconds)
    
    # Format the datetime with timezone
    return dt.strftime("%Y-%m-%d %H:%M:%S %z")



def send_request_per_day():
    # get euribor rate
    # GET https://www.euribor-rates.eu/umbraco/api/euriborpageapi/highchartsdata

    min_date = "2024-01-01"
    min_date_timestamp = date_to_timestamp(min_date)

    max_date = "2025-01-01"
    max_date_timestamp = date_to_timestamp(max_date)
    

    try:
        response = requests.get(
            url="https://www.euribor-rates.eu/umbraco/api/euriborpageapi/highchartsdata",
            params={
                "series[0]": "4",
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
                    date = date_str.split()[0]
                    
                    # Create directory if it doesn't exist
                    os.makedirs('api', exist_ok=True)
                    
                    # Create file path
                    file_path = os.path.join('api', date)
                    
                    # Write value to file
                    with open(file_path, 'w') as f:
                        f.write(str(value))
                        print(f'File {file_path} created')

    except requests.exceptions.RequestException:
        print('HTTP Request failed')

def send_request_per_month(year=2025):
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
                "series[0]": "4",
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
                    date = date_str.split()[0]
                    
                    # Extract year and month from date
                    year_month = date[:7]  # Gets YYYY-MM format
                    
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
            
            # Create directory if it doesn't exist
            os.makedirs("api/monthly", exist_ok=True)
            
            # Write each monthly average to its corresponding file
            for month, average in monthly_averages.items():
                file_path = f"api/monthly/{month}"
                with open(file_path, 'w') as f:
                    f.write(str(average))

    except requests.exceptions.RequestException:
        print('HTTP Request failed')

for year in range(2012, 2026):
    send_request_per_month(year)
