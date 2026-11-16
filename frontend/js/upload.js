const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const dropzoneTitle = document.getElementById("dropzone-title");
const dropzoneSub = document.getElementById("dropzone-sub");
const uploadStatus = document.getElementById("upload-status");
const docList = document.getElementById("doc-list");

let isUploading = false;

function isPdf(file) {
  return file.name.toLowerCase().endsWith(".pdf");
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function setUploading(uploading, fileName = "") {
  isUploading = uploading;
  dropzone.classList.toggle("is-uploading", uploading);
  fileInput.disabled = uploading;
  dropzoneTitle.textContent = uploading ? `Indexing ${fileName}…` : "Drop a PDF here";
  dropzoneSub.textContent = uploading
    ? "Large PDFs can take a minute."
    : "or click to browse";
}

function showStatus(message, type) {
  uploadStatus.textContent = message;
  uploadStatus.className = `upload-status is-${type}`;
  uploadStatus.hidden = false;
}

async function readError(response) {
  const data = await response.json().catch(() => ({}));
  return typeof data.detail === "string" ? data.detail : `Request failed (HTTP ${response.status}).`;
}

function friendlyError(error) {
  return error instanceof TypeError ? "Could not reach the server. Is it running?" : error.message;
}

function showEmptyList(text) {
  const item = document.createElement("li");
  item.className = "doc-empty";
  item.textContent = text;
  docList.replaceChildren(item);
}

function createDocumentItem({ filename, pages, chunks }) {
  const item = document.createElement("li");
  item.className = "doc-item";
  item.innerHTML = `
    <span class="doc-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
           stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
        <path d="M14 3v5h5" />
      </svg>
    </span>
    <div class="doc-info">
      <span class="doc-name"></span>
      <span class="doc-meta"></span>
    </div>
    <button class="doc-delete" type="button">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M4 7h16" />
        <path d="M10 11v6M14 11v6" />
        <path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12" />
        <path d="M9 7V4h6v3" />
      </svg>
    </button>
  `;

  const name = item.querySelector(".doc-name");
  name.textContent = filename;
  name.title = filename;
  item.querySelector(".doc-meta").textContent =
    `${plural(pages, "page")} · ${plural(chunks, "chunk")}`;

  const deleteButton = item.querySelector(".doc-delete");
  deleteButton.setAttribute("aria-label", `Remove ${filename}`);
  deleteButton.title = "Remove document";
  deleteButton.addEventListener("click", () => removeDocument(filename, deleteButton));

  return item;
}

async function loadDocuments() {
  try {
    const response = await fetch("/documents");
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    const documents = await response.json();
    if (documents.length === 0) {
      showEmptyList("No documents yet. Upload a PDF to get started.");
      return;
    }
    docList.replaceChildren(...documents.map(createDocumentItem));
  } catch (error) {
    showEmptyList(`Could not load documents: ${friendlyError(error)}`);
  }
}

async function removeDocument(filename, button) {
  if (!window.confirm(`Remove "${filename}"? Its content will no longer be used for answers.`)) {
    return;
  }
  button.disabled = true;
  try {
    const response = await fetch(`/documents/${encodeURIComponent(filename)}`, { method: "DELETE" });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    showStatus(`${filename} was removed.`, "success");
    await loadDocuments();
  } catch (error) {
    button.disabled = false;
    showStatus(friendlyError(error), "error");
  }
}

async function uploadFile(file) {
  if (isUploading) {
    return;
  }
  if (!isPdf(file)) {
    showStatus(`"${file.name}" is not a PDF. Please choose a .pdf file.`, "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  uploadStatus.hidden = true;
  setUploading(true, file.name);

  try {
    const response = await fetch("/upload", { method: "POST", body: formData });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    const data = await response.json();
    const message = data.replaced
      ? `${data.filename} was re-indexed. The previous version was replaced.`
      : `${data.filename} is ready. You can now ask questions about it.`;
    showStatus(message, "success");
    await loadDocuments();
  } catch (error) {
    showStatus(friendlyError(error), "error");
  } finally {
    setUploading(false);
  }
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  fileInput.value = "";
  if (file) {
    uploadFile(file);
  }
});

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  if (!isUploading) {
    dropzone.classList.add("is-dragover");
  }
});

dropzone.addEventListener("dragleave", (event) => {
  if (!dropzone.contains(event.relatedTarget)) {
    dropzone.classList.remove("is-dragover");
  }
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("is-dragover");
  const file = event.dataTransfer.files[0];
  if (file) {
    uploadFile(file);
  }
});

window.addEventListener("dragover", (event) => event.preventDefault());
window.addEventListener("drop", (event) => event.preventDefault());

loadDocuments();
