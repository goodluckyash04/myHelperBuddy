function generateCSV() {
  var table = document.getElementById("myTable");
  var filename = document.getElementById("key");
  if (filename) {
    console.log(filename);
    filename = filename.textContent.replace(",", " ").trim() + ".csv";
  } else {
    filename = "mhb-report.csv";
  }
  var csvRows = [];

  for (var i = 0; i < table.rows.length; i++) {
    var row = table.rows[i];
    var rowData = [];

    for (var j = 0; j < row.cells.length; j++) {
      var cell = row.cells[j];
      rowData.push('"' + cell.textContent.trim().replace(/"/g, '""') + '"');
    }

    csvRows.push(rowData.join(","));
  }

  var csvContent = csvRows.join("\n");

  var blob = new Blob([csvContent], { type: "text/csv" });

  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;

  a.click();
}

function confirmationModal() {
  const modal = document.getElementById("confirmModal");
  modal.addEventListener("show.bs.modal", function (event) {
    const button = event.relatedTarget;
    const undoUrl = button.getAttribute("data-url");
    const confirmButton = modal.querySelector("#confirmButton");
    confirmButton.setAttribute("href", undoUrl);
  });
}

document.addEventListener('DOMContentLoaded', confirmationModal);

function selectMultiple() {
  var checkboxes = document.getElementsByName("record_ids");
  for (var i = 0; i < checkboxes.length; i++) {
    checkboxes[i].checked = this.checked;
  }
}

document.getElementById("select-all-checkbox").addEventListener("change", selectMultiple);


