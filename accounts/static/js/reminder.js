document.getElementById("frequency").addEventListener("change", function () {
    const frequency = this.value;
    const customRepeatDaysContainer = document.getElementById(
      "customRepeatDaysContainer"
    );

    if (frequency === "custom") {
      customRepeatDaysContainer.style.display = "block"; // Show custom repeat input
    } else {
      customRepeatDaysContainer.style.display = "none"; // Hide custom repeat input
    }
  });