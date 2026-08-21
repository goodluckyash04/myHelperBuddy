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
  } else {
    toggleEditName(currentRowId);
  }
}

window.toggleEditName = function(rowId) {
  const viewDiv = document.getElementById('name-view-' + rowId);
  const editDiv = document.getElementById('name-edit-' + rowId);
  const inputEl = document.getElementById('input-' + rowId);
  
  if (viewDiv.style.display === 'none') {
    viewDiv.style.display = 'flex';
    editDiv.style.display = 'none';
  } else {
    viewDiv.style.display = 'none';
    editDiv.style.display = 'flex';
    inputEl.focus();
    inputEl.selectionStart = inputEl.selectionEnd = inputEl.value.length;
  }
};

window.submitEditName = function(rowId, csrf) {
  const newCounterparty = document.getElementById('input-' + rowId).value.trim();
  const oldCounterparty = document.getElementById('counterparty-' + rowId).getAttribute('data-counterparty');

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
        const rowLink = document.getElementById('row-link-' + rowId);
        if(rowLink) {
          rowLink.href = '/ledger-transaction/' + encodeURIComponent(newCounterparty);
        }
        const counterpartyElement = document.getElementById('counterparty-' + rowId);
        counterpartyElement.textContent = newCounterparty;
        counterpartyElement.setAttribute('data-counterparty', newCounterparty);
        toggleEditName(rowId);
      } else {
        alert('Failed to update counterparty.');
      }
    }).catch(error => {
      console.error('Error updating counterparty name:', error);
      alert('Error updating counterparty name.');
    });
  } else {
    toggleEditName(rowId);
  }
};



// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function () {
  // Initialize date to today
  const dateInput = document.getElementById('transaction_date');
  if (dateInput) {
    dateInput.value = new Date().toISOString().split('T')[0];
  }
});




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
      const counterpartyTxtDiv = document.getElementById('counterparty_txt_div');
      const counterpartyTxtInput = document.getElementById('counterparty_txt');
      
      const options = Array.from(counterpartySelect.options);
      const dataCpty = (data.counterparty || '').trim();
      
      // Try exact match first
      let foundOption = options.find(opt => opt.value.trim() === dataCpty);
      // Try case-insensitive match
      if (!foundOption && dataCpty) {
        foundOption = options.find(opt => opt.value.trim().toUpperCase() === dataCpty.toUpperCase());
      }

      if (foundOption) {
        counterpartySelect.value = foundOption.value;
        counterpartyTxtDiv.style.display = 'none';
        counterpartyTxtInput.removeAttribute('required');
        counterpartySelect.setAttribute('required', 'required');
      } else if (data.counterparty) {
        // Not in dropdown, set as "other" and show text input
        counterpartySelect.value = 'other';
        counterpartyTxtInput.value = data.counterparty;
        counterpartyTxtDiv.style.display = 'block';
        counterpartySelect.removeAttribute('required');
        counterpartyTxtInput.setAttribute('required', 'required');
      }
      
      // Trigger counterparty change to load tabs
      if (typeof counterpartyChange === 'function') {
        counterpartyChange();
      }

      // Set dates and amounts
      document.getElementById('transaction_date').value = data.transaction_date;
      document.getElementById('amount').value = data.amount;

      // Set other fields
      document.getElementById('description').value = data.description || '';
      const notesEl = document.getElementById('notes');
      if (notesEl) notesEl.value = data.notes || '';

      // Set tab_name selector securely
      const tabSel = document.getElementById('tab_name_select');
      if (tabSel && data.tab_name) {
        const tabName = data.tab_name.trim();
        let opt = Array.from(tabSel.options).find(o => o.value.trim().toUpperCase() === tabName.toUpperCase());
        
        if (!opt) {
          // If the tab is missing (e.g. legacy or casing issue), inject it so it can be selected
          opt = document.createElement('option');
          opt.value = data.tab_name;
          opt.textContent = data.tab_name;
          // insert right before the "+ New Tab" (__new__) option
          const newTabOpt = Array.from(tabSel.options).find(o => o.value === '__new__');
          if (newTabOpt) {
            tabSel.insertBefore(opt, newTabOpt);
          } else {
            tabSel.appendChild(opt);
          }
        }
        
        tabSel.value = opt.value;
        if (typeof tabSelectChange === 'function') tabSelectChange();
      }



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
  document.getElementById('ledgerModalLabel').innerHTML = '<i class="fas fa-receipt me-2"></i> Add Ledger Entry';
  document.getElementById('submitButton').innerHTML = '<i class="fas fa-save me-2"></i>Save Entry';



  // Reset date to today
  document.getElementById('transaction_date').value = new Date().toISOString().split('T')[0];

  // Hide optional divs
  document.getElementById('counterparty_txt_div').style.display = 'none';
});

// Open modal from Passbook view and pre-fill details
window.openPassbookModal = function(counterparty, tabName) {
  const form = document.getElementById('myLedgerForm');
  form.reset();
  document.getElementById('transaction_id').value = '';
  form.action = '/create-ledger-transaction/';
  document.getElementById('ledgerModalLabel').innerHTML = '<i class="fas fa-receipt me-2"></i> Add Ledger Entry';
  document.getElementById('submitButton').innerHTML = '<i class="fas fa-save me-2"></i>Save Entry';
  
  // Set date to today
  document.getElementById('transaction_date').value = new Date().toISOString().split('T')[0];
  
  // Set default direction
  const rdo = document.getElementById('paid');
  if(rdo) rdo.checked = true;

  // Set counterparty
  const cpSelect = document.getElementById('counterparty');
  const cpTxtInput = document.getElementById('counterparty_txt');
  const cpTxtDiv = document.getElementById('counterparty_txt_div');
  
  if (cpSelect) {
    let found = Array.from(cpSelect.options).find(opt => opt.value.trim().toUpperCase() === counterparty.toUpperCase());
    if (found) {
      cpSelect.value = found.value;
      cpTxtDiv.style.display = 'none';
      cpTxtInput.removeAttribute('required');
      cpSelect.setAttribute('required', 'required');
    } else {
      cpSelect.value = 'other';
      cpTxtInput.value = counterparty;
      cpTxtDiv.style.display = 'block';
      cpSelect.removeAttribute('required');
      cpTxtInput.setAttribute('required', 'required');
    }
  }

  // Trigger tab load
  if (typeof counterpartyChange === 'function') {
    counterpartyChange();
    setTimeout(() => {
      const tabSelect = document.getElementById('tab_name_select');
      if (tabSelect && tabName) {
        tabSelect.value = tabName;
      }
    }, 50);
  }

  // Show modal
  const modal = new bootstrap.Modal(document.getElementById('ledgerModal'));
  modal.show();
};
