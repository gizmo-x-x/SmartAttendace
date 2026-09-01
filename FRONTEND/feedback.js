fetch("https://smartattendace.onrender.com/public-config")
  .then(r => r.json())
  .then(config => {
    if (!config.whatsapp_number) return;
    const btn = document.createElement("a");
    btn.href = `https://wa.me/${config.whatsapp_number}`;
    btn.target = "_blank";
    btn.textContent = "Feedback / Help 💬";
    btn.style.cssText = "position:fixed;bottom:20px;right:20px;background:#25D366;color:white;padding:0.6rem 1rem;border-radius:999px;text-decoration:none;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.2);z-index:999;";
    document.body.appendChild(btn);
  });