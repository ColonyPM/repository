document.addEventListener("DOMContentLoaded", () => {
  const modalEl = document.getElementById("uploadTokenModal");
  if (!modalEl) return;

  const tokenBox = modalEl.querySelector("upload-token-box");

  modalEl.addEventListener("shown.bs.modal", () => {
    if (tokenBox && typeof tokenBox.start === "function") {
      tokenBox.start();
    }
  });

  modalEl.addEventListener("hidden.bs.modal", () => {
    if (tokenBox && typeof tokenBox.stop === "function") {
      tokenBox.stop();
    }
  });
});
