// Trip weather: fetches ./api/weather and renders one card per upcoming trip day.
const API_URL = "./api/weather";
const LOCALE = "en-US";

const MESSAGES = {
  loading: "Loading weather data…",
  empty: "No weather data available",
  allPast: "Trip dates have passed",
  outOfRange: "Forecast available ~16 days ahead",
  unavailable: "Forecast unavailable",
  fetchFailed: "Failed to fetch weather data",
};

let listEl;
let statusEl;

// "2026-07-07" -> "Tuesday, Jul 7". Read and formatted in UTC so the visitor's
// timezone can never shift the calendar date.
function formatDate(isoDate) {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString(LOCALE, {
    timeZone: "UTC",
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

// Past days are hidden; everything else gets a card.
function upcomingDays(days) {
  return days.filter((day) => day.status !== "past");
}

// The text for the status region once data has loaded ("" hides it).
function statusMessage(days) {
  if (days.length === 0) return MESSAGES.empty;
  if (upcomingDays(days).length === 0) return MESSAGES.allPast;
  return "";
}

function createElement(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

// e.g. "↑ High 73°F", where the arrow is hidden from screen readers and
// "High" is visible only to them.
function createTemp(className, arrow, label, value) {
  const temp = createElement("span", className);
  const arrowEl = createElement("span", "", `${arrow} `);
  arrowEl.setAttribute("aria-hidden", "true");
  temp.append(
    arrowEl,
    createElement("span", "visually-hidden", `${label} `),
    `${value}°F`,
  );
  return temp;
}

function createCard(day) {
  const card = createElement("li", "weather-card");
  card.dataset.status = day.status;

  const date = createElement("time", "date", formatDate(day.date));
  date.setAttribute("datetime", day.date);
  const temps = createElement("p", "temps");

  if (day.status === "ok") {
    temps.append(
      createTemp("high", "↑", "High", day.max_temp),
      createTemp("low", "↓", "Low", day.min_temp),
    );
  } else {
    const message =
      day.status === "out_of_range"
        ? MESSAGES.outOfRange
        : MESSAGES.unavailable;
    temps.append(createElement("span", "unavailable", message));
  }

  card.append(
    date,
    createElement("h2", "city", day.city),
    createElement("p", "country", day.country),
    createElement(
      "p",
      "weather",
      day.status === "ok" ? day.weather || "-" : "-",
    ),
    temps,
  );
  return card;
}

function showStatus(message, state) {
  statusEl.textContent = message;
  statusEl.dataset.state = state;
  statusEl.hidden = message === "";
}

function renderCards(days) {
  listEl.replaceChildren(...upcomingDays(days).map(createCard));
  showStatus(statusMessage(days), "message");
}

function showError(message) {
  listEl.replaceChildren();
  showStatus(`Error: ${message}`, "error");
}

async function loadWeather(fetchImpl = fetch) {
  let response;
  try {
    response = await fetchImpl(API_URL);
  } catch {
    showError(MESSAGES.fetchFailed);
    return;
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    showError(data?.error || MESSAGES.fetchFailed);
  } else if (!Array.isArray(data)) {
    showError(MESSAGES.fetchFailed);
  } else {
    renderCards(data);
  }
}

function bindDomElements() {
  listEl = document.getElementById("weather-list");
  statusEl = document.getElementById("status");
}

function initializeApp(fetchImpl) {
  bindDomElements();
  if (!listEl || !statusEl) return Promise.resolve();

  showStatus(MESSAGES.loading, "loading");
  return loadWeather(fetchImpl);
}

if (typeof document !== "undefined") {
  initializeApp();
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    API_URL,
    MESSAGES,
    formatDate,
    upcomingDays,
    statusMessage,
    createCard,
    renderCards,
    loadWeather,
    initializeApp,
  };
}
