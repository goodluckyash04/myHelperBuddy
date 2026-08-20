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
  var status = document.getElementById("status");

  // Default values (Income)
  submit_button.textContent = "Add Income";
  var categories = ["Salary", "Other"];
  var beneficiary_container = document.getElementById("beneficiary_container");
  var status_container = document.getElementById("status_container");
  if (beneficiary_container) beneficiary_container.style.display = "none";
  if (status_container) status_container.style.display = "none";
  other.style.display = "none";

  if (Expense.checked) {
    submit_button.textContent = "Add Expense";
    categories = CATEGORIES.filter((item) => item != "EMI");
    document.getElementById("beneficiary_container").style.display = "block";
    document.getElementById("status_container").style.display = "block";
  } else {
    document.getElementById("beneficiary_container").style.display = "none";
    document.getElementById("status_container").style.display = "none";
  }

  // Update category options
  categorySelect.innerHTML = categories
    .map(function (category, index) {
      return `
        <div class="txn-pill-option">
          <input type="radio" name="category" id="cat_${category}_${index}" value="${category}" required>
          <label class="txn-pill-label" for="cat_${category}_${index}">${category}</label>
        </div>`;
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
      // Update button text without removing the icon
      var btnTextEl = document.getElementById("submitBtnText");
      if (btnTextEl) btnTextEl.textContent = `Update ${data.type}`;

      // category
      var categorySelect = document.getElementById("category_u");
      if (data.type == "Income") {
        CATEGORIES = ["Salary", "Other"];
      }
      categorySelect.innerHTML = CATEGORIES.map(function (category, index) {
        return `
        <div class="txn-pill-option">
          <input type="radio" name="category" id="cat_u_${category}_${index}" value="${category}" ${category === data.category ? "checked" : ""} required>
          <label class="txn-pill-label" for="cat_u_${category}_${index}">${category}</label>
        </div>`;
      }).join("");

      // beneficiary
      document.getElementById("beneficiary_data").value = data.beneficiary;

      // date
      document.getElementById("date_u").value = data.date;

      // amount
      document.getElementById("amount_u").value = data.amount;

      // description
      document.getElementById("description_u").value = data.description;
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

