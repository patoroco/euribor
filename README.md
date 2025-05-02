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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Jorge Maroto
