/* ============================================================
   FarmConnect — Ask the Farm Expert (RAG assistant) chat UI.
   Vanilla JS, no dependencies. Sends each question to /api/ask,
   which translates → answers from the knowledge base (local model
   if one is running) → translates back to the chosen language.
   ============================================================ */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function mdInline(s) {
    s = escapeHtml(s);
    s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    return s;
  }
  // A deliberately tiny Markdown renderer — enough for the assistant's bold
  // labels, bullet lists and paragraphs, and safe (everything is escaped).
  function mdToHtml(md) {
    const lines = String(md || "").split(/\r?\n/);
    let html = "", inList = false;
    const closeList = () => { if (inList) { html += "</ul>"; inList = false; } };
    for (const raw of lines) {
      const line = raw.trim();
      if (!line) { closeList(); continue; }
      if (/^[-*]\s+/.test(line)) {
        if (!inList) { html += "<ul>"; inList = true; }
        html += "<li>" + mdInline(line.replace(/^[-*]\s+/, "")) + "</li>";
      } else if (/^#{1,4}\s+/.test(line)) {
        closeList();
        const lvl = Math.min(line.match(/^#+/)[0].length + 2, 6);
        html += `<h${lvl}>${mdInline(line.replace(/^#+\s+/, ""))}</h${lvl}>`;
      } else {
        closeList();
        html += "<p>" + mdInline(line) + "</p>";
      }
    }
    closeList();
    return html;
  }

  function initAssistant() {
    const scroll = $("#askScroll"), msgs = $("#askMessages"), form = $("#askForm"),
      input = $("#askInput"), welcome = $("#askWelcome"), modePill = $("#askMode");
    if (!form || !msgs) return;
    const endpoint = form.dataset.endpoint || "/api/ask";

    const currentLang = () => {
      try { return (window.FarmTranslator && window.FarmTranslator.current) || "en"; }
      catch (e) { return "en"; }
    };
    const scrollDown = () => { scroll.scrollTop = scroll.scrollHeight; };

    function addRow(mine, inner) {
      const row = document.createElement("div");
      row.className = "bubble-row " + (mine ? "mine" : "theirs");
      row.innerHTML = inner;
      msgs.appendChild(row);
      scrollDown();
      return row;
    }
    function userBubble(text) { addRow(true, `<div class="bubble">${escapeHtml(text)}</div>`); }
    function typingBubble() {
      return addRow(false, `<div class="bubble ai-bubble"><span class="ai-typing"><i></i><i></i><i></i></span></div>`);
    }
    function confidenceChip(data) {
      // Only show a confidence badge when the answer is grounded in sources.
      if (!data || !data.confidence_band || data.confidence_band === "none") return "";
      const band = data.confidence_band;
      const label = band === "high" ? "High confidence"
        : band === "medium" ? "Medium confidence"
        : "Low confidence";
      const icon = band === "high" ? "🟢" : band === "medium" ? "🟡" : "🟠";
      const pct = (typeof data.confidence === "number")
        ? ` (${Math.round(data.confidence * 100)}%)` : "";
      return `<span class="conf-chip conf-${band}" title="How well this answer matches the knowledge base">${icon} ${label}${pct}</span>`;
    }
    function aiBubble(data) {
      let src = "";
      if (data.sources && data.sources.length) {
        const conf = confidenceChip(data);
        src = `<div class="ai-sources">📚 ${data.sources
          .map((s) => `<span class="src-chip">${escapeHtml(s.title)}</span>`).join("")}${conf}</div>`;
      }
      addRow(false, `<div class="bubble ai-bubble"><div class="ai-answer">${mdToHtml(data.answer)}</div>${src}</div>`);
    }
    function setMode(data) {
      if (!modePill) return;
      modePill.textContent = data.used_llm ? "🤖 AI model"
        : data.mode === "price" ? "💰 Pricing guidance"
        : data.mode === "no_match" ? "🤝 Ask an officer"
        : "📚 Knowledge base";
    }

    function ask(question) {
      question = (question || "").trim();
      if (!question) return;
      if (welcome) welcome.style.display = "none";
      userBubble(question);
      input.value = "";
      if (!navigator.onLine) {
        addRow(false, `<div class="bubble ai-bubble">📶 You're offline. The Farm Expert needs a connection to answer. Please try again once you're back online — your question stays in this chat.</div>`);
        return;
      }
      const typing = typingBubble();
      fetch(endpoint, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, lang: currentLang() }),
      })
        .then((r) => r.json())
        .then((data) => {
          typing.remove();
          if (data && data.ok) { setMode(data); aiBubble(data); }
          else aiBubble({ answer: "Sorry — something went wrong. Please try asking again." });
        })
        .catch(() => {
          typing.remove();
          aiBubble({ answer: "⚠️ I couldn't reach the server just now. Please check your connection and try again." });
        });
    }

    form.addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); });
    $$(".suggest-card").forEach((c) => c.addEventListener("click", () => ask(c.dataset.q)));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initAssistant);
  else initAssistant();
})();
