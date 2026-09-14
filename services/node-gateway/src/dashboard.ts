/**
 * JARVIS Web Dashboard - Self-contained Mission Control UI for live preview.
 */

export function getDashboardHtml(): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>JARVIS — Autonomous AI Assistant Command Center</title>
  <style>
    :root {
      --bg-base: #070a12;
      --bg-surface: #0e1526;
      --bg-card: rgba(18, 28, 50, 0.7);
      --border-color: #1e2c4d;
      --border-bright: #00f0ff44;
      --primary: #00f0ff;
      --primary-glow: 0 0 15px rgba(0, 240, 255, 0.4);
      --success: #00ff88;
      --warning: #ffaa00;
      --danger: #ff3366;
      --text-main: #e2e8f0;
      --text-muted: #8899b5;
      --font-mono: 'Consolas', 'Courier New', monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(0, 240, 255, 0.05) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(0, 255, 136, 0.04) 0%, transparent 40%),
        linear-gradient(rgba(14, 21, 38, 0.2) 1px, transparent 1px),
        linear-gradient(90deg, rgba(14, 21, 38, 0.2) 1px, transparent 1px);
      background-size: 100% 100%, 100% 100%, 40px 40px, 40px 40px;
    }

    header {
      border-bottom: 1px solid var(--border-color);
      background: rgba(14, 21, 38, 0.85);
      backdrop-filter: blur(12px);
      padding: 16px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .arc-reactor {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      border: 2px solid var(--primary);
      box-shadow: var(--primary-glow);
      display: flex;
      align-items: center;
      justify-content: center;
      animation: pulse 2.5s infinite ease-in-out;
    }

    .arc-inner {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: var(--primary);
      box-shadow: 0 0 10px var(--primary);
    }

    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 0.9; }
      50% { transform: scale(1.1); opacity: 1; filter: drop-shadow(0 0 8px #00f0ff); }
    }

    .brand h1 {
      font-size: 1.4rem;
      font-weight: 800;
      letter-spacing: 3px;
      color: #fff;
    }

    .brand span {
      font-size: 0.75rem;
      letter-spacing: 1px;
      color: var(--primary);
      text-transform: uppercase;
      margin-left: 6px;
      padding: 2px 6px;
      border: 1px solid var(--border-bright);
      border-radius: 4px;
    }

    .status-bar {
      display: flex;
      align-items: center;
      gap: 20px;
      font-family: var(--font-mono);
      font-size: 0.85rem;
    }

    .status-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: rgba(0, 255, 136, 0.1);
      border: 1px solid rgba(0, 255, 136, 0.3);
      border-radius: 20px;
      color: var(--success);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
    }

    .container {
      max-width: 1440px;
      margin: 0 auto;
      padding: 32px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }

    .full-width {
      grid-column: 1 / -1;
    }

    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 24px;
      backdrop-filter: blur(8px);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      transition: border-color 0.2s;
    }

    .card:hover {
      border-color: var(--border-bright);
    }

    .card-title {
      font-size: 1.1rem;
      font-weight: 700;
      letter-spacing: 1px;
      margin-bottom: 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #fff;
      border-bottom: 1px solid rgba(255, 255, 255, 0.07);
      padding-bottom: 10px;
    }

    .card-title .tag {
      font-size: 0.75rem;
      font-family: var(--font-mono);
      color: var(--primary);
      font-weight: normal;
    }

    /* System Telemetry Grid */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
    }

    .metric-box {
      background: rgba(7, 10, 18, 0.6);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px;
    }

    .metric-label {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }

    .metric-value {
      font-size: 1.25rem;
      font-family: var(--font-mono);
      font-weight: 700;
      color: var(--primary);
    }

    /* Agents Grid */
    .agents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 14px;
    }

    .agent-card {
      background: rgba(7, 10, 18, 0.6);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px;
      transition: all 0.2s ease;
    }

    .agent-card:hover {
      border-color: var(--primary);
      transform: translateY(-2px);
    }

    .agent-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .agent-name {
      font-weight: 700;
      font-size: 0.95rem;
      color: #fff;
    }

    .agent-role {
      font-size: 0.75rem;
      color: var(--primary);
      font-family: var(--font-mono);
    }

    .agent-desc {
      font-size: 0.8rem;
      color: var(--text-muted);
      line-height: 1.35;
    }

    /* Mission Terminal */
    .terminal-container {
      display: flex;
      flex-direction: column;
      height: 480px;
    }

    .terminal-output {
      flex: 1;
      background: #04060a;
      border: 1px solid #141c2e;
      border-radius: 8px;
      padding: 16px;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      color: #94a3b8;
      overflow-y: auto;
      line-height: 1.5;
      margin-bottom: 16px;
    }

    .terminal-line { margin-bottom: 4px; }
    .term-info { color: var(--primary); }
    .term-success { color: var(--success); }
    .term-warn { color: var(--warning); }
    .term-dim { color: #475569; }

    .terminal-input-bar {
      display: flex;
      gap: 12px;
    }

    input[type="text"] {
      flex: 1;
      background: rgba(7, 10, 18, 0.9);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 12px 16px;
      color: #fff;
      font-family: var(--font-mono);
      font-size: 0.9rem;
      outline: none;
      transition: border-color 0.2s;
    }

    input[type="text"]:focus {
      border-color: var(--primary);
      box-shadow: var(--primary-glow);
    }

    button {
      background: linear-gradient(135deg, #00d2ff, #00f0ff);
      color: #040711;
      font-weight: 700;
      font-family: var(--font-sans);
      letter-spacing: 0.5px;
      border: none;
      border-radius: 6px;
      padding: 0 24px;
      cursor: pointer;
      transition: all 0.2s;
    }

    button:hover {
      filter: brightness(1.15);
      box-shadow: var(--primary-glow);
    }

    .quick-actions {
      display: flex;
      gap: 8px;
      margin-top: 10px;
      flex-wrap: wrap;
    }

    .quick-btn {
      background: rgba(14, 21, 38, 0.6);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      font-size: 0.75rem;
      font-family: var(--font-mono);
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
    }

    .quick-btn:hover {
      color: var(--primary);
      border-color: var(--primary);
      background: rgba(0, 240, 255, 0.05);
    }

    /* Tools Pill List */
    .tools-list {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .tool-tag {
      background: rgba(7, 10, 18, 0.7);
      border: 1px solid var(--border-color);
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .tool-tag span {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--primary);
    }

    footer {
      border-top: 1px solid var(--border-color);
      padding: 20px;
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
      font-family: var(--font-mono);
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="arc-reactor">
        <div class="arc-inner"></div>
      </div>
      <div>
        <h1>J.A.R.V.I.S. <span>v1.0 Hybrid</span></h1>
      </div>
    </div>
    <div class="status-bar">
      <div id="connectionPill" class="status-pill">
        <div id="statusDot" class="status-dot"></div>
        <span id="connectionStatus">CONNECTING...</span>
      </div>
    </div>
  </header>

  <div class="container">

    <!-- Top Telemetry Row -->
    <div class="card full-width">
      <div class="card-title">
        <span>CORE ARCHITECTURE & TELEMETRY</span>
        <span class="tag">PHASE 01 — 05 ACTIVE</span>
      </div>
      <div class="metrics-grid">
        <div class="metric-box">
          <div class="metric-label">Node Gateway</div>
          <div class="metric-value">127.0.0.1:3000</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Protocol Engine</div>
          <div class="metric-value">v1.0.0 JSON-IPC</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Multi-Agent Core</div>
          <div class="metric-value">10 Agents (DAG)</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">Office Sandbox</div>
          <div class="metric-value">DOCX / PDF / PPTX</div>
        </div>
      </div>
    </div>

    <!-- 10 Multi-Agents Row -->
    <div class="card full-width">
      <div class="card-title">
        <span>AUTONOMOUS MULTI-AGENT RUNTIME (PHASE 05)</span>
        <span class="tag">10 SPECIALIZED AGENTS</span>
      </div>
      <div class="agents-grid">
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">🧭 Planner</div>
            <div class="agent-role">DAG Builder</div>
          </div>
          <div class="agent-desc">Decomposes goals into acyclic task graphs with parallel waves.</div>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">🔍 Researcher</div>
            <div class="agent-role">Data Hunter</div>
          </div>
          <div class="agent-desc">Performs fact retrieval, web scraping, and domain analysis.</div>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">💡 Reasoning</div>
            <div class="agent-role">Logic Core</div>
          </div>
          <div class="agent-desc">Executes complex causal inference and strategic reasoning.</div>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">💻 Coding</div>
            <div class="agent-role">Developer</div>
          </div>
          <div class="agent-desc">Writes production-grade software and creates document artifacts.</div>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">🛡️ Security</div>
            <div class="agent-role">Guard</div>
          </div>
          <div class="agent-desc">Audits code, verifies sandbox boundaries, and enforces safety.</div>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">🧪 Testing</div>
            <div class="agent-role">QA Engine</div>
          </div>
          <div class="agent-desc">Designs and runs unit, integration, and regression suites.</div>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">📝 Review</div>
            <div class="agent-role">Auditor</div>
          </div>
          <div class="agent-desc">Enforces Clean Code, SOLID principles, and quality gates.</div>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">🔬 Verifier</div>
            <div class="agent-role">Anti-Hallucination</div>
          </div>
          <div class="agent-desc">Inspects physical file bytes on disk to confirm real output.</div>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">🔄 Recovery</div>
            <div class="agent-role">Healer</div>
          </div>
          <div class="agent-desc">Applies bounded retries and dynamic replanning on failures.</div>
        </div>
        <div class="agent-card">
          <div class="agent-header">
            <div class="agent-name">📜 Synthesizer</div>
            <div class="agent-role">Executive Reporter</div>
          </div>
          <div class="agent-desc">Aggregates verified evidence into one unified final response.</div>
        </div>
      </div>
    </div>

    <!-- Interactive Mission Console -->
    <div class="card full-width">
      <div class="card-title">
        <span>LIVE MISSION CONTROL & WEBSOCKET CONSOLE</span>
        <span class="tag">REAL-TIME BIDIRECTIONAL IPC</span>
      </div>
      <div class="terminal-container">
        <div id="terminalOutput" class="terminal-output">
          <div class="terminal-line term-dim">[SYSTEM INITIALIZING] Loading JARVIS Hybrid Kernel...</div>
          <div class="terminal-line term-info">[SYSTEM] Connected to JARVIS Protocol v1.0.0 WebSocket Interface.</div>
          <div class="terminal-line term-success">[READY] 10 Autonomous Agents, Tool Sandbox, and AI Router ready for missions.</div>
        </div>
        <div class="terminal-input-bar">
          <input type="text" id="commandInput" placeholder="Enter autonomous agent mission (e.g., 'Generate executive architecture briefing')..." />
          <button id="sendBtn">DISPATCH GOAL</button>
        </div>
        <div class="quick-actions">
          <span style="font-size: 0.75rem; color: var(--text-muted); align-self: center;">Quick Presets:</span>
          <button class="quick-btn" onclick="sendPreset('system.ping', { ping: true })">Ping Engine</button>
          <button class="quick-btn" onclick="sendPreset('agent.execute', { goal: 'Audit system security and export DOCX' })">Security Audit & DOCX</button>
          <button class="quick-btn" onclick="sendPreset('agent.execute', { goal: 'Decompose multi-agent research DAG' })">Research DAG Plan</button>
          <button class="quick-btn" onclick="sendPreset('tools.list', {})">Inspect Sandboxed Tools</button>
        </div>
      </div>
    </div>

    <!-- Sandboxed Tool Suite -->
    <div class="card full-width">
      <div class="card-title">
        <span>SANDBOXED TOOL REGISTRY & OFFICE GENERATION (PHASE 04)</span>
        <span class="tag">PATH TRAVERSAL PROTECTED</span>
      </div>
      <div class="tools-list">
        <div class="tool-tag">📄 <strong>generate_docx</strong> <span>[Office DOCX Engine]</span></div>
        <div class="tool-tag">📊 <strong>generate_xlsx</strong> <span>[Office Excel Engine]</span></div>
        <div class="tool-tag">📽️ <strong>generate_pptx</strong> <span>[Office Slides Engine]</span></div>
        <div class="tool-tag">📑 <strong>generate_pdf</strong> <span>[ReportLab PDF Engine]</span></div>
        <div class="tool-tag">🛡️ <strong>FileSystemSandbox</strong> <span>[chroot Jail: /workspace]</span></div>
        <div class="tool-tag">🔐 <strong>ToolPolicyEngine</strong> <span>[Risk Assessment Gate]</span></div>
      </div>
    </div>

  </div>

  <footer>
    JARVIS Autonomous AI Assistant Platform • Developed under Strict Software Engineering Standards
  </footer>

  <script>
    let ws = null;
    const term = document.getElementById('terminalOutput');
    const input = document.getElementById('commandInput');
    const sendBtn = document.getElementById('sendBtn');
    const connStatus = document.getElementById('connectionStatus');
    const connPill = document.getElementById('connectionPill');
    const statusDot = document.getElementById('statusDot');

    function log(msg, type = 'term-info') {
      const line = document.createElement('div');
      line.className = 'terminal-line ' + type;
      const ts = new Date().toLocaleTimeString();
      line.textContent = '[' + ts + '] ' + msg;
      term.appendChild(line);
      term.scrollTop = term.scrollHeight;
    }

    function connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = protocol + '//' + window.location.host + '/ws';

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        connStatus.textContent = 'ONLINE (WS 1.0)';
        connPill.style.borderColor = 'rgba(0, 255, 136, 0.4)';
        connPill.style.background = 'rgba(0, 255, 136, 0.1)';
        connPill.style.color = 'var(--success)';
        statusDot.style.background = 'var(--success)';
        statusDot.style.boxShadow = '0 0 8px var(--success)';
        log('WebSocket link established with JARVIS Gateway (' + wsUrl + ')', 'term-success');
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.success) {
            log('ACK [' + data.id + '] ' + (data.payload?.message || JSON.stringify(data.payload)), 'term-success');
          } else {
            log('ERROR [' + data.id + '] ' + (data.error?.message || 'Unknown error'), 'term-warn');
          }
        } catch(e) {
          log('RAW: ' + evt.data, 'term-dim');
        }
      };

      ws.onerror = (err) => {
        log('WebSocket error occurred.', 'term-warn');
      };

      ws.onclose = () => {
        connStatus.textContent = 'DISCONNECTED';
        connPill.style.borderColor = 'rgba(255, 51, 102, 0.4)';
        connPill.style.background = 'rgba(255, 51, 102, 0.1)';
        connPill.style.color = 'var(--danger)';
        statusDot.style.background = 'var(--danger)';
        statusDot.style.boxShadow = '0 0 8px var(--danger)';
        log('Gateway connection lost. Reconnecting in 3 seconds...', 'term-warn');
        setTimeout(connectWebSocket, 3000);
      };
    }

    function dispatchCommand(type, payload) {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        log('Cannot send: WebSocket is not open.', 'term-warn');
        return;
      }

      const reqId = 'req-' + Math.random().toString(36).substring(2, 9);
      const message = {
        id: reqId,
        type: type,
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        payload: payload
      };

      log('DISPATCH [' + type + '] Payload: ' + JSON.stringify(payload), 'term-info');
      ws.send(JSON.stringify(message));
    }

    function sendPreset(type, payload) {
      dispatchCommand(type, payload);
    }

    sendBtn.onclick = () => {
      const text = input.value.trim();
      if (!text) return;
      dispatchCommand('agent.execute', { goal: text });
      input.value = '';
    };

    input.onkeydown = (e) => {
      if (e.key === 'Enter') {
        sendBtn.click();
      }
    };

    window.onload = connectWebSocket;
  </script>
</body>
</html>`;
}
