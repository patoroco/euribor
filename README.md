# EURIBOR Rates API

This project provides a simple API to access EURIBOR rates data. The data is automatically updated through GitHub Actions and served via GitHub Pages.

## API Endpoints

### Daily Rates

- Format: `https://patoroco.github.io/euribor/api/daily/{YYYY}/{MM}/{DD}`
- Example: `https://patoroco.github.io/euribor/api/daily/2024/12/27`
- Returns: The EURIBOR rate for the specified date

### Monthly Averages

- Format: `https://patoroco.github.io/euribor/api/monthly/{YYYY}/{MM}`
- Example: `https://patoroco.github.io/euribor/api/monthly/2024/12`
- Returns: The average EURIBOR rate for the specified month

## Data Source

The data is collected from [euribor-rates.eu](https://www.euribor-rates.eu/) and updated automatically through GitHub Actions.

## Automatic Updates

The data is updated daily at 10:00 UTC using a GitHub Action workflow. The workflow:

1. Fetches the latest EURIBOR rates from euribor-rates.eu
2. Updates daily rate files in the `/api/daily/{YYYY}/{MM}/{DD}` directory structure
3. Calculates and updates monthly averages in the `/api/monthly/{YYYY}/{MM}` directory structure
4. Commits and pushes changes to the repository

On the first run, the workflow will also populate historical data starting from 2012.

## Directory Structure

```
api/
├── daily/
│   ├── 2024/
│   │   ├── 01/
│   │   │   ├── 01  # Rate for January 1, 2024
│   │   │   ├── 02  # Rate for January 2, 2024
│   │   │   └── ...
│   │   ├── 02/
│   │   │   └── ...
│   │   └── ...
│   └── 2025/
│       └── ...
└── monthly/
    ├── 2024/
    │   ├── 01  # Average rate for January 2024
    │   ├── 02  # Average rate for February 2024
    │   └── ...
    └── 2025/
        └── ...
```

## Google Sheets Integration

You can easily integrate this API with Google Sheets using custom functions. Here's an example of the functions:

```javascript
/**
 * Formats a date for the Euribor API
 *
 * @param {string|Date} date - Date to format
 * @param {boolean} isMonthly - Whether this is for monthly data (true) or daily data (false)
 * @return {string} Formatted date path for the API
 */
function formatDateForAPI(date, isMonthly) {
  let year, month, day;

  if (typeof date === "string") {
    // If already a string, split by common separators
    const parts = date.split(/[-/\.]/);
    if (parts.length >= 2) {
      year = parts[0];
      month = parts[1].padStart(2, "0");
      day = parts.length > 2 ? parts[2].padStart(2, "0") : "";
    } else {
      return date; // Return as is if format can't be determined
    }
  } else if (date instanceof Date) {
    // If it's a Date object, format it
    year = date.getFullYear();
    month = (date.getMonth() + 1).toString().padStart(2, "0");
    day = date.getDate().toString().padStart(2, "0");
  } else {
    return date.toString(); // Return string representation for unknown types
  }

  // Return path formatted for API: YYYY/MM/DD for daily or YYYY/MM for monthly
  return isMonthly ? `${year}/${month}` : `${year}/${month}/${day}`;
}

/**
 * Fetches Euribor data from the API
 *
 * @param {string} type - The type of data to fetch: "daily" or "monthly"
 * @param {string|Date} date - Date to fetch rate for
 * @return {string} The Euribor rate or error message
 */
function EURIBOR(type, date) {
  if (date === undefined) {
    return "UNDEFINED";
  }

  const isMonthly = type === "monthly";
  const formattedDate = formatDateForAPI(date, isMonthly);
  const url = `https://patoroco.github.io/euribor/api/${type}/${formattedDate}`;

  try {
    const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    const statusCode = response.getResponseCode();

    if (statusCode !== 200) {
      return "NODATA";
    }

    return response.getContentText();
  } catch (error) {
    return "ERROR";
  }
}

/**
 * Fetches daily Euribor rate for a specific date
 *
 * @param {string|Date} date - Date to fetch rate for (YYYY-MM-DD, YYYY/MM/DD, or Date object)
 * @return {string} The daily Euribor rate
 */
function EURIBOR_DAILY(date) {
  return EURIBOR("daily", date);
}

/**
 * Fetches monthly average Euribor rate
 *
 * @param {string|Date} yearMonth - Year and month to fetch average for (YYYY-MM, YYYY/MM, or Date object)
 * @return {string} The monthly average Euribor rate
 */
function EURIBOR_MONTHLY(yearMonth) {
  return EURIBOR("monthly", yearMonth);
}
```

### Usage in Google Sheets

1. Open your Google Sheet
2. Go to Extensions > Apps Script
3. Paste the code above
4. Save and close the script editor
5. In your sheet, you can now use:
   - `=EURIBOR_DAILY("2024/12/27")` or `=EURIBOR_DAILY(DATE(2024,12,27))` for daily rates
   - `=EURIBOR_MONTHLY("2024/12")` or `=EURIBOR_MONTHLY(DATE(2024,12,1))` for monthly averages

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Jorge Maroto
