// ---------- MATH ENGINE ----------

let angleMode = "DEG"; // "DEG" or "RAD"
let memoryValue = 0;
let lastAnswer = 0;
let expression = "";

const toRad = (x) => (angleMode === "DEG" ? (x * Math.PI) / 180 : x);
const fromRad = (x) => (angleMode === "DEG" ? (x * 180) / Math.PI : x);

const calcMath = math.create(math.all);
calcMath.import({
  sin: (x) => Math.sin(toRad(x)),
  cos: (x) => Math.cos(toRad(x)),
  tan: (x) => Math.tan(toRad(x)),
  asin: (x) => fromRad(Math.asin(x)),
  acos: (x) => fromRad(Math.acos(x)),
  atan: (x) => fromRad(Math.atan(x)),
  log: (x) => Math.log10(x),
  ln: (x) => Math.log(x),
  nPr: (n, r) => calcMath.permutations(n, r),
  nCr: (n, r) => calcMath.combinations(n, r),
}, { override: true });

function toEvalString(displayExpr) {
  return displayExpr
    .replace(/×/g, "*")
    .replace(/÷/g, "/")
    .replace(/√\(/g, "sqrt(")
    .replace(/∛\(/g, "cbrt(")
    .replace(/π/g, "pi")
    .replace(/\bAns\b/g, String(lastAnswer));
}

function updateScreen(errorMessage) {
  document.getElementById("calcExpr").textContent = expression;
  document.getElementById("calcResult").textContent = errorMessage || "";
  document.getElementById("angleModeLabel").textContent = angleMode;
  document.getElementById("angleModeBtn").textContent = angleMode;
  document.getElementById("memoryIndicator").textContent = memoryValue !== 0 ? "M" : "";
}

function liveEvaluate() {
  if (!expression) {
    document.getElementById("calcResult").textContent = "0";
    return;
  }
  try {
    const result = calcMath.evaluate(toEvalString(expression));
    if (result === undefined) return;
    document.getElementById("calcResult").textContent = formatResult(result);
  } catch (err) {
    // Don't show an error while still typing - only on "="
  }
}

function formatResult(result) {
  if (typeof result === "number") {
    if (Number.isInteger(result)) return String(result);
    return String(parseFloat(result.toFixed(10)));
  }
  return calcMath.format(result, { precision: 10 });
}

// ---------- SCIENTIFIC PANEL TOGGLE ----------

document.getElementById("sciToggleBtn").addEventListener("click", () => {
  const panel = document.getElementById("sciPanel");
  const btn = document.getElementById("sciToggleBtn");
  panel.classList.toggle("open");
  btn.textContent = panel.classList.contains("open") ? "🔼 Hide scientific functions" : "🔬 Scientific functions";
});

// ---------- BUTTON HANDLING ----------

document.querySelectorAll("#calcButtons button").forEach((btn) => {
  btn.addEventListener("click", () => {
    const appendValue = btn.dataset.append;
    const action = btn.dataset.action;

    if (appendValue !== undefined) {
      expression += appendValue;
      updateScreen();
      liveEvaluate();
      return;
    }

    switch (action) {
      case "ac":
        expression = "";
        updateScreen();
        break;

      case "del":
        expression = expression.slice(0, -1);
        updateScreen();
        liveEvaluate();
        break;

      case "equals": {
        if (!expression) return;
        try {
          const result = calcMath.evaluate(toEvalString(expression));
          lastAnswer = typeof result === "number" ? result : 0;
          document.getElementById("calcResult").textContent = formatResult(result);
          expression = formatResult(result);
        } catch (err) {
          document.getElementById("calcResult").textContent = "Math ERROR";
        }
        break;
      }

      case "percent": {
        if (!expression) return;
        try {
          const result = calcMath.evaluate(toEvalString(expression));
          const percentValue = result / 100;
          expression = formatResult(percentValue);
          document.getElementById("calcResult").textContent = formatResult(percentValue);
          document.getElementById("calcExpr").textContent = expression;
        } catch (err) {
          document.getElementById("calcResult").textContent = "Math ERROR";
        }
        break;
      }

      case "toggleSign":
        if (expression.startsWith("-(") && expression.endsWith(")")) {
          expression = expression.slice(2, -1);
        } else if (expression) {
          expression = `-(${expression})`;
        }
        updateScreen();
        liveEvaluate();
        break;

      case "toggleAngle":
        angleMode = angleMode === "DEG" ? "RAD" : "DEG";
        updateScreen();
        liveEvaluate();
        break;

      case "mPlus":
        try {
          const result = calcMath.evaluate(toEvalString(expression || document.getElementById("calcResult").textContent));
          memoryValue += typeof result === "number" ? result : 0;
        } catch (err) { /* ignore */ }
        updateScreen();
        break;

      case "mMinus":
        try {
          const result = calcMath.evaluate(toEvalString(expression || document.getElementById("calcResult").textContent));
          memoryValue -= typeof result === "number" ? result : 0;
        } catch (err) { /* ignore */ }
        updateScreen();
        break;

      case "mr":
        expression += formatResult(memoryValue);
        updateScreen();
        liveEvaluate();
        break;

      case "mc":
        memoryValue = 0;
        updateScreen();
        break;
    }
  });
});

updateScreen();