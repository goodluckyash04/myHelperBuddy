let currentRowId;

function openModal(rowId) {
  currentRowId = rowId;
  const counterpartyElement = document.getElementById('counterparty-' + rowId);
  const currentCounterparty = counterpartyElement.getAttribute('data-counterparty');
  document.getElementById('newCounterparty').value = currentCounterparty;
  new bootstrap.Modal(document.getElementById('editModal')).show();
}

function updateCounterpartyInModal(csrf) {
  const newCounterparty = document.getElementById('newCounterparty').value.trim();
  const oldCounterparty = document.getElementById('counterparty-' + currentRowId).getAttribute('data-counterparty');
  
  if (newCounterparty && newCounterparty !== oldCounterparty) {
    fetch(`/update-counterparty-name/${oldCounterparty}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf
      },
      body: JSON.stringify({ newCounterparty: newCounterparty })
    }).then(response => {
      if (response.ok) {
        const counterpartyElement = document.getElementById('counterparty-' + currentRowId);
        counterpartyElement.textContent = newCounterparty;
        counterpartyElement.setAttribute('data-counterparty', newCounterparty);
      } else {
        alert('Failed to update counterparty.');
      }
    }).catch(error => {
      console.error('Error updating counterparty name:', error);
      alert('Error updating counterparty name.');
    });
  }
  
  // Close the modal
  const modal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
  modal.hide();
}

function openModalAndGetLedger(Id) {
  document.getElementById(
    "myLedgerForm"
  ).action = `/update-ledger-transaction/${Id}`;
  document.getElementById("submitButton").textContent = "Update";

  fetch(`/update-ledger-transaction/${Id}`)
    .then((response) => response.json())
    .then((data) => {
      console.log("data", data);
      document.getElementById(
        "tname"
      ).textContent = `Edit ${data.transaction_type}`;

      // type
      if (data.transaction_type == "Receivable") {
        document.getElementById("receivable").checked = true;
      } else if (data.transaction_type == "Payable") {
        document.getElementById("payable").checked = true;
      } else if (data.transaction_type == "Received") {
        document.getElementById("received").checked = true;
      } else {
        document.getElementById("paid").checked = true;
      }

      // Counterparty
      document.getElementById("counterparty").style.display = "none";
      document.getElementById("counterparty").required = false;

      // no_of_installments
      document.getElementById("no_of_installments").style.display = "none";

      // transaction_date
      document.getElementById("transaction_date").value = data.transaction_date;

      // amount
      document.getElementById("amount").value = data.amount;

      // description
      document.getElementById("description").textContent = data.description;
    });
}

function counterpartyChange() {
  const cParty = document.getElementById('counterparty');
  const cParty_txt = document.getElementById('counterparty_txt');

  if (cParty.value === 'other') {
    cParty.removeAttribute('name');
    cParty_txt.setAttribute('name', 'counterparty');
    cParty_txt.style.display = 'block';
  } else {
    cParty_txt.removeAttribute('name');
    cParty.setAttribute('name', 'counterparty');
    cParty_txt.style.display = 'none';
  }
}