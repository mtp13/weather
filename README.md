# Trip Weather Forecast

A daily weather forecast for each day of an upcoming trip, from
[Open-Meteo](https://open-meteo.com/) (free, no API key).

**Live:** https://mike.pullen.dev/weather/

A Vercel Python function (`api/weather.py`) reads `itinerary.json` and returns
one forecast per trip day, using each city's local calendar day. A static page
(`index.html`, `app.js`, `style.css`) shows them. Days that have already passed
are hidden, and once every date has passed the page says "Trip dates have
passed".

## Updating the trip

Edit `itinerary.json`: a list of visits, each with `name`, `country`,
`latitude`, `longitude` and `dates` (ISO `YYYY-MM-DD`, one per day).

```json
[
  {
    "name": "Example City",
    "country": "Country",
    "latitude": 12.34,
    "longitude": 56.78,
    "dates": ["2027-01-10", "2027-01-11"]
  }
]
```

Open-Meteo forecasts up to 16 days ahead, so later dates show "Forecast
available ~16 days ahead" until they come into range. The file is public.

## Running and testing

```sh
uv sync && npm ci
vercel dev                     # page and function at http://localhost:3000
uv run python api/weather.py   # print the forecast in the terminal
uv run pytest                  # Python tests
npm test                       # JavaScript unit tests
npm run test:e2e               # Playwright and accessibility tests
npm run lint                   # Prettier and html-validate
```

See [AGENTS.md](AGENTS.md) for the layout, conventions and deployment notes.
