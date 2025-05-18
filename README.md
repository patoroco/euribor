# EURIBOR Rates API

This project provides a simple API to access EURIBOR rates data. The data is automatically updated through GitHub Actions and served via GitHub Pages.

## API Endpoints

> **Note about GitHub Pages**: This API is hosted on GitHub Pages, which automatically serves `index.json` files when a directory URL is accessed. This means you can omit `index.json` from all JSON endpoint URLs.

### Yearly JSON with Monthly Averages

- Format: `https://patoroco.github.io/euribor/api/{YYYY}`
- Example: `https://patoroco.github.io/euribor/api/2024`
- Returns: JSON object with monthly average EURIBOR rates for the specified year

Example response:

```json
{
  "01": {
    "value": "3.589",
    "_meta": {
      "full_date": "2024-01",
      "last_modified": "2024-05-21T10:00:00"
    }
  },
  "02": {
    "value": "3.572",
    "_meta": {
      "full_date": "2024-02",
      "last_modified": "2024-05-21T10:00:00"
    }
  }
  // ... other months
}
```

### Monthly JSON with Daily Rates

- Format: `https://patoroco.github.io/euribor/api/{YYYY}/{MM}`
- Example: `https://patoroco.github.io/euribor/api/2024/12`
- Returns: JSON object with daily EURIBOR rates for the specified month

> **Important**: The JSON includes entries for all days of the month. Days without data (weekends, holidays) have a `null` value while days with data have the actual rate as a string.

Example response:

```json
{
  "01": {
    "value": "3.585",
    "_meta": {
      "full_date": "2024-12-01",
      "last_modified": "2024-12-01T10:00:00"
    }
  },
  "02": {
    "value": "3.590",
    "_meta": {
      "full_date": "2024-12-02",
      "last_modified": "2024-12-02T10:00:00"
    }
  },
  "03": {
    "value": null,
    "_meta": {
      "full_date": "2024-12-03",
      "last_modified": "2024-12-03T10:00:00"
    }
  }
  // ... other days
}
```

## Data Source

The data is collected from [euribor-rates.eu](https://www.euribor-rates.eu/) and updated automatically through GitHub Actions.

## Automatic Updates

The data is updated daily at 10:00 UTC using a GitHub Action workflow. The workflow:

1. Fetches the latest EURIBOR rates from euribor-rates.eu
2. Calculates monthly averages based on daily rates
3. Generates and updates JSON files for both yearly (with monthly data) and monthly (with daily data)
4. Commits and pushes changes to the repository

On the first run, the workflow will also populate historical data starting from 1999.

## Directory Structure

```
api/
├── 2024/
│   ├── index.json  # JSON with all monthly averages for 2024 (accessible via /api/2024/)
│   ├── 01/
│   │   └── index.json  # JSON with all daily rates for January 2024 (accessible via /api/2024/01/)
│   ├── 02/
│   │   └── index.json  # JSON with all daily rates for February 2024 (accessible via /api/2024/02/)
│   └── ...
└── 2025/
    └── ...
```

Each of the `index.json` files can be accessed through GitHub Pages by simply using the directory URL (without explicitly referencing the filename). For example, `https://patoroco.github.io/euribor/api/2024/` will serve the yearly JSON file for 2024.

## Development

This project uses UV, an ultra-fast Python package manager, for dependency management and virtual environments.

### Setting up the development environment

1. **Install UV**:

   ```bash
   curl -fsSL https://astral.sh/uv/install.sh | bash
   ```

2. **Create virtual environment**:

   ```bash
   uv venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   # .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:

   ```bash
   uv pip install -e ".[dev]"  # Install package with development dependencies
   ```

4. **Run tests**:
   ```bash
   python -m pytest
   ```

### Running the Script

The script can be run with various options to control which years and months to process:

```bash
# Process current month (and previous month if in first week)
python -m src.euribor

# Process a specific year
python -m src.euribor --year 2024

# Process a specific month of the current year
python -m src.euribor --month 5

# Process a specific year and month
python -m src.euribor --year 2024 --month 5

# Process all historical years (1999 to current)
python -m src.euribor --all
```

Command line options:

- `--year YEAR`: Process only the specified year
- `--month MONTH`: Process only the specified month
- `--all`: Process all years from 1999 to current
- No arguments: Process the current month (and previous month if in first week of the month, or previous year's December if in January)

Processing only the current month significantly speeds up execution, especially for automation via GitHub Actions.

#### Smart defaults for automation:

- If running in January, it also processes December of the previous year
- If running in the first week of a month, it also processes the previous month
- This ensures that any late updates to the previous period are captured

For more information on UV, visit the [UV official website](https://astral.sh/uv).

## Google Sheets Integration

You can easily integrate this API with Google Sheets using custom functions. Here's an example of the functions:

```javascript
/**
 * Fetches Euribor data from the JSON API
 *
 * @param {string} type - The type of data to fetch: "monthly" for yearly JSON or "daily" for monthly JSON
 * @param {string|Date} date - Date to fetch rate for (YYYY for yearly, YYYY-MM for monthly)
 * @param {string} key - The specific key to fetch (month number for yearly, day number for monthly)
 * @param {string} field - The field to return (defaults to "value")
 * @return {string} The Euribor rate or error message
 */
function EURIBOR_JSON(type, date, key, field = "value") {
  if (date === undefined) {
    return "UNDEFINED";
  }

  let year, month;

  if (typeof date === "string") {
    // If already a string, split by common separators
    const parts = date.split(/[-/\.]/);
    year = parts[0];
    month = parts.length > 1 ? parts[1].padStart(2, "0") : "";
  } else if (date instanceof Date) {
    // If it's a Date object, format it
    year = date.getFullYear();
    month = (date.getMonth() + 1).toString().padStart(2, "0");
  } else {
    return "INVALID_DATE";
  }

  // Prepare path for API call
  let url;
  if (type === "monthly") {
    // Yearly JSON with monthly data
    url = `https://patoroco.github.io/euribor/api/${year}`;
  } else if (type === "daily") {
    // Monthly JSON with daily data
    if (!month) return "MISSING_MONTH";
    url = `https://patoroco.github.io/euribor/api/${year}/${month}`;
  } else {
    return "INVALID_TYPE";
  }

  try {
    const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    const statusCode = response.getResponseCode();

    if (statusCode !== 200) {
      return "NODATA";
    }

    const jsonData = JSON.parse(response.getContentText());

    // If no key specified, return the entire JSON
    if (!key) {
      return JSON.stringify(jsonData);
    }

    // Ensure key is padded with zeros if it's a number
    const paddedKey = isNaN(key) ? key : key.toString().padStart(2, "0");

    // Check if the key exists
    if (!jsonData[paddedKey]) {
      return "KEY_NOT_FOUND";
    }

    // Return the requested field
    if (field === "value") {
      return jsonData[paddedKey].value;
    } else if (field.startsWith("_meta.")) {
      const metaField = field.split(".")[1];
      return jsonData[paddedKey]._meta[metaField];
    } else {
      return "INVALID_FIELD";
    }
  } catch (error) {
    return "ERROR: " + error.toString();
  }
}

/**
 * Fetches a specific day's value from the monthly JSON
 *
 * @param {string|Date} yearMonth - Year and month (YYYY-MM, YYYY/MM, or Date object)
 * @param {string|number} day - The day to fetch (1-31)
 * @return {string} The daily Euribor rate
 */
function EURIBOR_JSON_DAILY(yearMonth, day) {
  return EURIBOR_JSON("daily", yearMonth, day);
}

/**
 * Fetches a specific month's average from the yearly JSON
 *
 * @param {string|number} year - The year (YYYY)
 * @param {string|number} month - The month to fetch (1-12)
 * @return {string} The monthly average Euribor rate
 */
function EURIBOR_JSON_MONTHLY(year, month) {
  return EURIBOR_JSON("monthly", year, month);
}
```

### Usage in Google Sheets

1. Open your Google Sheet
2. Go to Extensions > Apps Script
3. Paste the code above
4. Save and close the script editor
5. In your sheet, you can now use:
   - `=EURIBOR_JSON_DAILY("2024/12", 27)` for daily rates from the JSON API
   - `=EURIBOR_JSON_MONTHLY(2024, 12)` for monthly averages from the JSON API

> **Note**: The JSON functions use GitHub Pages' automatic index.json serving feature, making the URLs simpler and more intuitive.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Jorge Maroto
