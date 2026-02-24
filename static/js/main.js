document.addEventListener("DOMContentLoaded", () => {
  const dateInput = document.querySelector("#appointment_date");
  if (dateInput) {
    const today = new Date().toISOString().split("T")[0];
    dateInput.min = today;
  }

  const flashStack = document.querySelector("#flash-stack");
  if (flashStack) {
    setTimeout(() => {
      flashStack.style.opacity = "0";
      flashStack.style.transition = "opacity 0.4s ease";
    }, 3000);
  }
});
