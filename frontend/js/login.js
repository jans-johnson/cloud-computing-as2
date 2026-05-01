import { api } from "./api.js";

const form = document.getElementById("login-form");
const errorEl = document.getElementById("error");

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.add("show");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.classList.remove("show");
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  try {
    await api.login(email, password);
    window.location.href = "main.html";
  } catch (err) {
    // Spec wording: 'email or password is invalid'
    showError(err.message || "email or password is invalid");
  }
});
