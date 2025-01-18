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
function generateCSV() {
  var table = document.getElementById("myTable");
  var filename = document.getElementById("key");
  if (filename) {
    console.log(filename)
    filename = filename.textContent.replace(","," ").trim() + ".csv";
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

document
  .getElementById("select-all-checkbox")
  .addEventListener("change", function () {
    var checkboxes = document.getElementsByName("record_ids");
    for (var i = 0; i < checkboxes.length; i++) {
      checkboxes[i].checked = this.checked;
    }
  });

function reviseTotal() {
  actualTotal = document.getElementById("total");
  console.log(actualTotal.textContent);
  newValue = document.getElementById("select");

  console.log(newValue.parentElement.parentElement.children[4]);
}
