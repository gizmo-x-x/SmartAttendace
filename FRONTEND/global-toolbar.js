// global-toolbar.js
// Include this on any page (right before </body>) to get:
// 1. A persistent digital clock + date bar fixed to the top
// 2. A floating calculator icon (bottom-right) for quick access from anywhere

(function () {
  // ---------- INJECT STYLES ----------
  const style = document.createElement("style");
  style.textContent = `
    #globalTopBar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 10000;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #111;
      color: #eee;
      padding: 0.4rem 1rem;
      font-family: "Courier New", monospace;
      font-size: 0.85rem;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }
    #globalCalcIcon {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 10000;
      width: 54px;
      height: 54px;
      border-radius: 50%;
      background: #2e7d32;
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.5rem;
      text-decoration: none;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    #globalCalcIcon:hover {
      background: #1b5e20;
    }
    body.has-global-topbar {
      padding-top: 2.2rem;
    }
  `;
  document.head.appendChild(style);

  // ---------- TOP BAR (CLOCK + DATE) ----------
  const topBar = document.createElement("div");
  topBar.id = "globalTopBar";
  topBar.innerHTML = `<span id="globalDate"></span><span id="globalTime"></span>`;
  document.body.prepend(topBar);
  document.body.classList.add("has-global-topbar");

  function updateGlobalClock() {
    const now = new Date();
    document.getElementById("globalDate").textContent = now.toLocaleDateString(undefined, {
      weekday: "short", year: "numeric", month: "short", day: "numeric",
    });
    document.getElementById("globalTime").textContent = now.toLocaleTimeString();
  }
  updateGlobalClock();
  setInterval(updateGlobalClock, 1000);

  // ---------- FLOATING CALCULATOR ICON ----------
  // Don't show the icon while already on the calculator page itself
  const onCalculatorPage = window.location.pathname.toLowerCase().includes("calculator.html");
  if (!onCalculatorPage) {
    const calcIcon = document.createElement("a");
    calcIcon.id = "globalCalcIcon";
    calcIcon.href = "calculator.html";
    calcIcon.title = "Open Calculator";
    calcIcon.textContent = "🧮";
    document.body.appendChild(calcIcon);
  }
})();