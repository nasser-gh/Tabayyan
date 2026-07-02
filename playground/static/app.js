"use strict";
(function () {
  const $ = (id) => document.getElementById(id);
  const SAMPLES = JSON.parse($("samples").textContent || "{}");
  let lastScan = null;

  // ---- theme ----
  const root = document.documentElement;
  $("theme-toggle").addEventListener("click", () => {
    const cur = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", cur);
    localStorage.setItem("tby-theme", cur);
  });

  // ---- editor helpers ----
  const input = $("input");
  const updateCount = () => { $("charcount").textContent = input.value.length.toLocaleString() + " chars"; };
  input.addEventListener("input", updateCount);
  $("clear").addEventListener("click", () => { input.value = ""; updateCount(); input.focus(); });

  // samples
  document.querySelectorAll(".sample-btn").forEach((b) => {
    b.addEventListener("click", () => {
      const s = SAMPLES[b.dataset.key];
      if (s) { input.value = s.text; updateCount(); }
    });
  });

  // file upload + drag/drop (read client-side, never uploaded)
  const readFile = (file) => {
    if (!file) return;
    if (!/\.txt$/i.test(file.name) && file.type !== "text/plain") { showError("Only .txt files are supported."); return; }
    const r = new FileReader();
    r.onload = () => { input.value = String(r.result || ""); updateCount(); };
    r.readAsText(file);
  };
  $("file").addEventListener("change", (e) => readFile(e.target.files[0]));
  const drop = $("drop");
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("drag"); }));
  drop.addEventListener("drop", (e) => readFile(e.dataTransfer.files[0]));

  // ---- tabs ----
  document.querySelectorAll(".tab").forEach((t) => {
    t.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("is-active"));
      t.classList.add("is-active");
      ["results", "json", "redaction"].forEach((n) => { $("tab-" + n).hidden = (n !== t.dataset.tab); });
    });
  });
  const showTab = (name) => document.querySelector('.tab[data-tab="' + name + '"]').click();

  // ---- error ----
  function showError(msg) { const e = $("error"); e.textContent = msg; e.hidden = false; }
  function clearError() { $("error").hidden = true; }

  async function post(url, body) {
    const res = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || "Request failed");
    return data;
  }

  const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  // ---- scan ----
  $("scan").addEventListener("click", async () => {
    clearError();
    try {
      const data = await post("/api/scan", { text: input.value });
      lastScan = data;
      // stats
      $("stats").hidden = false;
      $("s-total").textContent = data.count; $("s-high").textContent = data.high;
      $("s-med").textContent = data.medium; $("s-low").textContent = data.low;
      $("s-ms").textContent = data.ms; $("s-chars").textContent = data.chars.toLocaleString();
      $("s-det").textContent = data.detectors;
      // highlight
      $("empty").hidden = true;
      const hl = $("highlight"); hl.hidden = false;
      hl.innerHTML = data.highlighted || "<span class='tag'>(no text)</span>";
      // cards
      $("cards").innerHTML = data.matches.length
        ? data.matches.map(cardHTML).join("")
        : "<div class='empty'>No PII detected.</div>";
      // json
      $("json").textContent = JSON.stringify(data.matches, null, 2);
      showTab("results");
    } catch (e) { showError(e.message); }
  });

  function cardHTML(m) {
    return `<div class="card">
      <div class="c-top"><span class="c-name">${esc(m.detector)}</span>
        <span class="tagpill conf-${m.confidence}">${m.confidence.toUpperCase()}</span></div>
      <div class="c-val">${esc(m.value)}</div>
      <div class="c-meta">
        <span class="tagpill">${esc(m.category_label)}</span>
        <span class="tagpill">offset ${m.start}–${m.end}</span>
      </div>
    </div>`;
  }

  // ---- redact ----
  $("redact").addEventListener("click", async () => {
    clearError();
    try {
      const mode = $("mode").value;
      const data = await post("/api/redact", { text: input.value, mode });
      $("r-original").textContent = data.original;
      $("r-redacted").textContent = data.redacted;
      $("r-mode").textContent = data.mode;
      showTab("redaction");
    } catch (e) { showError(e.message); }
  });

  // ---- copy / download ----
  const copy = (text) => navigator.clipboard && navigator.clipboard.writeText(text);
  const download = (text, name) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    a.download = name; a.click(); URL.revokeObjectURL(a.href);
  };
  $("copy-json").addEventListener("click", () => copy($("json").textContent));
  $("dl-json").addEventListener("click", () => download($("json").textContent, "tabayyan-detections.json"));
  $("copy-red").addEventListener("click", () => copy($("r-redacted").textContent));
  $("dl-red").addEventListener("click", () => download($("r-redacted").textContent, "tabayyan-redacted.txt"));

  updateCount();
})();
