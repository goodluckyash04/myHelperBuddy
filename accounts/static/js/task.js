
function dateCheck() {
  var date = document.getElementById("complete_by").value;
  var submitButton = document.getElementById("submitbutton");
  var currentDate = new Date();
  var givenDate = new Date(date);

  if (givenDate <= currentDate) {
    alert('Complete By date must be in the future.');
    submitButton.disabled = true;
  } else {
    submitButton.disabled = false;
  }
}

// Reset modal when opening for "Add Task"
function resetTaskModal() {
  document.getElementById("myTaskForm").action = "/addTask/";
  document.getElementById("exampleModalLabel").textContent = "Add Task";
  document.getElementById("submitbutton").innerHTML = '<i class="fa-solid fa-plus-circle"></i> Add Task';
  document.getElementById("myTaskForm").reset();

  // Reset to default values
  document.getElementById('start_date').value = new Date().toISOString().split('T')[0];
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('complete_by').value = tomorrow.toISOString().split('T')[0];
  document.getElementById('priority').value = 'Medium';

  // Hide status field (only for edit mode)
  const statusField = document.getElementById('statusField');
  if (statusField) {
    statusField.style.display = 'none';
  }
}

// Open modal and populate for editing
function openModalAndGetTask(Id) {
  document.getElementById("myTaskForm").action = `/editTask/${Id}`;
  document.getElementById("exampleModalLabel").textContent = "Edit Task";
  document.getElementById("submitbutton").innerHTML = '<i class="fa-solid fa-save"></i> Update Task';

  // Show status field for editing
  const statusField = document.getElementById('statusField');
  if (statusField) {
    statusField.style.display = 'block';
  }

  fetch(`/editTask/${Id}`)
    .then((response) => response.json())
    .then((data) => {
      console.log("data", data);

      // Set modal title (truncate if long)
      document.getElementById("exampleModalLabel").textContent =
        data.name?.length < 18 ? `Edit: ${data.name}` : `Edit: ${data.name.slice(0, 17)}...`;

      // Priority
      document.getElementById("priority").value = data.priority || "Medium";

      // Task name
      document.getElementById("title").value = data.name || "";

      // Dates
      document.getElementById("start_date").value = data.start_date || "";
      document.getElementById("complete_by").value = data.complete_by_date || "";

      // Description
      document.getElementById("descirption").value = data.description || "";

      // Estimated hours
      if (data.estimated_hours) {
        document.getElementById("estimated_hours").value = data.estimated_hours;
      }

      // Status
      if (data.status) {
        document.getElementById("status").value = data.status;
      }

      // Category
      if (data.category) {
        document.getElementById("category").value = data.category;
      }

      // Tags (multi-select)
      if (data.tags && data.tags.length > 0) {
        const tagSelect = document.getElementById("tags");
        Array.from(tagSelect.options).forEach(option => {
          option.selected = data.tags.includes(parseInt(option.value));
        });
      }
    })
    .catch(error => {
      console.error("Error fetching task:", error);
      alert("Failed to load task details. Please try again.");
    });
}

// Add color indicators to category dropdown
document.addEventListener('DOMContentLoaded', function () {
  const categorySelect = document.getElementById('category');
  if (categorySelect) {
    Array.from(categorySelect.options).forEach(option => {
      if (option.dataset.color) {
        option.style.background = option.dataset.color + '20'; // 20% opacity
        option.style.borderLeft = `4px solid ${option.dataset.color}`;
        option.style.paddingLeft = '8px';
      }
    });
  }
});
