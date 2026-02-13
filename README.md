# Trip Weather Forecast

Weather forecast for travel dates using the [Open-Meteo API](https://open-meteo.com/).

## Live Site

**URL**: https://mike.pullen.dev

## Overview

This project fetches weather forecasts for cities on specific travel dates:
- Nashville, TN
- Barcelona, Spain (2 visits)
- La Goulette, Tunisia
- Palermo, Italy
- Rome, Italy
- Savona, Italy
- Marseille, France
- Paris, France

## Tech Stack

- **Backend**: Python (Vercel serverless functions)
- **Frontend**: Plain HTML/CSS/JS
- **API**: Open-Meteo (free, no API key required)

## Local Development

```bash
# Install dependencies
uv sync

# Run locally
vercel dev
```

Visit http://localhost:3000

## Deployment

1. Push to GitHub
2. Import project in Vercel
3. Deploy automatically

## Notes

- Free Open-Meteo API limits forecasts to 16 days
- Dates beyond the forecast window show "Unavailable"
