import { api } from "./api.js";

const userArea = document.getElementById("user-area");
const subsEl = document.getElementById("subs");
const subsEmpty = document.getElementById("subs-empty");
const resultsEl = document.getElementById("results");
const queryForm = document.getElementById("query-form");
const queryError = document.getElementById("query-error");

function requireAuth() {
  if (!api.currentUserName()) {
    window.location.href = "index.html";
    return false;
  }
  return true;
}

function songCard(song, action) {
  const div = document.createElement("div");
  div.className = "song";

  const img = document.createElement("img");
  img.src = song.image_url || "";
  img.alt = song.artist;
  img.onerror = () => { img.style.visibility = "hidden"; };

  const meta = document.createElement("div");
  meta.innerHTML = `
    <div class="title">${escapeHtml(song.title)}</div>
    <div class="meta">${escapeHtml(song.artist)} — ${escapeHtml(song.album)} (${escapeHtml(song.year)})</div>
  `;

  const btn = document.createElement("button");
  btn.textContent = action.label;
  btn.className = action.className || "";
  btn.addEventListener("click", () => action.onClick(song, div));

  div.append(img, meta, btn);
  return div;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

async function refreshSubscriptions() {
  const { items } = await api.listSubscriptions();
  subsEl.innerHTML = "";
  if (!items.length) {
    subsEmpty.style.display = "block";
    return;
  }
  subsEmpty.style.display = "none";
  for (const song of items) {
    subsEl.append(
      songCard(song, {
        label: "Remove",
        className: "danger",
        onClick: async (s, node) => {
          await api.unsubscribe({ artist: s.artist, title: s.title, album: s.album });
          node.remove();
          if (!subsEl.children.length) subsEmpty.style.display = "block";
        },
      }),
    );
  }
}

queryForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  queryError.classList.remove("show");
  resultsEl.innerHTML = "";

  const title = document.getElementById("title").value.trim();
  const artist = document.getElementById("artist").value.trim();
  const album = document.getElementById("album").value.trim();
  const year = document.getElementById("year").value.trim();

  if (!title && !artist && !album && !year) {
    queryError.textContent = "At least one field must be completed.";
    queryError.classList.add("show");
    return;
  }

  let resp;
  try {
    resp = await api.searchMusic({ title, artist, album, year });
  } catch (err) {
    queryError.textContent = err.message || "Query failed.";
    queryError.classList.add("show");
    return;
  }

  if (!resp.items.length) {
    queryError.textContent = "No result is retrieved. Please query again";
    queryError.classList.add("show");
    return;
  }

  for (const song of resp.items) {
    resultsEl.append(
      songCard(song, {
        label: "Subscribe",
        onClick: async (s, node) => {
          await api.subscribe({ artist: s.artist, title: s.title, album: s.album });
          node.querySelector("button").disabled = true;
          node.querySelector("button").textContent = "Subscribed";
          await refreshSubscriptions();
        },
      }),
    );
  }
});

document.getElementById("logout").addEventListener("click", async (e) => {
  e.preventDefault();
  await api.logout();
  window.location.href = "index.html";
});

if (requireAuth()) {
  userArea.textContent = api.currentUserName();
  refreshSubscriptions().catch((err) => {
    // If the backend says we're not authenticated, kick to login.
    if (/auth/i.test(err.message)) window.location.href = "index.html";
  });
}
