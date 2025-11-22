(function () {
  // --- Config ---
  const MAX_UPLOAD_SIZE = 10 * 1024 * 1024; // 10MB
  const ALLOWED = [
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "application/pdf",
    "text/plain",
    "text/csv",
    "text/html",
    "application/json",
    "application/zip",
    "application/x-zip-compressed",
    "application/x-rar-compressed",
    "application/vnd.rar",
    "application/epub+zip",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
  ];

  // --- Upload modal elements ---
  const uploadModalEl = document.getElementById("fileUploadModal");
  const dropzone = document.getElementById("dropzone");
  const chooseFileBtn = document.getElementById("chooseFileBtn");
  const fileInput = document.getElementById("fileInput");
  const fileDetails = document.getElementById("fileDetails");
  const fileNameEl = document.getElementById("fileName");
  const fileMetaEl = document.getElementById("fileMeta");
  const fileIcon = document.getElementById("fileIcon");
  const clearFileBtn = document.getElementById("clearFileBtn");
  const submitBtn = document.getElementById("submitBtn");
  const uploadForm = document.getElementById("uploadForm");
  const uploadFeedback = document.getElementById("uploadFeedback");
  const uploadProgress = document.getElementById("uploadProgress");
  const uploadMsg = document.getElementById("uploadMsg");
  const maxSizeLabel = document.getElementById("maxSizeLabel");

  // small guard: if upload modal isn't present, skip upload wiring (page may not include it)
  const hasUpload = uploadForm && fileInput && chooseFileBtn && dropzone;

  // --- Helpers ---
  function humanSize(bytes) {
    if (bytes === 0) return "0 bytes";
    if (!bytes && bytes !== 0) return "unknown";
    const units = ["bytes", "KB", "MB", "GB", "TB"];
    let i = 0,
      s = Number(bytes);
    while (s >= 1024 && i < units.length - 1) {
      s /= 1024;
      i++;
    }
    return (i === 0 ? parseInt(s) : s.toFixed(2)) + " " + units[i];
  }

  function iconClassForType(ct) {
    if (!ct) return "bi bi-file-earmark-fill text-muted";
    ct = ct.toLowerCase();
    if (ct.includes("pdf")) return "bi bi-file-earmark-pdf-fill text-danger";
    if (ct.includes("word") || ct.includes("officedocument.word"))
      return "bi bi-file-earmark-word-fill text-primary";
    if (ct.includes("excel") || ct.includes("spreadsheet"))
      return "bi bi-file-earmark-spreadsheet-fill text-success";
    if (ct.includes("zip")) return "bi bi-file-zip-fill text-secondary";
    if (ct.includes("text")) return "bi bi-file-text-fill text-info";
    return "bi bi-file-earmark-fill text-muted";
  }

  // --- Upload UI functions ---
  function showFileInfo(file) {
    if (!file || !fileDetails) return;
    fileDetails.classList.remove("d-none");
    fileNameEl.textContent = file.name;
    fileMetaEl.textContent = `${file.type || "unknown"} · ${humanSize(
      file.size
    )}`;
    fileIcon.className = iconClassForType(file.type) + " fs-4";
    if (submitBtn) submitBtn.disabled = false;
  }

  function clearFile() {
    if (fileInput)
      try {
        fileInput.value = "";
      } catch {}
    if (fileDetails) fileDetails.classList.add("d-none");
    if (fileNameEl) fileNameEl.textContent = "";
    if (fileMetaEl) fileMetaEl.textContent = "";
    if (fileIcon)
      fileIcon.className = "bi bi-file-earmark-fill fs-4 text-muted";
    if (submitBtn) submitBtn.disabled = true;
    if (uploadFeedback) uploadFeedback.classList.add("d-none");
    if (uploadProgress) uploadProgress.style.width = "0%";
    if (uploadMsg) uploadMsg.textContent = "";
  }

  if (maxSizeLabel)
    maxSizeLabel.textContent = `${(MAX_UPLOAD_SIZE / (1024 * 1024)).toFixed(
      0
    )} MB`;

  // --- Upload wiring (if present) ---
  if (hasUpload) {
    // only choose button opens picker (prevents double-open)
    chooseFileBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      fileInput.click();
    });

    // file input change
    fileInput.addEventListener("change", function (e) {
      const f = fileInput.files && fileInput.files[0];
      if (!f) {
        clearFile();
        return;
      }
      if (f.size > MAX_UPLOAD_SIZE) {
        alert(
          `File too large. Max ${(MAX_UPLOAD_SIZE / 1024 / 1024).toFixed(
            0
          )} MB.`
        );
        return clearFile();
      }
      if (ALLOWED.length && f.type && !ALLOWED.includes(f.type)) {
        const lc = f.name.toLowerCase();
        const extOK = [
          ".pdf",
          ".doc",
          ".docx",
          ".xls",
          ".xlsx",
          ".txt",
          ".zip",
          ".png",
          ".jpg",
          ".jpeg",
        ].some((ext) => lc.endsWith(ext));
        if (!extOK) {
          alert("This file type is not allowed.");
          return clearFile();
        }
      }
      showFileInfo(f);
    });

    // clear button
    if (clearFileBtn) clearFileBtn.addEventListener("click", clearFile);

    // drag & drop UX (dropzone DOES NOT call fileInput.click())
    ["dragenter", "dragover"].forEach((evt) => {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("dragover");
      });
    });
    ["dragleave", "dragend"].forEach((evt) => {
      dropzone.addEventListener(evt, function (e) {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("dragover");
      });
    });

    dropzone.addEventListener("drop", function (e) {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("dragover");
      const dt = e.dataTransfer;
      if (!dt || !dt.files || !dt.files.length) return;
      // try to set fileInput.files (works on many browsers)
      try {
        fileInput.files = dt.files;
      } catch (err) {
        /* ignore */
      }
      const f = dt.files[0];
      if (!f) return;
      if (f.size > MAX_UPLOAD_SIZE) {
        alert(
          `File too large. Max ${(MAX_UPLOAD_SIZE / 1024 / 1024).toFixed(
            0
          )} MB.`
        );
        return clearFile();
      }
      if (ALLOWED.length && f.type && !ALLOWED.includes(f.type)) {
        const lc = f.name.toLowerCase();
        const extOK = [
          ".pdf",
          ".doc",
          ".epub",
          ".docx",
          ".xls",
          ".xlsx",
          ".txt",
          ".zip",
          ".png",
          ".jpg",
          ".jpeg",
        ].some((ext) => lc.endsWith(ext));
        if (!extOK) {
          alert("This file type is not allowed.");
          return clearFile();
        }
      }
      showFileInfo(f);
      // update visible drop text if you have one
      const dropText = document.getElementById("dropText");
      if (dropText) dropText.innerHTML = `<strong>${f.name}</strong>`;
    });

    // keyboard accessibility: Enter/Space should open via choose button
    dropzone.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        chooseFileBtn.click();
      }
    });

    // upload form submission via XHR for progress
    uploadForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const f = fileInput.files && fileInput.files[0];
      if (!f) {
        alert("Please choose a file first.");
        return;
      }
      if (f.size > MAX_UPLOAD_SIZE) {
        alert("File too large.");
        return;
      }

      const fd = new FormData();
      fd.append("file", f);
      const pwdInput = document.getElementById("download_password");
      if (pwdInput && pwdInput.value)
        fd.append("download_password", pwdInput.value);

      const csrfInput = uploadForm.querySelector(
        'input[name="csrfmiddlewaretoken"]'
      );
      const csrf = csrfInput ? csrfInput.value : null;

      if (uploadFeedback) uploadFeedback.classList.remove("d-none");
      if (uploadMsg) uploadMsg.textContent = "Uploading...";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="bi bi-upload me-1"></i> Uploading...';
      }

      const xhr = new XMLHttpRequest();
      xhr.open("POST", uploadForm.action, true);
      if (csrf) xhr.setRequestHeader("X-CSRFToken", csrf);

      xhr.upload.onprogress = function (ev) {
        if (ev.lengthComputable && uploadProgress) {
          const pct = Math.round((ev.loaded / ev.total) * 100);
          uploadProgress.style.width = pct + "%";
          uploadProgress.setAttribute("aria-valuenow", String(pct));
        }
      };

      xhr.onload = function () {
        // XHR followed redirect and returned the final HTML (likely 200)
        // Check responseText for server-side Django messages (alert elements)
        const text = xhr.responseText || "";

        // parse response HTML
        let containsError = false;
        try {
          const parser = new DOMParser();
          const doc = parser.parseFromString(text, "text/html");

          // 1) look for Bootstrap alert elements with alert-danger or alert-warning
          const alertEls = doc.querySelectorAll(
            ".alert, .messages, .alert-danger, .alert-warning, .alert-error"
          );
          if (alertEls && alertEls.length) {
            alertEls.forEach((el) => {
              const cls = el.className || "";
              const alertText = el.textContent?.trim();
              if (alertText) {
                // decide whether it's an error or success by class or by keywords
                if (
                  cls.indexOf("alert-danger") !== -1 ||
                  cls.indexOf("alert-error") !== -1 ||
                  cls.indexOf("alert-warning") !== -1
                ) {
                  // display first error we find
                  if (uploadMsg) uploadMsg.textContent = alertText;
                  containsError = true;
                } else if (cls.indexOf("alert-success") !== -1) {
                  // success message — we'll handle as success below
                } else {
                  // some sites render messages without specific classes - check keywords
                  const low = alertText.toLowerCase();
                  if (
                    low.includes("error") ||
                    low.includes("failed") ||
                    low.includes("already exist") ||
                    low.includes("already exists")
                  ) {
                    if (uploadMsg) uploadMsg.textContent = alertText;
                    containsError = true;
                  }
                }
              }
            });
          }

          // 2) If you use a specific container for messages, e.g. <div id="django-messages">, check it:
          if (!containsError) {
            const msgContainer =
              doc.getElementById("django-messages") ||
              doc.querySelector(".django-messages");
            if (msgContainer) {
              const s = msgContainer.textContent?.trim() || "";
              if (s) {
                if (
                  s.toLowerCase().includes("error") ||
                  s.toLowerCase().includes("already exist")
                ) {
                  if (uploadMsg) uploadMsg.textContent = s;
                  containsError = true;
                }
              }
            }
          }
        } catch (err) {
          console.warn("Could not parse response HTML for messages", err);
        }

        if (containsError) {
          // show inline error message and re-enable UI
          if (uploadFeedback) uploadFeedback.classList.remove("d-none");
          if (uploadMsg && !uploadMsg.textContent)
            uploadMsg.textContent = "Upload failed. See server message.";
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-upload me-1"></i> Upload';
          }
          return;
        }

        // No error detected in HTML: treat as success
        if (xhr.status >= 200 && xhr.status < 300) {
          const modalInstance =
            bootstrap.Modal.getInstance(uploadModalEl) ||
            new bootstrap.Modal(uploadModalEl);
          modalInstance.hide();
          setTimeout(() => {
            location.reload();
          }, 350);
          return;
        }

        // Fallback for non-2xx statuses
        if (uploadMsg)
          uploadMsg.textContent =
            xhr.responseText || "Upload failed. Please try again.";
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="bi bi-upload me-1"></i> Upload';
        }
      };

      xhr.onerror = function () {
        if (uploadMsg)
          uploadMsg.textContent = "Network error. Please try again.";
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="bi bi-upload me-1"></i> Upload';
        }
      };

      const keywordsInput = document.getElementById("keywords");
      if (keywordsInput && keywordsInput.value) {
        fd.append("keywords", keywordsInput.value);
      }

      xhr.send(fd);
    });

    // reset on modal open/close
    uploadModalEl.addEventListener("shown.bs.modal", function () {
      clearFile();
      chooseFileBtn.focus();
    });
    uploadModalEl.addEventListener("hidden.bs.modal", function () {
      clearFile();
      if (uploadProgress) uploadProgress.style.width = "0%";
    });
  }

  // --- Password visibility toggle (delegated) ---
  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".btn-toggle-pwd");
    if (!btn) return;
    const input = btn
      .closest(".input-group")
      ?.querySelector(".pwd-toggle-input");
    if (!input) return;
    const isHidden = input.type === "password";
    const icon = btn.querySelector("i");
    if (isHidden) {
      input.type = "text";
      btn.setAttribute("aria-pressed", "true");
      btn.title = "Hide password";
      if (icon) {
        icon.classList.remove("bi-eye");
        icon.classList.add("bi-eye-slash");
      }
    } else {
      input.type = "password";
      btn.setAttribute("aria-pressed", "false");
      btn.title = "Show password";
      if (icon) {
        icon.classList.remove("bi-eye-slash");
        icon.classList.add("bi-eye");
      }
    }
    input.focus();
  });

  document.addEventListener("keydown", function (e) {
    const btn = e.target.closest && e.target.closest(".btn-toggle-pwd");
    if (!btn) return;
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      btn.click();
    }
  });

  // --- Download password modal wiring (set action + submit UX) ---
  (function () {
    const pwdModal = document.getElementById("pwdModal");
    const pwdForm = document.getElementById("pwdForm");
    if (!pwdModal || !pwdForm) return;

    pwdModal.addEventListener("show.bs.modal", function (event) {
      const btn = event.relatedTarget;
      const fileId = btn?.getAttribute("data-file-id");
      const filename = btn?.getAttribute("data-filename") || "";
      const titleEl = document.getElementById("pwdFileName");
      if (titleEl) titleEl.textContent = filename;
      if (fileId) pwdForm.action = `/document/${fileId}/download/`;
    });

    pwdForm.addEventListener("submit", function () {
      // close modal BEFORE submit
      const modalElement = pwdForm.closest(".modal");
      const modalInstance = bootstrap.Modal.getInstance(modalElement);
      if (modalInstance) modalInstance.hide();

      // disable button + show loading text
      const btn = pwdForm.querySelector('button[type="submit"]');
      if (btn) {
        btn.disabled = true;
        btn.innerText = "Please wait...";
      }
      // let normal form submission proceed (server will return file or redirect)
    });
  })();

  // --- Generic safe guards / no-op for missing elements handled above ---
})();

// ---- Delete file button ---
(function () {
  const modal = document.getElementById("deleteModal");
  const form = document.getElementById("deleteForm");

  modal.addEventListener("show.bs.modal", function (event) {
    const btn = event.relatedTarget;

    const fileId = btn.getAttribute("data-file-id");
    const filename = btn.getAttribute("data-filename");
    const isProtected = btn.getAttribute("data-protected") === "1";

    // Set form action
    form.action = `/document/${fileId}/delete/`;

    // Fill content
    document.getElementById("deleteFilename").textContent = filename;

    // Show/hide password input
    const wrap = document.getElementById("deletePasswordWrap");
    document.getElementById("deletePassword").value = "";

    if (isProtected) wrap.classList.remove("d-none");
    else wrap.classList.add("d-none");
  });
})();

// Tag input widget
(function () {
  const tagInput = document.getElementById("tagInput");
  const tagChips = document.getElementById("tagChips");
  const keywordsHidden = document.getElementById("keywords");
  if (!tagInput || !tagChips || !keywordsHidden) return;

  // state: array of normalized tags
  let tags = [];

  function normalizeTag(s) {
    return s.trim().toLowerCase().replace(/\s+/g, " ");
  }

  function renderTags() {
    tagChips.innerHTML = "";
    tags.forEach((t, idx) => {
      const chip = document.createElement("span");
      chip.className = "tag-chip me-1 mb-1 d-inline-flex align-items-center";
      chip.title = t;
      chip.innerHTML = `<span class="tag-text">${t}</span>`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "remove ms-2";
      btn.innerHTML = "&times;";
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        removeTag(idx);
      });
      chip.appendChild(btn);
      tagChips.appendChild(chip);
    });
    keywordsHidden.value = tags.join(", ");
  }

  function addTagRaw(s) {
    if (!s) return;
    const t = normalizeTag(s);
    if (!t) return;
    if (tags.includes(t)) return;
    tags.push(t);
    renderTags();
  }
  function removeTag(i) {
    tags.splice(i, 1);
    renderTags();
  }

  // Accept Enter, comma, semicolon; also handle paste with commas
  tagInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === "," || e.key === ";") {
      e.preventDefault();
      const v = tagInput.value;
      const parts = v
        .split(/[,;]+/)
        .map((x) => x.trim())
        .filter(Boolean);
      parts.forEach(addTagRaw);
      tagInput.value = "";
    } else if (e.key === "Backspace" && tagInput.value === "") {
      // remove last
      if (tags.length) {
        tags.pop();
        renderTags();
      }
    }
  });

  tagInput.addEventListener("blur", (e) => {
    const v = tagInput.value;
    if (v && v.trim()) {
      v.split(/[,;]+/)
        .map((x) => x.trim())
        .filter(Boolean)
        .forEach(addTagRaw);
      tagInput.value = "";
    }
  });

  tagInput.addEventListener("paste", (e) => {
    e.preventDefault();
    const txt = (e.clipboardData || window.clipboardData).getData("text");
    if (!txt) return;
    txt
      .split(/[,;]+/)
      .map((x) => x.trim())
      .filter(Boolean)
      .forEach(addTagRaw);
    tagInput.value = "";
  });

  // Expose helper to prefill tags from a comma string (useful when editing)
  window.__tagsWidget = {
    set: function (commaString) {
      tags = [];
      if (!commaString) {
        renderTags();
        return;
      }
      commaString
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean)
        .forEach(addTagRaw);
    },
    get: function () {
      return tags.slice();
    },
  };

  // initialize render
  renderTags();
})();

// --- Edit document ----
(function () {
  const modal = document.getElementById("editDetailsModal");
  const form = document.getElementById("editDetailsForm");

  modal.addEventListener("show.bs.modal", function (event) {
    const btn = event.relatedTarget;
    const fileId = btn.getAttribute("data-file-id");
    const filename = btn.getAttribute("data-filename");
    const keywords = btn.getAttribute("data-keywords") || "";
    const isProtected = btn.getAttribute("data-protected") === "1";

    // Set form action
    form.action = `/document/${fileId}/update-details/`;

    // Fill values
    document.getElementById("editFilename").value = filename;
    document.getElementById("editKeywords").value = keywords;

    // Reset password fields
    document.getElementById("editOldPassword").value = "";
    document.getElementById("editPassword").value = "";
    document.getElementById("clearEditPwd").checked = false;

    // Show/hide old password
    const wrap = document.getElementById("oldPasswordWrap");
    if (isProtected) wrap.classList.remove("d-none");
    else wrap.classList.add("d-none");
  });
})();
