import {
  getApiBase,
  setApiBase,
  getWebBase,
  setWebBase,
  normalizeApiBase,
  normalizeWebBase,
} from "../config.js";

const input = document.getElementById("api-base");
const status = document.getElementById("status");
input.value = await getApiBase();
const webInput = document.getElementById("web-base");
webInput.value = await getWebBase();

document
  .getElementById("server-form")
  .addEventListener("submit", async (event) => {
    event.preventDefault();
    status.textContent = "İzin bekleniyor…";
    try {
      const apiBase = normalizeApiBase(input.value);
      const webBase = normalizeWebBase(webInput.value);
      input.value = await setApiBase(apiBase);
      webInput.value = await setWebBase(webBase);
      status.textContent = "Sunucu adresi kaydedildi.";
    } catch (error) {
      status.textContent =
        error instanceof Error ? error.message : "Adres kaydedilemedi.";
    }
  });
