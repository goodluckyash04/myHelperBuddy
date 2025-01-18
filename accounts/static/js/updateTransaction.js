CATEGORIES = [
  "Shopping",
  "Food",
  "Investment",
  "Utilities",
  "Groceries",
  "Medical",
  "General",
  "Gifts",
  "Entertainment",
  "EMI",
  "Other",
];
MODE = ["CreditCard", "Online", "Cash"];
STATUS = ["Pendiing", "Completed"];

function openModalAndGetExpense(Id) {
  document.getElementById(
    "updateExpenseForm"
  ).action = `/update-transaction/${Id}`;

  fetch(`/update-transaction/${Id}`)
    .then((response) => response.json())
    .then((data) => {
      console.log("data", data);
      // title
      document.getElementById("title").textContent = `${data.type}`;
      document.getElementById(
        "submitButton"
      ).textContent = `Update ${data.type}`;

      // category
      var categorySelect = document.getElementById("category");
      if (data.type == "Income") {
        CATEGORIES = ["Salary", "Other"];
      }
      categorySelect.innerHTML = CATEGORIES.map(function (category) {
        return `<option value="${category}" ${category === data.category ? "selected" : ""}>${category}</option>`;
      }).join("");

      // beneficiary
      document.getElementById("beneficiary_data").value = data.beneficiary;

      // date
      document.getElementById("date").value = data.date;

      // amount
      document.getElementById("amount").value = data.amount;

      // description
      document.getElementById("description").value = data.description;

      // mode_detail
      document.getElementById("mode_detail").value = data.mode_detail;

      // mode
      var modeSelect = document.getElementById("mode");
      modeSelect.innerHTML = MODE.map(function (mode) {
        return `<option value="${mode}" ${mode === data.mode ? "selected" : ""}>${mode}</option>`;
      }).join("");
    });
}
