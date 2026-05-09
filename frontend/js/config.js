// Frontend config — single bundle, three deployable backends.
//
// Fill in the three URLs below after each backend is deployed. The
// segmented toggle on every page reads/writes `api_backend` in
// localStorage; `API_BASE` is then derived from BACKENDS[<key>].
//
// localStorage["api_base"] still wins if set — handy for dev (point
// at localhost:8080 via DevTools without touching this file).
(function () {
  const BACKENDS = {
    ec2:    "http://ec2-54-196-95-55.compute-1.amazonaws.com",
    ecs:    "http://REPLACE-WITH-ALB-DNS",
    lambda: "https://jfm18fmx23.execute-api.us-east-1.amazonaws.com/prod",
  };

  const ORDER = ["ec2", "ecs", "lambda"];
  const LABELS = { ec2: "EC2", ecs: "ECS", lambda: "Lambda" };

  function isConfigured(key) {
    const v = BACKENDS[key];
    return typeof v === "string" && v && !v.includes("REPLACE-WITH");
  }

  function defaultBackend() {
    return ORDER.find(isConfigured) || ORDER[0];
  }

  function getActiveBackend() {
    const stored = localStorage.getItem("api_backend");
    if (stored && BACKENDS[stored]) return stored;
    return defaultBackend();
  }

  function resolveApiBase() {
    // Manual override (dev): localStorage.setItem("api_base", "http://localhost:8080")
    const manual = localStorage.getItem("api_base");
    if (manual) return manual;
    return BACKENDS[getActiveBackend()] || "";
  }

  function setActiveBackend(key) {
    if (!BACKENDS[key]) return;
    if (key === getActiveBackend()) return;
    localStorage.setItem("api_backend", key);
    // Tokens are signed with one backend's SESSION_SECRET — they won't
    // validate against another. Clear so the user re-logs in cleanly.
    localStorage.removeItem("music_token");
    localStorage.removeItem("music_user");
    // Drop any dev override so the toggle actually takes effect.
    localStorage.removeItem("api_base");
    location.reload();
  }

  window.APP_CONFIG = {
    API_BASE: resolveApiBase(),
    BACKENDS,
    ORDER,
    LABELS,
    isConfigured,
    getActiveBackend,
    setActiveBackend,
  };
})();
