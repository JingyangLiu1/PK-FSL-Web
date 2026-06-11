// For split deployment, you can set:
// window.__API_BASE__ = "https://<your-backend-domain>";
// Default locale for the frontend UI.
window.__APP_LOCALE__ = window.__APP_LOCALE__ || "zh-CN";
window.__API_BASE__ =
  window.__API_BASE__ ||
  (window.location && window.location.origin && window.location.origin !== "null"
    ? window.location.origin
    : "http://127.0.0.1:8000");
