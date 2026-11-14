const chapters = [
  {
    era: "Origins",
    title: "The Selection",
    line: "A child looks up. An adult looks back.",
    record: "Era documented",
    fiction: "Story dramatized",
    color: "#415e63"
  },
  {
    era: "The Beijing school years",
    title: "The School",
    line: "An outsider learns to read the room.",
    record: "Era under review",
    fiction: "School story dramatized",
    color: "#5f483c"
  },
  {
    era: "University · Hong Kong",
    title: "University Burning",
    line: "A city in motion. A biography with missing pages.",
    record: "History documented",
    fiction: "Character path questioned",
    color: "#71332e"
  },
  {
    era: "Graduate study · finance",
    title: "The Credential",
    line: "A credential opens a door. What happened next?",
    record: "Milestones sourced",
    fiction: "Private motives unknown",
    color: "#445c72"
  },
  {
    era: "Shanghai · capital · crypto",
    title: "Hexi",
    line: "Money, networks, and the first compute trail.",
    record: "Corporate era sourced",
    fiction: "Connections dramatized",
    color: "#6b4b2d"
  },
  {
    era: "Gaming · infrastructure",
    title: "The Compute Variable",
    line: "Servers become leverage. Compute becomes policy.",
    record: "Commercial record sourced",
    fiction: "Causation not established",
    color: "#244f62"
  },
  {
    era: "2023 — present",
    title: "The Affair",
    line: "Two trajectories meet. The unanswered question remains.",
    record: "Public timeline sourced",
    fiction: "Relationship frame dramatized",
    color: "#7a2823"
  }
];

const root = document.querySelector(".experience");
const buttons = [...document.querySelectorAll(".chapter")];
const frames = [...document.querySelectorAll(".frame")];
const number = document.querySelector("#season-number");
const era = document.querySelector("#season-era");
const title = document.querySelector("#season-title");
const line = document.querySelector("#season-line");
const record = document.querySelector("#evidence-record");
const fiction = document.querySelector("#evidence-fiction");
const mark = document.querySelector("#scene-mark");
let active = 0;
let touchStart = null;

function render(index, moveFocus = false) {
  active = (index + chapters.length) % chapters.length;
  const chapter = chapters[active];
  root.dataset.season = String(active);
  root.style.setProperty("--scene", chapter.color);
  frames.forEach((frame, i) => frame.classList.toggle("is-active", i === active));

  number.textContent = String(active + 1).padStart(2, "0");
  era.textContent = chapter.era;
  title.textContent = chapter.title;
  line.textContent = chapter.line;
  record.textContent = chapter.record;
  fiction.textContent = chapter.fiction;
  mark.textContent = ["I", "II", "III", "IV", "V", "VI", "VII"][active];

  buttons.forEach((button, i) => {
    const current = i === active;
    button.classList.toggle("is-active", current);
    if (current) button.setAttribute("aria-current", "step");
    else button.removeAttribute("aria-current");
  });

  root.classList.remove("is-changing");
  requestAnimationFrame(() => root.classList.add("is-changing"));
  if (moveFocus) buttons[active].focus({ preventScroll: true });
}

buttons.forEach(button => {
  button.addEventListener("click", () => render(Number(button.dataset.index)));
});

document.querySelector("#previous").addEventListener("click", () => render(active - 1));
document.querySelector("#next").addEventListener("click", () => render(active + 1));

document.addEventListener("keydown", event => {
  if (event.key === "ArrowRight" || event.key === "ArrowDown") render(active + 1, true);
  if (event.key === "ArrowLeft" || event.key === "ArrowUp") render(active - 1, true);
  if (/^[1-7]$/.test(event.key)) render(Number(event.key) - 1, true);
});

root.addEventListener("pointerdown", event => {
  if (event.pointerType === "mouse") return;
  touchStart = { x: event.clientX, y: event.clientY };
});

root.addEventListener("pointerup", event => {
  if (!touchStart || event.pointerType === "mouse") return;
  const dx = event.clientX - touchStart.x;
  const dy = event.clientY - touchStart.y;
  touchStart = null;
  if (Math.max(Math.abs(dx), Math.abs(dy)) < 44) return;
  if (Math.abs(dx) > Math.abs(dy)) render(active + (dx < 0 ? 1 : -1));
  else render(active + (dy < 0 ? 1 : -1));
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
}

render(0);
