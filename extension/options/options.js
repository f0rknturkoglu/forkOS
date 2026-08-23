import { getApiBase, setApiBase } from "../config.js";

const input = document.getElementById("api-base");
const status = document.getElementById("status");
input.value = await getApiBase();

document.getElementById("server-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  status.textContent = "İzin bekleniyor…";
  try {
    input.value = await setApiBase(input.value);
    status.textContent = "Sunucu adresi kaydedildi.";
  } catch (error) {
    status.textContent = error instanceof Error ? error.message : "Adres kaydedilemedi.";
  }
});
