var CATEGORIES = [
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

// Get the current date and time in ISO format (YYYY-MM-DD)
var currentDate = new Date().toISOString().split("T")[0];

function beneficiary_s() {
  var bene = document.getElementById("beneficiary");
  var other_bene = document.getElementById("other_beneficiary");
  var other_input = document.getElementById("beneficiary_text");
  other_input.removeAttribute("style");
  if (bene.value == "Other") {
    bene.removeAttribute("name");
    other_input.setAttribute("name", "beneficiary");
    other_bene.removeAttribute("style");
  } else {
    other_bene.style.display = "none";
    other_input.removeAttribute("name");
    bene.setAttribute("name", "beneficiary");
  }
}

function payType() {
  document.getElementById("transactionBody").removeAttribute("style");
  document.getElementById("date").value = currentDate;

  var submit_button = document.getElementById("submitButton");
  var categorySelect = document.getElementById("category");
  var beneficiary = document.getElementById("beneficiary");
  var other = document.getElementById("beneficiary_text");
  var mode = document.getElementById("mode");
  var mode_detail = document.getElementById("mode_detail");
  var status = document.getElementById("status");

  // Default values
  submit_button.textContent = "Add Income";
  var categories = ["Salary", "Other"];
  beneficiary.style.display = "none";
  other.style.display = "none";
  mode.style.display = "none";
  mode_detail.style.display = "none";
  status.style.display = "none";

  if (Expense.checked) {
    submit_button.textContent = "Add Expense";
    categories = CATEGORIES.filter((item) => item != "EMI");
    beneficiary.style.display = "";
    mode.style.display = "";
    mode_detail.style.display = "";
    status.style.display = "";
  }

  // Update category options
  categorySelect.innerHTML = categories
    .map(function (category) {
      return `<option value="${category}">${category}</option>`;
    })
    .join("");
}

// update transaction modal
function openModalAndGetExpense(Id) {
  document.getElementById(
    "updateExpenseForm"
  ).action = `/update-transaction/${Id}`;

  fetch(`/update-transaction/${Id}`)
    .then((response) => response.json())
    .then((data) => {
      // title
      document.getElementById("title_u").textContent = `${data.type}`;
      document.getElementById(
        "submitButton"
      ).textContent = `Update ${data.type}`;

      // category
      var categorySelect = document.getElementById("category_u");
      if (data.type == "Income") {
        CATEGORIES = ["Salary", "Other"];
      }
      categorySelect.innerHTML = CATEGORIES.map(function (category) {
        return `<option value="${category}" ${category === data.category ? "selected" : ""}>${category}</option>`;
      }).join("");

      // beneficiary
      document.getElementById("beneficiary_data").value = data.beneficiary;

      // date
      document.getElementById("date_u").value = data.date;

      // amount
      document.getElementById("amount_u").value = data.amount;

      // description
      document.getElementById("description_u").value = data.description;

      if (data.type == "Expense") {
        document.getElementById("mode_detail_u").removeAttribute("style");
        document.getElementById("mode_u").removeAttribute("style");

        // mode_detail
        document.getElementById("mode_detail_u").value = data.mode_detail;

        // mode
        var modeSelect = document.getElementById("mode_u");
        modeSelect.innerHTML = MODE.map(function (mode) {
          return `<option value="${mode}" ${mode === data.mode ? "selected" : ""}>${mode}</option>`;
        }).join("");
      } else {
        
        document.getElementById("mode_detail_u").style.display = "none";
        document.getElementById("mode_u").style.display = "none";
      }
    });
}

// show hidden information
function hiddendiscription() {
  td = document.getElementsByClassName("td-desc");
  th = document.getElementById("th-desc");

  if (td[0].hidden == true && th.hidden == true) {
    for (i = 0; i < td.length; i++) {
      td[i].removeAttribute("hidden");
    }
    th.removeAttribute("hidden");
  } else {
    for (i = 0; i < td.length; i++) {
      td[i].setAttribute("hidden", true);
    }
    th.setAttribute("hidden", true);
  }
}

