const STORAGE_KEY = "minerakshak-test-api-base-v2";

export function defaultApiBase() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) return saved.replace(/\/$/, "");
  return `${location.protocol}//${location.hostname}:8000`;
}

export function getApiBase() {
  return defaultApiBase();
}

async function getJson(url) {
  const response = await fetch(url, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export function fetchRover(rover = "MRR-01") {
  return getJson(`${getApiBase()}/api/rover/latest?rover_id=${encodeURIComponent(rover)}`);
}


export function fetchAnalytics(rover = "MRR-01") {
  return getJson(`${getApiBase()}/api/analytics?rover_id=${encodeURIComponent(rover)}&history_limit=30`);
}
