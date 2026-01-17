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


// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function () {
  // Initialize date to today
  const dateInput = document.getElementById('transaction_date');
  if (dateInput) {
    dateInput.value = new Date().toISOString().split('T')[0];
  }

  // Show payment method for completed transactions
  document.querySelectorAll('input[name="transaction_type"]').forEach(radio => {
    radio.addEventListener('change', function () {
      const paymentDiv = document.getElementById('payment_method_div');
      if (paymentDiv) {
        if (this.value === 'RECEIVED' || this.value === 'PAID') {
          paymentDiv.style.display = 'block';
        } else {
          paymentDiv.style.display = 'none';
        }
      }
    });
  });
});

// Show/hide counterparty text input
function counterpartyChange() {
  const select = document.getElementById('counterparty');
  const textDiv = document.getElementById('counterparty_txt_div');

  if (!select || !textDiv) {
    console.error('Counterparty elements not found');
    return;
  }

  if (select.value === 'other') {
    textDiv.style.display = 'block';
    // Disable the select and focus on text input
    const textInput = document.getElementById('counterparty_txt');
    if (textInput) {
      textInput.focus();
      // Remove required from select when using text input
      select.removeAttribute('required');
      textInput.setAttribute('required', 'required');
    }
  } else {
    textDiv.style.display = 'none';
    // Re-enable select
    const textInput = document.getElementById('counterparty_txt');
    if (textInput) {
      textInput.removeAttribute('required');
      select.setAttribute('required', 'required');
    }
  }
}

// Toggle installment settings
function toggleInstallments() {
  const checkbox = document.getElementById('enable_installments');
  const settings = document.getElementById('installment_settings');
  if (!checkbox || !settings) return;

  settings.style.display = checkbox.checked ? 'block' : 'none';
  if (checkbox.checked) {
    previewInstallments();
  }
}

// Toggle custom days field
function toggleCustomDays() {
  const frequency = document.getElementById('installment_frequency');
  const customDiv = document.getElementById('custom_days_div');
  if (!frequency || !customDiv) return;

  customDiv.style.display = frequency.value === 'CUSTOM' ? 'block' : 'none';
  previewInstallments();
}

// Preview installments
function previewInstallments() {
  const amountInput = document.getElementById('amount');
  const numInput = document.getElementById('no_of_installments');
  const frequencyInput = document.getElementById('installment_frequency');

  if (!amountInput || !numInput || !frequencyInput) return;

  const amount = parseFloat(amountInput.value) || 0;
  const numInstallments = parseInt(numInput.value) || 1;
  const frequency = frequencyInput.value;

  if (amount > 0 && numInstallments > 1) {
    const installmentAmount = (amount / numInstallments).toFixed(2);
    const preview = document.getElementById('installment_preview');
    const content = document.getElementById('preview_content');

    if (preview && content) {
      let frequencyText = frequency === 'MONTHLY' ? 'month' : frequency === 'WEEKLY' ? 'week' : 'custom period';

      content.innerHTML = `
  <div class="mt-2">
    <p class="mb-1"><strong>${numInstallments}</strong> installments of <strong>₹${installmentAmount}</strong> each</p>
    <p class="mb-0 text-muted"><small>Frequency: ${frequency.toLowerCase()}</small></p>
  </div>
  `;
      preview.style.display = 'block';
    }
  } else {
    const preview = document.getElementById('installment_preview');
    if (preview) {
      preview.style.display = 'none';
    }
  }
}

// Global function to populate form for editing (called from parent page)
window.editTransaction = function (txnId) {
  fetch(`/update-ledger-transaction/${txnId}`)
    .then(response => response.json())
    .then(data => {
      // Set hidden ID
      document.getElementById('transaction_id').value = data.id;

      // Set transaction type
      document.querySelectorAll('input[name="transaction_type"]').forEach(radio => {
        radio.checked = (radio.value === data.transaction_type);
      });

      // Set counterparty (case-insensitive search)
      const counterpartySelect = document.getElementById('counterparty');
      const options = Array.from(counterpartySelect.options);
      // Try exact match first
      let foundOption = options.find(opt => opt.value === data.counterparty);
      // Try case-insensitive match
      if (!foundOption && data.counterparty) {
        foundOption = options.find(opt => opt.value.toUpperCase() === data.counterparty.toUpperCase());
      }

      if (foundOption) {
        counterpartySelect.value = foundOption.value;
        console.log('Counterparty set to:', foundOption.value);
      } else if (data.counterparty) {
        // Not in dropdown, set as "other" and show text input
        counterpartySelect.value = 'other';
        document.getElementById('counterparty_txt').value = data.counterparty;
        document.getElementById('counterparty_txt_div').style.display = 'block';
        console.log('Counterparty set as other:', data.counterparty);
      }

      // Set counterparty details
      document.getElementById('counterparty_contact').value = data.counterparty_contact || '';
      document.getElementById('counterparty_email').value = data.counterparty_email || '';

      // Set dates and amounts
      document.getElementById('transaction_date').value = data.transaction_date;
      document.getElementById('due_date').value = data.due_date || '';
      document.getElementById('amount').value = data.amount;

      // Set other fields
      document.getElementById('description').value = data.description || '';
      document.getElementById('reference_number').value = data.reference_number || '';
      document.getElementById('invoice_number').value = data.invoice_number || '';
      document.getElementById('notes').value = data.notes || '';
      document.getElementById('tags').value = data.tags || '';

      // Set payment method if applicable
      if (data.payment_method) {
        document.getElementById('payment_method').value = data.payment_method;
        document.getElementById('payment_method_div').style.display = 'block';
      }

      // Hide installment section when editing
      document.getElementById('installment_card').style.display = 'none';

      // Update modal title and button
      document.getElementById('ledgerModalLabel').innerHTML = '<i class="fas fa-edit me-2"></i>Edit Transaction';
      document.getElementById('submitButton').innerHTML = '<i class="fas fa-save me-2"></i>Update Transaction';

      // Change form action to update
      document.getElementById('myLedgerForm').action = `/update-ledger-transaction/${txnId}`;

      // Show modal
      const modal = new bootstrap.Modal(document.getElementById('ledgerModal'));
      modal.show();
    })
    .catch(error => {
      console.error('Error:', error);
      alert('Error loading transaction details');
    });
};

// Reset modal when closing
document.getElementById('ledgerModal').addEventListener('hidden.bs.modal', function () {
  // Reset form
  document.getElementById('myLedgerForm').reset();
  document.getElementById('transaction_id').value = '';

  // Reset action and labels
  document.getElementById('myLedgerForm').action = '/create-ledger-transaction/';
  document.getElementById('ledgerModalLabel').innerHTML = '<i class="fas fa-receipt me-2"></i>Add Ledger Transaction';
  document.getElementById('submitButton').innerHTML = '<i class="fas fa-save me-2"></i>Save Transaction';

  // Show installment section
  document.getElementById('installment_card').style.display = 'block';

  // Reset date to today
  document.getElementById('transaction_date').value = new Date().toISOString().split('T')[0];

  // Hide optional divs
  document.getElementById('counterparty_txt_div').style.display = 'none';
  document.getElementById('payment_method_div').style.display = 'none';
  document.getElementById('installment_settings').style.display = 'none';
});
