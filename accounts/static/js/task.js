
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

function openModalAndGetTask(Id) {
  document.getElementById("myTaskForm").action = `/editTask/${Id}`;
  document.getElementById("submitbutton").textContent = "Update Task";

  fetch(`/editTask/${Id}`)
    .then((response) => response.json())
    .then((data) => {
      console.log("data", data);
      // Priority
      var prioritySelect = document.getElementById("priority");

      PRIORITY = ["High", "Medium", "Low"];
      document.getElementById("exampleModalLabel").textContent =
        data.name?.length < 18 ? data.name : `${data.name.slice(0, 17)}...`;

      prioritySelect.innerHTML = PRIORITY.map(function (priority) {
        return `<option value="${priority}" ${priority === data.priority ? "selected" : ""}>${priority}</option>`;
      }).join("");

      // name
      document.getElementById("title").value = data.name;

      // complete_by_date
      document.getElementById("complete_by").value = data.complete_by_date;

      // description
      document.getElementById("descirption").value = data.description;
    });
}
