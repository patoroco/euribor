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
    generate_yearly_json, 
    generate_monthly_json,
    generate_all_yearly_json,
    generate_all_monthly_json
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
    (tmp_path / "api" / "daily").mkdir()
    (tmp_path / "api" / "monthly").mkdir()
    (tmp_path / "api" / "daily" / "2021").mkdir()
    (tmp_path / "api" / "daily" / "2021" / "01").mkdir()
    (tmp_path / "api" / "monthly" / "2021").mkdir()
    
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
        # Test for directory creation in send_request_per_day
        with mock.patch('builtins.open', mock.mock_open()) as mock_file:
            send_request_per_day(2021, 1)
            # Check that proper nested directory is created
            mock_makedirs.assert_any_call(os.path.join('api', 'daily', '2021', '01'), exist_ok=True)
        
        # Test for directory creation in send_request_per_month
        with mock.patch('builtins.open', mock.mock_open()) as mock_file:
            send_request_per_month(2021)
            # Check that proper nested directory is created
            mock_makedirs.assert_any_call(os.path.join('api', 'monthly', '2021'), exist_ok=True)

    def test_file_writing_per_day(self, temp_dir, mock_requests_get):
        """Test file writing in send_request_per_day function"""
        # Change to the temp directory for file operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Mock the file writing
            with mock.patch('builtins.open', mock.mock_open()) as mock_file:
                send_request_per_day(2021, 1)
                
                # Check if the file was opened for writing
                mock_file.assert_called()
                
                # Verify at least one call was to the correct path format
                call_args_list = mock_file.call_args_list
                
                # Check that at least one path has the correct format
                path_format_found = False
                for call in call_args_list:
                    path = call[0][0]
                    # The path should be something like api/daily/2021/01/01
                    if path.startswith(os.path.join('api', 'daily', '2021', '01')):
                        path_format_found = True
                        break
                        
                assert path_format_found, "No file path with the expected format was used"
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
                
                # Verify at least one call was to the correct path format
                call_args_list = mock_file.call_args_list
                
                # Check that at least one path has the correct format
                path_format_found = False
                for call in call_args_list:
                    path = call[0][0]
                    # The path should be something like api/monthly/2021/01
                    if path.startswith(os.path.join('api', 'monthly', '2021')):
                        path_format_found = True
                        break
                        
                assert path_format_found, "No file path with the expected format was used"
        finally:
            # Restore original directory
            os.chdir(original_dir)
    
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
                generate_yearly_json('2021', '01', 3.456)
                
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
                generate_yearly_json('2021', '01', 3.456)
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    assert data['01']['_meta']['last_modified'] == '2021-12-31T12:00:00'
                
                # Test updating the same month with a different value
                # The last_modified date should change
                datetime_mock.now.return_value = datetime(2022, 1, 1, 12, 0, 0)
                generate_yearly_json('2021', '01', 3.789)
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    assert data['01']['value'] == '3.789'
                    assert data['01']['_meta']['last_modified'] == '2022-01-01T12:00:00'
        finally:
            # Restore original directory
            os.chdir(original_dir)
    
    def test_generate_all_yearly_json(self, temp_dir):
        """Test generating all yearly JSON files from monthly data"""
        # Change to the temp directory for file operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Create test monthly data
            os.makedirs(os.path.join('api', 'monthly', '2021'), exist_ok=True)
            os.makedirs(os.path.join('api', '2021'), exist_ok=True)
            
            # Create sample monthly data files
            with open(os.path.join('api', 'monthly', '2021', '01'), 'w') as f:
                f.write('3.456')
            with open(os.path.join('api', 'monthly', '2021', '02'), 'w') as f:
                f.write('3.789')
            
            # Mock datetime.now() properly to return our fixed datetime
            fixed_datetime = datetime(2021, 12, 31, 12, 0, 0)
            datetime_mock = mock.Mock(wraps=datetime)
            datetime_mock.now.return_value = fixed_datetime
            
            # Patch the datetime class in the module being tested
            with mock.patch('src.euribor.datetime', datetime_mock):
                # Test generating all JSON files
                generate_all_yearly_json()
                
                # Verify the JSON file was created with the right content
                json_file = os.path.join('api', '2021', 'index.json')
                assert os.path.exists(json_file)
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    assert '01' in data
                    assert '02' in data
                    assert data['01']['value'] == '3.456'
                    assert data['02']['value'] == '3.789'
                    assert data['01']['_meta']['full_date'] == '2021-01'
                    assert data['02']['_meta']['full_date'] == '2021-02'
                    assert data['01']['_meta']['last_modified'] == '2021-12-31T12:00:00'
                    assert data['02']['_meta']['last_modified'] == '2021-12-31T12:00:00'
        finally:
            # Restore original directory
            os.chdir(original_dir)

    def test_monthly_json_generation(self, temp_dir):
        """Test JSON file generation with daily data for a month"""
        # Change to the temp directory for file operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Create test directories
            os.makedirs(os.path.join('api', '2021', '01'), exist_ok=True)
            
            # Create test daily data
            daily_data = {
                "01": 3.456,
                "15": 3.789,
                "31": 3.567
            }
            
            # Mock datetime.now() properly to return our fixed datetime
            fixed_datetime = datetime(2021, 12, 31, 12, 0, 0)
            datetime_mock = mock.Mock(wraps=datetime)
            datetime_mock.now.return_value = fixed_datetime
            
            # Patch the datetime class in the module being tested
            with mock.patch('src.euribor.datetime', datetime_mock):
                # Test generating a monthly JSON file
                generate_monthly_json('2021', '01', daily_data)
                
                # Verify the JSON file was created with the right content
                json_file = os.path.join('api', '2021', '01', 'index.json')
                assert os.path.exists(json_file)
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    # Check that all days are present
                    assert '01' in data
                    assert '15' in data
                    assert '31' in data
                    
                    # Check the values
                    assert data['01']['value'] == '3.456'
                    assert data['15']['value'] == '3.789'
                    assert data['31']['value'] == '3.567'
                    
                    # Check metadata
                    assert data['01']['_meta']['full_date'] == '2021-01-01'
                    assert data['01']['_meta']['last_modified'] == '2021-12-31T12:00:00'
                    
                    # Check order of days (should be sorted numerically)
                    days = list(data.keys())
                    assert days == sorted(days, key=int)
                
                # Test updating with a changed value
                daily_data['15'] = 3.999
                datetime_mock.now.return_value = datetime(2022, 1, 1, 12, 0, 0)
                generate_monthly_json('2021', '01', daily_data)
                
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    assert data['15']['value'] == '3.999'
                    assert data['15']['_meta']['last_modified'] == '2022-01-01T12:00:00'
                    # Other dates should remain unchanged
                    assert data['01']['_meta']['last_modified'] == '2021-12-31T12:00:00'
        finally:
            # Restore original directory
            os.chdir(original_dir)
    
    def test_generate_all_monthly_json(self, temp_dir):
        """Test generating all monthly JSON files from daily data"""
        # Change to the temp directory for file operations
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Create test daily data
            os.makedirs(os.path.join('api', 'daily', '2021', '01'), exist_ok=True)
            os.makedirs(os.path.join('api', 'daily', '2021', '02'), exist_ok=True)
            os.makedirs(os.path.join('api', '2021', '01'), exist_ok=True)
            os.makedirs(os.path.join('api', '2021', '02'), exist_ok=True)
            
            # Create sample daily data files
            with open(os.path.join('api', 'daily', '2021', '01', '01'), 'w') as f:
                f.write('3.456')
            with open(os.path.join('api', 'daily', '2021', '01', '15'), 'w') as f:
                f.write('3.789')
            with open(os.path.join('api', 'daily', '2021', '02', '01'), 'w') as f:
                f.write('3.567')
            
            # Mock datetime.now() properly to return our fixed datetime
            fixed_datetime = datetime(2021, 12, 31, 12, 0, 0)
            datetime_mock = mock.Mock(wraps=datetime)
            datetime_mock.now.return_value = fixed_datetime
            
            # Patch the datetime class in the module being tested
            with mock.patch('src.euribor.datetime', datetime_mock):
                # Test generating all monthly JSON files
                generate_all_monthly_json()
                
                # Verify the JSON file for January was created with the right content
                jan_json_file = os.path.join('api', '2021', '01', 'index.json')
                assert os.path.exists(jan_json_file)
                
                with open(jan_json_file, 'r') as f:
                    data = json.load(f)
                    assert '01' in data
                    assert '15' in data
                    assert data['01']['value'] == '3.456'
                    assert data['15']['value'] == '3.789'
                
                # Verify the JSON file for February was created with the right content
                feb_json_file = os.path.join('api', '2021', '02', 'index.json')
                assert os.path.exists(feb_json_file)
                
                with open(feb_json_file, 'r') as f:
                    data = json.load(f)
                    assert '01' in data
                    assert data['01']['value'] == '3.567'
        finally:
            # Restore original directory
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
                        with mock.patch('os.listdir', return_value=['01']):
                            with mock.patch('os.path.isdir', return_value=True):
                                with mock.patch('os.path.isfile', return_value=True):
                                    with mock.patch('json.dump'):
                                        # Test if these functions run without errors
                                        send_request_per_day(2021, 1)
                                        send_request_per_month(2021)
                                        generate_all_yearly_json()
                                        generate_all_monthly_json()


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 
