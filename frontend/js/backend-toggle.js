// Renders the backend selector into any element with `data-backend-toggle`.
// Runs after DOMContentLoaded; non-module so it can drop into any page.
(function () {
  function render(host) {
    const cfg = window.APP_CONFIG;
    if (!cfg) return;
    const active = cfg.getActiveBackend();

    host.classList.add("backend-toggle");
    host.setAttribute("role", "group");
    host.setAttribute("aria-label", "Backend selector");
    host.innerHTML = "";

    const label = document.createElement("span");
    label.className = "backend-toggle-label";
    label.textContent = "Backend:";
    host.appendChild(label);

    cfg.ORDER.forEach((key) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "backend-toggle-btn";
      btn.textContent = cfg.LABELS[key];
      btn.dataset.backend = key;
      if (key === active) btn.classList.add("active");
      if (!cfg.isConfigured(key)) {
        btn.disabled = true;
        btn.title = "URL not configured in js/config.js";
      }
      btn.addEventListener("click", () => cfg.setActiveBackend(key));
      host.appendChild(btn);
    });
  }

  function init() {
    document
      .querySelectorAll("[data-backend-toggle]")
      .forEach((el) => render(el));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
