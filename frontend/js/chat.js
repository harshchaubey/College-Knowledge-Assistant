const messages = document.getElementById("messages");
const emptyState = document.getElementById("empty-state");
const chatForm = document.getElementById("chat-form");
const questionInput = document.getElementById("question");
const sendButton = chatForm.querySelector(".send-btn");

const DOC_ICON = `
  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"
       stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5" />
  </svg>`;

let isWaiting = false;

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInline(text) {
  return text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
}

function renderMarkdown(markdown) {
  const html = [];
  let paragraph = [];
  let listType = null;

  const flushParagraph = () => {
    if (paragraph.length) {
      html.push(`<p>${renderInline(paragraph.join(" "))}</p>`);
      paragraph = [];
    }
  };
  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`);
      listType = null;
    }
  };

  for (const rawLine of escapeHtml(markdown.trim()).split("\n")) {
    const line = rawLine.trim();
    const bullet = line.match(/^[-*•]\s+(.*)/);
    const numbered = line.match(/^\d+[.)]\s+(.*)/);
    const heading = line.match(/^#{1,6}\s+(.*)/);

    if (bullet || numbered) {
      flushParagraph();
      const type = bullet ? "ul" : "ol";
      if (listType !== type) {
        closeList();
        html.push(`<${type}>`);
        listType = type;
      }
      html.push(`<li>${renderInline((bullet || numbered)[1])}</li>`);
    } else if (heading) {
      flushParagraph();
      closeList();
      html.push(`<p><strong>${renderInline(heading[1])}</strong></p>`);
    } else if (!line) {
      flushParagraph();
      closeList();
    } else {
      closeList();
      paragraph.push(line);
    }
  }

  flushParagraph();
  closeList();
  return html.join("");
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function createMessage(role) {
  emptyState.remove();

  const message = document.createElement("div");
  message.className = `message message-${role}`;

  if (role === "bot") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "CK";
    message.append(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  message.append(bubble);

  messages.append(message);
  scrollToBottom();
  return { message, bubble };
}

function addUserMessage(text) {
  createMessage("user").bubble.textContent = text;
}

function addTypingIndicator() {
  const { message, bubble } = createMessage("bot");
  bubble.innerHTML = '<span class="typing" aria-label="Assistant is thinking"><span></span><span></span><span></span></span>';
  return message;
}

function renderSources(sources) {
  const wrapper = document.createElement("div");
  wrapper.className = "sources";

  const label = document.createElement("p");
  label.className = "sources-label";
  label.textContent = sources.length === 1 ? "Source" : "Sources";
  wrapper.append(label);

  for (const source of sources) {
    const details = document.createElement("details");
    details.className = "source";

    const summary = document.createElement("summary");
    summary.innerHTML = `${DOC_ICON}<span></span>`;
    summary.querySelector("span").textContent = `${source.document} · p. ${source.page}`;

    const snippet = document.createElement("p");
    snippet.textContent = source.snippet;

    details.append(summary, snippet);
    wrapper.append(details);
  }
  return wrapper;
}

function addBotMessage(answer, sources) {
  const { bubble } = createMessage("bot");

  const body = document.createElement("div");
  body.className = "answer";
  body.innerHTML = renderMarkdown(answer);
  bubble.append(body);

  if (sources.length) {
    bubble.append(renderSources(sources));
  }
  scrollToBottom();
}

function addErrorMessage(text) {
  const { message, bubble } = createMessage("bot");
  message.classList.add("is-error");
  bubble.textContent = text;
}

function autoResize() {
  questionInput.style.height = "auto";
  questionInput.style.height = `${questionInput.scrollHeight}px`;
}

function setWaiting(waiting) {
  isWaiting = waiting;
  sendButton.disabled = waiting;
}

async function askQuestion(rawQuestion) {
  const question = rawQuestion.trim();
  if (!question || isWaiting) {
    return;
  }

  addUserMessage(question);
  questionInput.value = "";
  autoResize();
  setWaiting(true);
  const typing = addTypingIndicator();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await response.json().catch(() => ({}));
    typing.remove();

    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : null;
      throw new Error(detail || `Request failed (HTTP ${response.status}).`);
    }
    addBotMessage(data.answer, data.sources || []);
  } catch (error) {
    typing.remove();
    addErrorMessage(
      error instanceof TypeError ? "Could not reach the server. Is it running?" : error.message
    );
  } finally {
    setWaiting(false);
    questionInput.focus();
  }
}

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  askQuestion(questionInput.value);
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

questionInput.addEventListener("input", autoResize);

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => askQuestion(chip.textContent));
});
