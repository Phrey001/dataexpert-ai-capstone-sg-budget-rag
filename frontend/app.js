const API_BASE_URL = window.AGENT_API_BASE_URL || window.location.origin;

const form = document.getElementById("ask-form");
const queryInput = document.getElementById("query");
const submitBtn = document.getElementById("submit-btn");

const errorBanner = document.getElementById("error-banner");
const resultPanel = document.getElementById("result");

const answerEl = document.getElementById("answer");
const applicabilityEl = document.getElementById("applicability-note");
const uncertaintyEl = document.getElementById("uncertainty-note");
const confidenceEl = document.getElementById("confidence");
const finalReasonEl = document.getElementById("final-reason");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);
  hideError();
  hideOutputs();

  const payload = { query: queryInput.value.trim() };

  if (!payload.query) {
    showError("Please enter a query.");
    setLoading(false);
    return;
  }

  try {
    const url = `${API_BASE_URL}/ask`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${response.status})`);
    }

    const data = await response.json();
    renderResult(data);
  } catch (error) {
    showError(error.message || "Unexpected error while calling API.");
  } finally {
    setLoading(false);
  }
});

function renderResult(data) {
  answerEl.textContent = data.answer || "";
  renderDetail(
    applicabilityEl,
    "How this applies to your question",
    data.applicability_note,
  );
  renderDetail(
    uncertaintyEl,
    "Evidence limits / uncertainty",
    data.uncertainty_note,
  );
  confidenceEl.textContent = Number(data.confidence ?? 0).toFixed(3);
  finalReasonEl.textContent = data.final_reason || "-";
  resultPanel.classList.remove("hidden");
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtn.textContent = isLoading ? "Asking..." : "Ask";
}

function hideOutputs() {
  resultPanel.classList.add("hidden");
  applicabilityEl.classList.add("hidden");
  uncertaintyEl.classList.add("hidden");
}

function renderDetail(element, label, value) {
  const text = (value || "").trim();
  if (!text) {
    element.textContent = "";
    element.classList.add("hidden");
    return;
  }
  element.textContent = `${label}: ${text}`;
  element.classList.remove("hidden");
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}

function hideError() {
  errorBanner.textContent = "";
  errorBanner.classList.add("hidden");
}
