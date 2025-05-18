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
from src.euribor import (
    send_request_per_day, 
    send_request_per_month, 
    update_yearly_json, 
    generate_monthly_json,
    generate_all_yearly_json,
    generate_all_monthly_json,
    create_yearly_json
)

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
    # Create the api directory structure with nested folders
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "2021").mkdir()
    (tmp_path / "api" / "2021" / "01").mkdir()
    
    # Return the temporary path
    return tmp_path


class TestEuriborDataFetching:
    """Tests for data fetching and API interaction"""

    def test_api_request_structure(self, mock_requests_get):
        """Test the structure of API requests"""
        with mock.patch('requests.get') as mock_get:
            mock_get.return_value = MOCK_RESPONSE
            send_request_per_day(2021, 1)
            
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
        # Test for directory creation in send_request_per_day (creates monthly JSON dirs)
        with mock.patch('builtins.open', mock.mock_open()), \
             mock.patch('json.load', return_value={}), \
             mock.patch('json.dump'):
            send_request_per_day(2021, 1)
            # Check that year/month directory for JSON is created
            mock_makedirs.assert_any_call(os.path.join('api', '2021', '01'), exist_ok=True)
        
        # Test for directory creation for yearly JSON
        with mock.patch('builtins.open', mock.mock_open()), \
             mock.patch('json.load', return_value={}), \
             mock.patch('json.dump'):
            send_request_per_month(2021)
            # Check that year directory is created
            mock_makedirs.assert_any_call(os.path.join('api', '2021'), exist_ok=True)

    def test_process_daily_data(self, mock_requests_get):
        """Test processing daily data from API response"""
        with mock.patch('src.euribor.generate_monthly_json') as mock_generate_json:
            result = send_request_per_day(2021, 1)
            
            # Check the result structure
            assert "days_processed" in result
            assert "daily_data" in result
            assert result["days_processed"] > 0
            
            # Check that the generate_monthly_json function was called
            mock_generate_json.assert_called()

    def test_process_monthly_data(self, mock_requests_get):
        """Test processing monthly data from API response"""
        with mock.patch('src.euribor.update_yearly_json') as mock_generate_json:
            result = send_request_per_month(2021)
            
            # Check the result structure
            assert "months_processed" in result
            assert "monthly_averages" in result
            assert result["months_processed"] > 0
            
            # Check that the update_yearly_json function was called
            mock_generate_json.assert_called()
    
    def test_json_generation(self, temp_dir):
        """Test JSON file generation with metadata"""
        # Change to the temp directory for file operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Create test directories
            os.makedirs(os.path.join('api', '2021'), exist_ok=True)
            
            # Mock datetime.now() properly to return our fixed datetime
            fixed_datetime = datetime(2021, 12, 31, 12, 0, 0)
            datetime_mock = mock.Mock(wraps=datetime)
            datetime_mock.now.return_value = fixed_datetime
            
            # Patch the datetime class in the module being tested
            with mock.patch('src.euribor.datetime', datetime_mock):
                # Test generating a new JSON file
                update_yearly_json('2021', '01', 3.456)
                
                # Verify the JSON file was created with the right content
                json_file = os.path.join('api', '2021', 'index.json')
                assert os.path.exists(json_file)
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    assert '01' in data
                    assert data['01']['value'] == '3.456'
                    assert data['01']['_meta']['full_date'] == '2021-01'
                    assert data['01']['_meta']['last_modified'] == '2021-12-31T12:00:00'
                
                # Test updating the same month with the same value
                # The last_modified date should not change
                update_yearly_json('2021', '01', 3.456)
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    assert data['01']['_meta']['last_modified'] == '2021-12-31T12:00:00'
                
                # Test updating the same month with a different value
                # The last_modified date should change
                datetime_mock.now.return_value = datetime(2022, 1, 1, 12, 0, 0)
                update_yearly_json('2021', '01', 3.789)
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    assert data['01']['value'] == '3.789'
                    assert data['01']['_meta']['last_modified'] == '2022-01-01T12:00:00'
        finally:
            # Restore original directory
            os.chdir(original_dir)
    
    def test_monthly_json_generation(self, temp_dir):
        """Test monthly JSON file generation with daily data"""
        # Change to the temp directory for file operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Create test directories
            os.makedirs(os.path.join('api', '2021', '01'), exist_ok=True)
            
            # Prepare test data
            daily_data = {
                '01': 0.123,  # 2021-01-01
                '02': 0.145,  # 2021-01-02
                '03': 0.167,  # 2021-01-03
                '04': 0.189,  # 2021-01-04
            }
            
            # Mock datetime.now() to return a fixed date after the month being tested
            # (to ensure no days are filtered out as future dates)
            fixed_datetime = datetime(2021, 2, 1, 12, 0, 0)  # February 1st, after the month we're testing
            
            with mock.patch('src.euribor.datetime', mock.Mock(wraps=datetime)) as mock_dt:
                mock_dt.now.return_value = fixed_datetime
                
                # Test generating a new monthly JSON file
                generate_monthly_json('2021', '01', daily_data)
                
                # Verify the JSON file was created with the right content
                json_file = os.path.join('api', '2021', '01', 'index.json')
                assert os.path.exists(json_file)
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    # Check that we have 31 days (January has 31 days)
                    assert len(data) == 31
                    
                    # Check our specific days have the correct values
                    assert '01' in data
                    assert '02' in data
                    assert '03' in data
                    assert '04' in data
                    
                    # Verify data values
                    assert data['01']['value'] == '0.123'
                    assert data['02']['value'] == '0.145'
                    assert data['03']['value'] == '0.167'
                    assert data['04']['value'] == '0.189'
                    
                    # Check that other days have null values
                    assert data['05']['value'] is None
                    assert data['15']['value'] is None
                    assert data['31']['value'] is None
                    
                    # Verify metadata for a specific day
                    assert data['01']['_meta']['full_date'] == '2021-01-01'
                    assert data['01']['_meta']['last_modified'] == '2021-02-01T12:00:00'
                
                # Test future date filtering - set now to be in the middle of the month
                mock_dt.now.return_value = datetime(2021, 1, 2, 12, 0, 0)  # January 2nd, within the month
                
                # Update data with different values
                daily_data['03'] = 0.172  # Changed value
                daily_data['05'] = 0.210  # Future day that should be filtered
                
                generate_monthly_json('2021', '01', daily_data)
                
                # Verify the JSON file was updated correctly
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    # Should only have days up to the current date (01 and 02)
                    assert len(data) == 2
                    assert '01' in data
                    assert '02' in data
                    assert '03' not in data  # Future day
                    assert '04' not in data  # Future day
                    assert '05' not in data  # Future day
                    
                    # Values should be correct
                    assert data['01']['value'] == '0.123'
                    assert data['02']['value'] == '0.145'
        
        finally:
            # Change back to the original directory
            os.chdir(original_dir)

class TestEuriborIntegration:
    """Integration tests for the entire workflow"""

    def test_full_workflow(self, mock_requests_get):
        """Test that the full workflow executes without errors"""
        # Mock any file operations to avoid actual file changes
        with mock.patch('os.makedirs'):
            # Create a mock that can handle both read and write operations
            mock_file = mock.mock_open(read_data='1.234')
            
            # Mock open to handle both writes and reads
            with mock.patch('builtins.open', mock_file):
                # Mock JSON load to return a proper structure
                with mock.patch('json.load', return_value={}):
                    with mock.patch('os.path.exists', return_value=True):
                        with mock.patch('json.dump'):
                            # Test if these functions run without errors
                            send_request_per_day(2021, 1)
                            send_request_per_month(2021)
                            
                            # Test the JSON generation functions with mocks in place
                            # to verify they run without errors
                            with mock.patch('src.euribor.send_request_per_month', return_value={"months_processed": 1, "monthly_averages": {"2021-01": 1.234}}):
                                with mock.patch('src.euribor.send_request_per_day', return_value={"days_processed": 1, "daily_data": {"2021": {"01": {"01": 1.234}}}}):
                                    generate_all_yearly_json()
                                    generate_all_monthly_json()


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 
