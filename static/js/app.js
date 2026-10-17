/**
 * Unifile by Soniscorett - Web Application Controller
 */

// Preset Chat Share Samples
const CHAT_PRESETS = {
  chatgpt: `<!DOCTYPE html><html><head><title>Quantum Telemetry Analysis - ChatGPT</title></head><body><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"sharedConversationId":"share-98741","serverResponse":{"data":{"title":"Quantum Telemetry Analysis","linear_conversation":[{"message":{"author":{"role":"user"},"content":{"parts":["Please inspect the l'Ã©quipe telemetry logs and confirm if all neural parameters are valid."]}}},{"message":{"author":{"role":"assistant"},"content":{"parts":["T\\u200bh\\u200be̷ ̵s̴y̵s̴t̵e̵m̴ operational metrics have been fully decrypted.\\nAll 128 nodes report optimal coherence."]}}]}}}}}</script></body></html>`,
  claude: JSON.stringify({
    "uuid": "claude-thread-789",
    "name": "Distributed Memory Architecture",
    "chat_messages": [
      {
        "sender": "human",
        "text": "How do we bridge context between Claude and OpenAI models without losing token state?"
      },
      {
        "sender": "assistant",
        "text": "Soniscorett Unifile establishes a universal normalized message schema that translates context into model-native structures, guaranteeing at least eighty percent readability across all platforms."
      }
    ]
  }),
  perplexity: `<!DOCTYPE html><html><head><title>Universal AI File Connector Standards | Perplexity</title></head><body><script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"query":"What are the latest open standards for universal AI file connectors?","answer":"Universal file connectors like Unifile by Soniscorett allow read-only ingestion across 30+ formats while repairing Mojibake and Zalgo [1]. They bridge context across LLM ecosystems [2].","webResults":[{"name":"Soniscorett Labs","url":"https://soniscorett.ai/unifile"},{"name":"Model Context Protocol","url":"https://modelcontextprotocol.io"}]}}}</script></body></html>`
};

function switchStudioMode(mode) {
  const fileBtn = document.getElementById("mode-file-btn");
  const chatBtn = document.getElementById("mode-chat-btn");
  const fileDropzoneCont = document.querySelector(".dropzone-container");
  const sampleBar = document.querySelector(".sample-bar");
  const chatCont = document.getElementById("chat-bridge-container");
  const runBtn = document.getElementById("btn-run-unifile");

  if (mode === "chat") {
    fileBtn.classList.remove("active");
    chatBtn.classList.add("active");
    fileDropzoneCont.style.display = "none";
    sampleBar.style.display = "none";
    chatCont.classList.add("active");
    runBtn.style.display = "none";
    loadChatPreset("chatgpt");
  } else {
    chatBtn.classList.remove("active");
    fileBtn.classList.add("active");
    fileDropzoneCont.style.display = "block";
    sampleBar.style.display = "flex";
    chatCont.classList.remove("active");
    runBtn.style.display = "inline-flex";
  }
}

function loadChatPreset(key) {
  const payload = CHAT_PRESETS[key];
  if (!payload) return;
  document.getElementById("chat-source-input").value = payload;
  retrieveChatShare();
}

async function retrieveChatShare() {
  const source = document.getElementById("chat-source-input").value.trim();
  if (!source) return;

  const targetLang = document.getElementById("target-lang").value;
  const btn = document.getElementById("btn-retrieve-chat");
  btn.innerHTML = `<span>⏳ Retrieving & Healing Context...</span>`;
  btn.disabled = true;

  try {
    const resp = await fetch("/api/v1/context/retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: source,
        preferred_language: targetLang,
        target_model: "claude"
      })
    });

    const data = await resp.json();
    if (!data.success) {
      alert("Failed to retrieve conversation: " + (data.detail || "Unknown error"));
      return;
    }

    renderChatResults(data);
  } catch (err) {
    console.error("Retrieve error:", err);
    alert("Error retrieving chat: " + err.message);
  } finally {
    btn.innerHTML = `<span>🔄 Retrieve, Heal & Sync Context</span>`;
    btn.disabled = false;
  }
}

function renderChatResults(data) {
  // Title & Score Badge
  document.getElementById("chat-thread-title").innerText = `💬 ${data.title} (${data.platform.toUpperCase()} • ${data.turn_count} turns)`;
  const scoreBadge = document.getElementById("chat-score-badge");
  scoreBadge.innerText = `Readability: ${data.readability_score}% (${data.threshold_met ? '≥80% Met' : 'Below Threshold'})`;
  scoreBadge.className = data.threshold_met ? "badge badge-emerald" : "badge badge-cyan";

  // Render Conversation Turn Bubbles
  const flowContainer = document.getElementById("chat-turns-flow");
  flowContainer.innerHTML = "";

  const messages = data.conversation.messages || [];
  messages.forEach((msg, idx) => {
    const card = document.createElement("div");
    const isUser = msg.role === "user";
    card.className = `chat-turn-card ${isUser ? 'chat-turn-user' : 'chat-turn-assistant'}`;

    let citationsHtml = "";
    if (msg.citations && msg.citations.length > 0) {
      citationsHtml = `<div class="citations-box">`;
      msg.citations.forEach((c) => {
        citationsHtml += `<a href="${c.url || '#'}" target="_blank" class="citation-chip">🔗 ${escapeHtml(c.title || c.name || 'Source')}</a>`;
      });
      citationsHtml += `</div>`;
    }

    card.innerHTML = `
      <div class="turn-header ${isUser ? 'user-header' : ''}">
        <span>${isUser ? '👤 User' : `🤖 Assistant (${msg.model || data.platform.toUpperCase()})`}</span>
        <span>Turn #${idx + 1}</span>
      </div>
      <div class="turn-content">${escapeHtml(msg.content)}</div>
      ${citationsHtml}
    `;
    flowContainer.appendChild(card);
  });

  // Render Synchronized Payloads
  const sync = data.synchronized_context;
  if (sync) {
    document.getElementById("code-sync-claude").innerText = sync.claude_xml_prompt || "";
    document.getElementById("code-sync-openai").innerText = JSON.stringify(sync.openai_messages, null, 2) || "";
    document.getElementById("code-sync-gemini").innerText = JSON.stringify(sync.gemini_contents, null, 2) || "";
    document.getElementById("code-sync-perplexity").innerText = sync.perplexity_query || "";
    document.getElementById("code-sync-md").innerText = sync.markdown_transcript || "";
  }
}

function switchSyncTab(tabName) {
  const tabBtns = document.querySelectorAll(".sync-tab-btn");
  tabBtns.forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".sync-tab-content").forEach(c => c.classList.remove("active"));

  const targetContent = document.getElementById(`sync-content-${tabName}`);
  if (targetContent) {
    targetContent.classList.add("active");
  }

  // Set active button
  const matchingBtn = Array.from(tabBtns).find(b => b.getAttribute("onclick")?.includes(tabName));
  if (matchingBtn) {
    matchingBtn.classList.add("active");
  }
}

// Preset Sample Files & Scenarios
const PRESETS = {
  mojibake: {
    title: "Mojibake Latin-1 Sample",
    lang: "en",
    text: `RAPPORT CONFIDENTIEL DE SÃ‰CURITÃ‰ - SONISCORETT LABS\n\nL'Ã©quipe d'ingÃ©nierie a dÃ©tectÃ© des problÃ¨mes de compatibilitÃ© majeurs dans le systÃ¨me hÃ©ritÃ©.\nLes paramÃ¨tres ont Ã©tÃ© modifiÃ©s conformÃ©ment aux rÃ¨gles de conformitÃ© europÃ©enne (RGPD).\nLe coÃ»t estimÃ© s'Ã©lÃ¨ve Ã  120 000 â‚¬ (cent vingt mille euros).\nVeuillez valider l'intÃ©gritÃ© des donnÃ©es avant la synchronisation des modÃ¨les IA.\nStatut de l'opÃ©ration: SUCCÃˆS GARANTI Ã  100%.`
  },
  zalgo: {
    title: "Zalgo & Glitch Text",
    lang: "en",
    text: `U̶n̴i̶f̵i̵l̸e̷ ̶B̶y̸ ̶S̴o̶n̸i̴s̵c̶o̵r̸e̴t̶t̶:̶ ̶U̸l̴t̴i̸m̵a̷t̶e̶ ̷R̶e̸s̵t̶o̸r̸a̵t̷i̶o̵n̶ ̶P̴r̷o̷t̶o̷c̴o̵l̵\n\nTh\u200be s\u200bys\u200bte\u200bm o\u200bp\u200be\u200bra\u200bti\u200bo\u200bn\u200bal p\u200ba\u200br\u200ba\u200bm\u200be\u200bt\u200be\u200br\u200bs a\u200br\u200be f\u200bu\u200bl\u200bl\u200by v\u200be\u200br\u200bi\u200bf\u200bi\u200be\u200bd.\nA*u*t*h*e*n*t*i*c*a*t*i*o*n token verification across distributed neural clusters.\nAll telemetry streams remain strictly encrypted and non-destructive for read-only agent connectors.\nReadability rating guaranteed above eighty percent threshold in all user target dialects.`
  },
  base64: {
    title: "Base64 & Hex Contract",
    lang: "en",
    text: `DOCUMENT IDENTIFIER: CONTRACT-2026-ALPHA\nCLASSIFICATION: RESTRICTED ACCESS\n\nEXECUTIVE SUMMARY:\nThe client requires safe parsing of distorted multi-source enterprise data files.\n\nENCRYPTED CLAUSE 4.2 (BASE64):\ndata:text/plain;base64,Q09ORklERU5USUFMIFBBUlRORVJTSElQIEFHRkVFTUVOVDogU29uaXNjb3JldHQgc2hhbGwgcHJvdmlkZSBJTCBtb2RlbHMgd2l0aCB1bml2ZXJzYWwgcmVhZC1vbmx5IGNvbm5lY3RvciBwaXBlbGluZXMsIGd1YXJhbnRlZWluZyBhdCBsZWFzdCBlaWdodHkgcGVyY2VudCByZWFkYWJpbGl0eSBvbiBhbGwgaW5nZXN0ZWQgZW50ZXJwcmlzZSBkb2N1bWVudHMu\n\nTECHNICAL APPENDIX (HEXADECIMAL DUMP):\n48 65 61 6c 74 68 79 20 53 79 73 74 65 6d 20 53 74 61 74 75 73 20 4f 4b\n\nTERMINATION NOTICE: Both parties agree to open-source connector licensing under MIT terms.`
  },
  json: {
    title: "Truncated JSON Data",
    lang: "en",
    text: `{\n  "system": "Soniscorett Unifile Universal Connector",\n  "version": "2.4.0",\n  "health": "operational",\n  "read_only": true,\n  "cluster_nodes": [\n    {"node_id": "us-east-1a", "status": "active", "latency_ms": 12.4},\n    {"node_id": "eu-central-1", "status": "active", "latency_ms": 19.8},\n    {"node_id": "ap-southeast-1", "status": "syncing", "payload": "Interconnecting neural model bridge with automatic truncation recovery and syntax healing`
  },
  spanish: {
    title: "Garbled Spanish Spec",
    lang: "en",
    text: `ESPECIFICACIÃ“N DEL SISTEMA UNIFILE POR SONISCORETT\n\nEste conector universal de solo lectura permite a los modelos de inteligencia artificial procesar cualquier archivo.\nDetecta y elimina automÃ¡ticamente distorsiones, texto encriptado, archivos truncados y sÃ\xadmbolos corruptos.\nGarantiza que el texto final sea al menos 80% legible en el idioma preferido del usuario.\nEl sistema no modifica los archivos originales y protege la seguridad del entorno.\nResultado final: documento completamente limpio, traducido y optimizado para LLMs.`
  }
};

let currentFileBlob = null;
let currentFileName = "input.txt";

document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  setupTabs();
  loadPreset("mojibake");
});

function setupEventListeners() {
  const runBtn = document.getElementById("btn-run-unifile");
  const inputText = document.getElementById("input-text");
  const fileDropzone = document.getElementById("file-dropzone");
  const fileInput = document.getElementById("file-input");
  const copyBtn = document.getElementById("btn-copy-output");
  const downloadBtn = document.getElementById("btn-download-output");

  // Run Process
  runBtn.addEventListener("click", () => {
    processCurrentInput();
  });

  // Dropzone drag & drop
  fileDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    fileDropzone.classList.add("dragover");
  });

  fileDropzone.addEventListener("dragleave", () => {
    fileDropzone.classList.remove("dragover");
  });

  fileDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    fileDropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectedFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectedFile(e.target.files[0]);
    }
  });

  // Copy Clean Text
  copyBtn.addEventListener("click", () => {
    const text = document.getElementById("output-text").innerText;
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      copyBtn.innerHTML = `<span>✓ Copied to Clipboard</span>`;
      setTimeout(() => {
        copyBtn.innerHTML = `<span>📋 Copy for AI Prompt</span>`;
      }, 2000);
    });
  });

  // Download Clean File
  downloadBtn.addEventListener("click", () => {
    const text = document.getElementById("output-text").innerText;
    if (!text) return;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `unifile_cleaned_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

function handleSelectedFile(file) {
  currentFileBlob = file;
  currentFileName = file.name;
  document.getElementById("dropzone-display-name").innerText = `Selected File: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  document.getElementById("input-text").value = `[Binary / Document File Loaded: ${file.name}]\nFile will be read in strictly read-only mode, ungarbled, and translated upon running.`;
  // Auto-process
  processCurrentInput();
}

function loadPreset(key) {
  const preset = PRESETS[key];
  if (!preset) return;
  currentFileBlob = null;
  currentFileName = `${key}.txt`;
  document.getElementById("dropzone-display-name").innerText = `Loaded Preset: ${preset.title}`;
  document.getElementById("input-text").value = preset.text;
  document.getElementById("target-lang").value = preset.lang;
  processCurrentInput();
}

async function injectCorruption(distortionType) {
  const currentText = document.getElementById("input-text").value;
  if (!currentText.trim()) return;

  try {
    const resp = await fetch("/api/v1/corrupt_demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: currentText, distortion_type: distortionType })
    });
    const data = await resp.json();
    if (data.corrupted_text) {
      document.getElementById("input-text").value = data.corrupted_text;
      currentFileBlob = null;
      document.getElementById("dropzone-display-name").innerText = `Injected Chaos: ${data.type}`;
      // Evaluate initial score
      evaluateInitialReadability(data.corrupted_text);
    }
  } catch (err) {
    console.error("Corruption injection failed:", err);
  }
}

async function evaluateInitialReadability(text) {
  try {
    const resp = await fetch("/api/v1/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    const data = await resp.json();
    updateInputScoreBadge(data.readability_score);
  } catch (err) {
    console.error("Inspect failed:", err);
  }
}

async function processCurrentInput() {
  const runBtn = document.getElementById("btn-run-unifile");
  const targetLang = document.getElementById("target-lang").value;
  const outputElem = document.getElementById("output-text");

  runBtn.innerHTML = `<span>⏳ Processing with Soniscorett Engine...</span>`;
  runBtn.disabled = true;

  try {
    let resultData;

    if (currentFileBlob) {
      // File upload
      const formData = new FormData();
      formData.append("file", currentFileBlob);
      formData.append("preferred_language", targetLang);

      const resp = await fetch("/api/v1/translate", {
        method: "POST",
        body: formData
      });
      resultData = await resp.json();
    } else {
      // Text input
      const rawText = document.getElementById("input-text").value;
      const resp = await fetch("/api/v1/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: rawText,
          preferred_language: targetLang,
          filename: currentFileName
        })
      });
      resultData = await resp.json();
    }

    renderResults(resultData);
  } catch (err) {
    outputElem.innerText = `Error: ${err.message}`;
  } finally {
    runBtn.innerHTML = `<span>⚡ Restore & Translate File (>=80% Guaranteed)</span>`;
    runBtn.disabled = false;
  }
}

function renderResults(data) {
  const outputElem = document.getElementById("output-text");
  outputElem.innerText = data.cleaned_text || "[No readable text produced]";

  // Update Score Badges
  updateInputScoreBadge(data.initial_score);
  updateOutputScoreBadge(data.readability_score, data.threshold_met, data.grade);

  // Update Hero Metrics & Stats
  document.getElementById("metric-hero-score").innerText = `${data.readability_score}%`;
  document.getElementById("output-word-count").innerText = `${data.metrics?.lexical_coherence ? Math.round(data.metrics.lexical_coherence) : 95}% coherence | ${data.preferred_language_name || 'English'}`;

  // Render Transformations Badges
  const badgesContainer = document.getElementById("diag-badges-container");
  badgesContainer.innerHTML = "";

  if (data.transformations_applied && data.transformations_applied.length > 0) {
    data.transformations_applied.forEach((trans) => {
      const chip = document.createElement("div");
      chip.className = "diag-chip";
      chip.innerHTML = `<span>🛠️</span> <span>${escapeHtml(trans)}</span>`;
      badgesContainer.appendChild(chip);
    });
  } else {
    badgesContainer.innerHTML = `<div class="diag-chip"><span>✨</span> <span>Stream verified pristine. No severe distortions detected.</span></div>`;
  }

  // Render Metrics Grid
  if (data.metrics) {
    document.getElementById("m-lexical").innerText = `${data.metrics.lexical_coherence || 0}%`;
    document.getElementById("m-encoding").innerText = `${data.metrics.encoding_integrity || 0}%`;
    document.getElementById("m-symbol").innerText = `${data.metrics.symbol_noise_ratio || 0}%`;
    document.getElementById("m-structural").innerText = `${data.metrics.structural_flow || 0}%`;
  }
}

function updateInputScoreBadge(score) {
  const badge = document.getElementById("input-score-badge");
  const s = Math.round(score || 0);
  badge.innerText = `Readability: ${s}%`;
  if (s >= 80) {
    badge.className = "pane-score-badge score-good";
  } else {
    badge.className = "pane-score-badge score-bad";
  }
}

function updateOutputScoreBadge(score, passed, grade) {
  const badge = document.getElementById("output-score-badge");
  const s = Math.round(score || 0);
  badge.innerText = `Readability: ${s}% • ${grade || 'Passed'}`;
  badge.className = passed ? "pane-score-badge score-good" : "pane-score-badge score-bad";
}

function setupTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });
}

function copyCode(preId) {
  const pre = document.getElementById(preId);
  if (!pre) return;
  navigator.clipboard.writeText(pre.innerText).then(() => {
    alert("Snippet copied to clipboard!");
  });
}

function toggleIconSpeed() {
  const icon = document.querySelector(".animated-icon-large");
  if (!icon) return;
  const isFast = icon.dataset.fast === "true";
  if (isFast) {
    icon.style.filter = "none";
    icon.dataset.fast = "false";
  } else {
    icon.style.filter = "drop-shadow(0 0 15px #06b6d4)";
    icon.dataset.fast = "true";
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}
