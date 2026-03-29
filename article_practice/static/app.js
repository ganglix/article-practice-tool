const samplePassage = `The museum guide gave a brief history of the building before the tour began.

After a few minutes, the group reached the oldest room, where an artist once kept a notebook and a lamp beside the window.`;

const sourceForm = document.querySelector("#source-form");
const sourceText = document.querySelector("#source-text");
const sourceError = document.querySelector("#source-error");
const sampleButton = document.querySelector("#sample-button");
const resetButton = document.querySelector("#reset-button");
const practicePanel = document.querySelector("#practice-panel");
const practiceMeta = document.querySelector("#practice-meta");
const exerciseSurface = document.querySelector("#exercise-surface");
const gradeButton = document.querySelector("#grade-button");
const resultsPanel = document.querySelector("#results-panel");
const resultsSummary = document.querySelector("#results-summary");
const scoreCard = document.querySelector("#score-card");
const mistakeList = document.querySelector("#mistake-list");
const originalText = document.querySelector("#original-text");
const blankTemplate = document.querySelector("#blank-template");

let currentExerciseId = null;
let blankInputs = [];

sampleButton.addEventListener("click", () => {
  sourceText.value = samplePassage;
  sourceError.textContent = "";
});

resetButton.addEventListener("click", () => {
  sourceText.value = "";
  sourceError.textContent = "";
  currentExerciseId = null;
  blankInputs = [];
  exerciseSurface.innerHTML = "";
  practicePanel.classList.add("hidden");
  resultsPanel.classList.add("hidden");
});

sourceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  sourceError.textContent = "";
  resultsPanel.classList.add("hidden");

  try {
    const payload = { text: sourceText.value };
    const response = await fetch("/api/exercises", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      sourceError.textContent = data.error || "Could not build the exercise.";
      return;
    }

    currentExerciseId = data.exercise_id;
    renderExercise(data.segments);
    practiceMeta.textContent = `${data.blank_count} article blanks ready. Fill them inline, then grade the result.`;
    practicePanel.classList.remove("hidden");
  } catch (error) {
    sourceError.textContent = "The local server did not respond.";
  }
});

gradeButton.addEventListener("click", async () => {
  if (!currentExerciseId) {
    return;
  }

  try {
    const answers = blankInputs.map((input) => input.value.trim());
    const response = await fetch("/api/grade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exercise_id: currentExerciseId, answers }),
    });
    const data = await response.json();

    if (!response.ok) {
      sourceError.textContent = data.error || "Could not grade the exercise.";
      return;
    }

    applyResults(data.results);
    renderResults(data);
  } catch (error) {
    sourceError.textContent = "The local server did not respond.";
  }
});

function renderExercise(segments) {
  exerciseSurface.innerHTML = "";
  blankInputs = [];
  let paragraph = createParagraph();

  for (const segment of segments) {
    if (segment.type === "text") {
      paragraph = appendTextSegment(paragraph, segment.content);
      continue;
    }

    const fragment = blankTemplate.content.cloneNode(true);
    const shell = fragment.querySelector(".blank-shell");
    const input = fragment.querySelector(".blank-input");
    const answer = fragment.querySelector(".blank-answer");
    input.dataset.index = String(segment.index);
    input.style.width = `${segment.width}ch`;
    input.addEventListener("input", () => {
      input.value = input.value.replace(/[^A-Za-z]/g, "").slice(0, 3).toLowerCase();
      shell.classList.remove("is-correct", "is-incorrect");
      answer.textContent = "";
    });
    blankInputs.push(input);
    paragraph.append(fragment);
  }

  commitParagraph(paragraph);

  if (blankInputs.length > 0) {
    blankInputs[0].focus();
  }
}

function appendTextSegment(paragraph, text) {
  const chunks = text.split("\n\n");

  chunks.forEach((chunk, index) => {
    if (chunk) {
      paragraph.append(document.createTextNode(chunk));
    }

    if (index < chunks.length - 1) {
      commitParagraph(paragraph);
      paragraph = createParagraph();
    }
  });

  return paragraph;
}

function createParagraph() {
  const paragraph = document.createElement("p");
  paragraph.className = "exercise-paragraph";
  return paragraph;
}

function commitParagraph(paragraph) {
  if (paragraph.childNodes.length === 0) {
    return;
  }

  exerciseSurface.append(paragraph);
}

function applyResults(results) {
  for (const result of results) {
    const input = blankInputs[result.index];
    const shell = input.closest(".blank-shell");
    const answer = shell.querySelector(".blank-answer");
    shell.classList.toggle("is-correct", result.correct);
    shell.classList.toggle("is-incorrect", !result.correct);
    answer.textContent = result.correct ? "" : result.expected;
  }
}

function renderResults(data) {
  resultsSummary.textContent = `${data.correct_count} of ${data.total_count} correct. ${data.comment}`;
  scoreCard.innerHTML = "";
  mistakeList.innerHTML = "";

  const number = document.createElement("div");
  number.className = "score-number";
  number.textContent = `${data.score}%`;
  const copy = document.createElement("p");
  copy.className = "mistake-copy";
  copy.textContent = data.comment;
  scoreCard.append(number, copy);

  if (data.mistakes.length === 0) {
    const item = document.createElement("div");
    item.className = "mistake-item";
    item.innerHTML = `
      <p class="mistake-title">No misses</p>
      <p class="mistake-copy">The passage is fully restored.</p>
    `;
    mistakeList.append(item);
  } else {
    for (const mistake of data.mistakes) {
      const item = document.createElement("div");
      item.className = "mistake-item";
      item.innerHTML = `
        <p class="mistake-title">Blank ${mistake.index + 1}: expected "${mistake.expected}"</p>
        <p class="mistake-copy">You entered "${mistake.actual}". Context: ${mistake.context}</p>
      `;
      mistakeList.append(item);
    }
  }

  originalText.textContent = data.original_text;
  resultsPanel.classList.remove("hidden");
  resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}
