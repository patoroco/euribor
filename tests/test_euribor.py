import pytest
from unittest import mock
import os
import json
from datetime import datetime, timezone
import calendar
import sys

# Add parent directory to path to be able to import modules correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modules to test
import src.date_utils as date_utils
from src.euribor import send_request_per_day, send_request_per_month

# Sample test data
SAMPLE_API_RESPONSE = [
    {
        "Data": [
            [1609459200000, 0.123],  # 2021-01-01
            [1609545600000, 0.145],  # 2021-01-02
            [1609632000000, 0.167],  # 2021-01-03
            [1609718400000, 0.189],  # 2021-01-04
        ]
    }
]

MOCK_RESPONSE = mock.Mock()
MOCK_RESPONSE.status_code = 200
MOCK_RESPONSE.json.return_value = SAMPLE_API_RESPONSE


class TestEuriborFunctions:
    """Unit tests for individual functions in euribor.py"""

    def test_date_to_timestamp(self):
        """Test conversion from date string to timestamp in milliseconds"""
        # Test a known date
        timestamp = date_utils.date_to_timestamp("2021-01-01")
        expected = 1609459200000  # 2021-01-01 00:00:00 UTC in milliseconds
        assert timestamp == expected

    def test_milliseconds_to_datetime(self):
        """Test conversion from milliseconds to datetime string"""
        date_str = date_utils.milliseconds_to_datetime(1609459200000)
        assert "2021-01-01" in date_str

    def test_extract_date(self):
        """Test extracting date from datetime string"""
        date = date_utils.extract_date("2021-01-01 12:00:00 +0000")
        assert date == "2021-01-01"

    def test_extract_month(self):
        """Test extracting month from date string"""
        month = date_utils.extract_month("2021-01-15")
        assert month == "2021-01"


@pytest.fixture
def mock_requests_get(monkeypatch):
    """Mock the requests.get function for testing"""
    def mock_get(*args, **kwargs):
        return MOCK_RESPONSE
    
    monkeypatch.setattr("requests.get", mock_get)
    return mock_get


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing file operations"""
    # Create the api directory structure
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "daily").mkdir()
    (tmp_path / "api" / "monthly").mkdir()
    
    # Return the temporary path
    return tmp_path


class TestEuriborDataFetching:
    """Tests for data fetching and API interaction"""

    def test_api_request_structure(self, mock_requests_get):
        """Test the structure of API requests"""
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = MOCK_RESPONSE
            send_request_per_day()
            
            # Verify the mock was called with the correct URL
            args, kwargs = mock_get.call_args
            assert kwargs['url'] == "https://www.euribor-rates.eu/umbraco/api/euriborpageapi/highchartsdata"
            
            # Verify headers and parameters (adjust as needed)
            assert "Referer" in kwargs['headers']
            assert "series[0]" in kwargs['params']


class TestEuriborFileOperations:
    """Tests for file operations"""

    @mock.patch('os.makedirs')
    def test_directory_creation(self, mock_makedirs, mock_requests_get):
        """Test that directories are created if they don't exist"""
        # Test for directory creation in send_request_per_day
        with mock.patch('builtins.open', mock.mock_open()) as mock_file:
            send_request_per_day()
            mock_makedirs.assert_any_call('api', exist_ok=True)
        
        # Test for directory creation in send_request_per_month
        with mock.patch('builtins.open', mock.mock_open()) as mock_file:
            send_request_per_month(2021)
            mock_makedirs.assert_any_call("api/monthly", exist_ok=True)

    def test_file_writing_per_day(self, temp_dir, mock_requests_get):
        """Test file writing in send_request_per_day function"""
        # Change to the temp directory for file operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Mock the file writing
            with mock.patch('builtins.open', mock.mock_open()) as mock_file:
                send_request_per_day()
                
                # Check if the file was opened for writing
                mock_file.assert_called()
                
                # Get all write calls
                write_calls = mock_file().write.call_args_list
                
                # Check if at least one write call was made
                assert len(write_calls) > 0
        finally:
            # Restore original directory
            os.chdir(original_dir)

    def test_file_writing_per_month(self, temp_dir, mock_requests_get):
        """Test file writing in send_request_per_month function"""
        # Change to the temp directory for file operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Mock the file writing
            with mock.patch('builtins.open', mock.mock_open()) as mock_file:
                send_request_per_month(2021)
                
                # Check if the file was opened for writing
                mock_file.assert_called()
                
                # Get all write calls
                write_calls = mock_file().write.call_args_list
                
                # Check if at least one write call was made
                assert len(write_calls) > 0
        finally:
            # Restore original directory
            os.chdir(original_dir)


class TestEuriborIntegration:
    """Integration tests for the entire workflow"""

    def test_full_workflow(self, mock_requests_get):
        """Test that the full workflow executes without errors"""
        # Mock any file operations to avoid actual file changes
        with mock.patch('os.makedirs'):
            with mock.patch('builtins.open', mock.mock_open()):
                # Test if these functions run without errors
                send_request_per_day()
                send_request_per_month(2021)


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 
