# BuySearchSell Scraper

Extract classified ads from BuySearchSell.com.au - Australia's leading online classifieds marketplace.

## Features

- Scrapes trades & services, buy & sell items, notices, and adult services
- Extracts titles, descriptions, prices, locations, contact info
- Configurable max results
- Supports multiple categories
- Proxy support included

## Input

- **Start URL**: Category page to scrape (default: trades-services)
- **Max Results**: Maximum number of listings to extract (default: 100)

## Output

Each listing contains:
- `id`: Unique listing ID
- `title`: Ad title
- `url`: Full URL to the listing
- `category`: Main category
- `subcategory`: Subcategory
- `description`: Full description
- `location`: Geographic location
- `price`: Price (if available)
- `phone`: Contact phone
- `email`: Contact email
- `image`: Main image URL
- `scrapedAt`: ISO timestamp

## Usage

```json
{
  "startUrl": "https://www.buysearchsell.com.au/all-locations/trades-services/",
  "maxResults": 50
}
```

## Categories

Available categories:
- Trades & Services
- Buy & Sell
- Notices
- Adult Services

Change the `startUrl` to scrape different categories.
