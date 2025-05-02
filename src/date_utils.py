"""
Utilities for date and time conversions used in the Euribor API.
"""
from datetime import datetime, timezone
import calendar

def date_to_timestamp(date_str):
    """
    Convert a date string in format YYYY-MM-DD to UTC timestamp in milliseconds
    
    Args:
        date_str (str): Date string in format YYYY-MM-DD
        
    Returns:
        int: Timestamp in milliseconds
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    # Force the date to be interpreted as UTC
    date_obj = date_obj.replace(tzinfo=timezone.utc)
    return calendar.timegm(date_obj.utctimetuple()) * 1000

def milliseconds_to_datetime(milliseconds):
    """
    Convert milliseconds to datetime string in format YYYY-MM-DD HH:mm:ss +timezone
    
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

def extract_date(datetime_str):
    """
    Extract date part from a datetime string
    
    Args:
        datetime_str (str): Datetime string in format YYYY-MM-DD HH:mm:ss +timezone
        
    Returns:
        str: Date part in format YYYY-MM-DD
    """
    return datetime_str.split()[0]

def extract_month(date_str):
    """
    Extract year and month from a date string
    
    Args:
        date_str (str): Date string in format YYYY-MM-DD
        
    Returns:
        str: Year and month in format YYYY-MM
    """
    return date_str[:7] 
