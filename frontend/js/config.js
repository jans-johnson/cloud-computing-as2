// Edit API_BASE after deploying a backend. The same frontend bundle is
// uploaded to S3 once and points at whichever of the three backends is
// being demonstrated by changing this single value.
window.APP_CONFIG = {
  API_BASE: window.localStorage.getItem("api_base") || "http://localhost:8080",
};
