import { api } from "./api.js";

const form = document.getElementById("register-form");
const errorEl = document.getElementById("error");

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.add("show");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.classList.remove("show");
  const email = document.getElementById("email").value.trim();
  const user_name = document.getElementById("user_name").value.trim();
  const password = document.getElementById("password").value;
  if (!email || !user_name || !password) {
    showError("All fields are required");
    return;
  }
  try {
    await api.register(email, user_name, password);
    window.location.href = "index.html";
  } catch (err) {
    // Backend returns 'The email already exists' for duplicates.
    showError(err.message || "Registration failed");
  }
});
