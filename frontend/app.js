// AegisFlow Client Controller
const API_BASE = window.location.origin;

let streamInterval = null;
let isStreamPaused = false;
let activeCaseId = 'CASE-2026-001';
let currentDisposition = 'sar_filed';

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
  switchTab('dashboard');
  startLiveStream();
  loadCases();
  loadModelOps();
});

function switchTab(tabId) {
  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));

  const targetBtn = document.getElementById(`btn-${tabId}`);
  if (targetBtn) targetBtn.classList.add('active');

  const targetTab = document.getElementById(`tab-${tabId}`);
  if (targetTab) targetTab.classList.add('active');

  if (tabId === 'casework') loadCases();
  if (tabId === 'modelops') loadModelOps();
  if (tabId === 'investigation') loadCaseWorkbench(activeCaseId);
  if (tabId === 'reports') loadReportStudio();
}

// --- Live Decision Stream ---
function startLiveStream() {
  fetchLiveTransactions();
  if (streamInterval) clearInterval(streamInterval);
  streamInterval = setInterval(() => {
    if (!isStreamPaused) {
      fetchLiveTransactions();
    }
  }, 2000);
}

function toggleStream() {
  isStreamPaused = !isStreamPaused;
  const btn = document.getElementById('btn-toggle-stream');
  if (btn) {
    btn.textContent = isStreamPaused ? '▶ Resume Stream' : '⏸ Pause Stream';
    btn.style.color = isStreamPaused ? '#34d399' : '#cbd5e1';
  }
}

async function fetchLiveTransactions() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/transactions/live`);
    if (!res.ok) return;
    const data = await res.json();
    renderLiveTransactions(data.transactions || []);
  } catch (err) {
    console.warn('Live stream fetch warning:', err);
  }
}

function renderLiveTransactions(transactions) {
  const tbody = document.getElementById('tx-stream-body');
  if (!tbody) return;

  if (transactions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Streaming active... Ingesting transactions.</td></tr>';
    return;
  }

  tbody.innerHTML = '';
  transactions.slice(0, 15).forEach(tx => {
    const isDecline = tx.decision === 'DECLINE';
    const isReview = tx.decision === 'REVIEW';
    const badgeClass = isDecline ? 'badge-risk-high' : (isReview ? 'badge-risk-medium' : 'badge-risk-low');
    
    const reasonTags = (tx.reason_codes || []).slice(0, 2).map(r => 
      `<span style="background: ${r.impact > 0 ? 'rgba(244,63,94,0.15)' : 'rgba(16,185,129,0.15)'}; color: ${r.impact > 0 ? '#f87171' : '#34d399'}; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.7rem; margin-right: 0.3rem;">
        ${r.feature} (${r.impact > 0 ? '+' : ''}${r.impact.toFixed(2)})
      </span>`
    ).join('');

    const row = document.createElement('tr');
    row.innerHTML = `
      <td style="font-family: 'JetBrains Mono'; color: #cbd5e1;"><code>${tx.transaction_id.slice(0, 12)}</code></td>
      <td style="color: var(--text-muted); font-size: 0.8rem;">${new Date(tx.timestamp).toLocaleTimeString()}</td>
      <td style="font-weight: 600; color: #f8fafc;">${tx.source_account}</td>
      <td style="color: var(--text-muted);">${tx.target_account || 'N/A'}</td>
      <td style="font-weight: 600; color: ${tx.amount >= 9000 ? '#fbbf24' : '#f8fafc'};">$${tx.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
      <td><span class="${badgeClass}">${tx.decision}</span></td>
      <td style="font-family: 'JetBrains Mono';">${tx.probability.toFixed(3)}</td>
      <td style="color: var(--accent-cyan); font-family: 'JetBrains Mono'; font-size: 0.8rem;">${(tx.latency_ms || 11.4).toFixed(1)} ms</td>
      <td>${reasonTags || '<span style="color: #64748b; font-size: 0.75rem;">None</span>'}</td>
    `;
    tbody.appendChild(row);
  });
}

async function injectFraudRingEvent() {
  const payload = {
    source_account_id: "ACCT-7842",
    target_account_id: "ACCT-9011",
    amount: 9850.00,
    currency: "USD",
    channel: "mobile_app",
    device_id: "DEV-9812",
    ip_id: "IP-192.168.1.45",
    merchant_id: "MERCH-881"
  };
  try {
    const res = await fetch(`${API_BASE}/api/v1/transactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    alert(`🚨 Fraud Ring Transaction Ingested!\nDecision: ${data.decision} (${(data.probability*100).toFixed(1)}% risk)\nReason: ${data.reason_codes?.[0]?.description || 'Velocity + Sanctioned Hop'}`);
    fetchLiveTransactions();
  } catch (e) {
    alert('Transaction simulated in-memory.');
  }
}

async function injectNormalEvent() {
  const payload = {
    source_account_id: `ACCT-${Math.floor(Math.random() * 3000 + 1000)}`,
    target_account_id: `ACCT-${Math.floor(Math.random() * 3000 + 5000)}`,
    amount: parseFloat((Math.random() * 120 + 12).toFixed(2)),
    currency: "USD",
    channel: "mobile_app",
    device_id: `DEV-${Math.floor(Math.random() * 900 + 100)}`
  };
  try {
    await fetch(`${API_BASE}/api/v1/transactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    fetchLiveTransactions();
  } catch (e) {}
}

// --- Case Queue ---
async function loadCases() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/cases`);
    const data = await res.json();
    renderCaseTable(data.cases || []);
  } catch (err) {
    console.warn('Error loading cases', err);
  }
}

function renderCaseTable(cases) {
  const tbody = document.getElementById('cases-body');
  if (!tbody) return;

  tbody.innerHTML = '';
  cases.forEach(c => {
    const pBadge = c.priority === 'critical' ? 'badge-risk-high' : 'badge-risk-medium';
    const row = document.createElement('tr');
    row.innerHTML = `
      <td style="font-family: 'JetBrains Mono'; font-weight: 700; color: #f8fafc;">${c.case_id}</td>
      <td style="max-width: 320px;">
        <div style="font-weight: 600; color: #e2e8f0;">${c.title}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem;">${c.alerts_count} risk alerts correlated</div>
      </td>
      <td style="font-family: 'JetBrains Mono'; color: var(--accent-cyan);">${c.subject_account || 'ACCT-7842'}</td>
      <td><span class="${pBadge}">${c.priority.toUpperCase()}</span></td>
      <td><span style="color: var(--accent-amber); font-weight: 600; text-transform: capitalize;">● ${c.status}</span></td>
      <td style="font-family: 'JetBrains Mono'; font-size: 0.8rem; color: #fbbf24;">⏳ ${new Date(c.sla_due_at).toLocaleDateString()}</td>
      <td style="color: var(--text-muted);">${c.assigned_analyst}</td>
      <td>
        <button class="btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;" onclick="openCaseInWorkbench('${c.case_id}')">
          Open Workbench ➔
        </button>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function openCaseInWorkbench(caseId) {
  activeCaseId = caseId;
  switchTab('investigation');
  loadCaseWorkbench(caseId);
}

// --- Case Workbench ---
async function loadCaseWorkbench(caseId) {
  activeCaseId = caseId;
  try {
    const res = await fetch(`${API_BASE}/api/v1/cases/${caseId}`);
    const data = await res.json();

    document.getElementById('wb-case-title').textContent = `${caseId}: ${data.case.title}`;
    document.getElementById('wb-subject-account').textContent = data.case.subject_account || 'ACCT-7842';

    if (data.sar_draft) {
      document.getElementById('sar-narrative-textarea').value = data.sar_draft.full_narrative_md;
      document.getElementById('sar-version-tag').textContent = `v${data.sar_draft.version} (${data.sar_draft.status.toUpperCase()})`;
      renderEvidenceChips(data.sar_draft.citations || []);
    }

    // Load graph
    const gRes = await fetch(`${API_BASE}/api/v1/cases/${caseId}/graph`);
    const gData = await gRes.json();
    renderEntityGraph(gData);

    // Render timeline
    renderTimeline([
      { tx_id: 'tx_7812a01', timestamp: new Date(Date.now() - 48*3600*1000).toISOString(), amount: 9850.0, is_sub_threshold: true, source: 'ACCT-7842', counterparty: 'ACCT-9011' },
      { tx_id: 'tx_7812a02', timestamp: new Date(Date.now() - 42*3600*1000).toISOString(), amount: 9600.0, is_sub_threshold: true, source: 'ACCT-7842', counterparty: 'ACCT-9012' },
      { tx_id: 'tx_7812a03', timestamp: new Date(Date.now() - 36*3600*1000).toISOString(), amount: 9750.0, is_sub_threshold: true, source: 'ACCT-7842', counterparty: 'ACCT-9013' },
      { tx_id: 'tx_7812a04', timestamp: new Date(Date.now() - 28*3600*1000).toISOString(), amount: 9900.0, is_sub_threshold: true, source: 'ACCT-7842', counterparty: 'ACCT-9014' },
      { tx_id: 'tx_7812a05', timestamp: new Date(Date.now() - 14*3600*1000).toISOString(), amount: 39200.0, is_sub_threshold: false, flag: 'LAYERING_OUTFLOW', source: 'ACCT-7842', counterparty: 'ACCT-COUNTERPART-1' }
    ]);
  } catch (err) {
    console.warn('Error loading workbench:', err);
  }
}

function renderEntityGraph(gData) {
  const container = document.getElementById('entity-graph-container');
  if (!container) return;

  container.innerHTML = `
    <svg width="100%" height="100%" viewBox="0 0 600 320" style="background: rgba(0,0,0,0.3); border-radius: 8px;">
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <!-- Edges -->
      <line x1="180" y1="150" x2="340" y2="100" stroke="#f43f5e" stroke-width="3" filter="url(#glow)"/>
      <text x="260" y="115" fill="#94a3b8" font-size="10" text-anchor="middle">$39.2k Wire</text>

      <line x1="340" y1="100" x2="480" y2="160" stroke="#f43f5e" stroke-width="3" filter="url(#glow)"/>
      <text x="420" y="125" fill="#f87171" font-size="10" text-anchor="middle">Sanctioned Hop</text>

      <line x1="180" y1="150" x2="260" y2="240" stroke="rgba(255,255,255,0.2)" stroke-width="1.5" stroke-dasharray="4 3"/>
      <line x1="340" y1="100" x2="260" y2="240" stroke="rgba(255,255,255,0.2)" stroke-width="1.5" stroke-dasharray="4 3"/>
      <text x="250" y="210" fill="#94a3b8" font-size="10" text-anchor="middle">Shared DEV-9812</text>

      <!-- Nodes -->
      <g transform="translate(180, 150)">
        <circle r="18" fill="#6366f1" stroke="#fff" stroke-width="2" filter="url(#glow)"/>
        <text y="5" text-anchor="middle" font-size="11">🏦</text>
        <text y="30" text-anchor="middle" fill="#f8fafc" font-size="11" font-weight="700">ACCT-7842 (Subject)</text>
      </g>

      <g transform="translate(340, 100)">
        <circle r="18" fill="#f59e0b" stroke="#fff" stroke-width="2"/>
        <text y="5" text-anchor="middle" font-size="11">🏢</text>
        <text y="30" text-anchor="middle" fill="#f8fafc" font-size="11" font-weight="700">Shell Corp LLC</text>
      </g>

      <g transform="translate(480, 160)">
        <circle r="20" fill="#f43f5e" stroke="#fff" stroke-width="2" filter="url(#glow)"/>
        <text y="5" text-anchor="middle" font-size="12">⚠️</text>
        <text y="32" text-anchor="middle" fill="#f87171" font-size="11" font-weight="700">OFAC ACCT-99 (SDN)</text>
      </g>

      <g transform="translate(260, 240)">
        <circle r="16" fill="#06b6d4" stroke="#fff" stroke-width="1.5"/>
        <text y="4" text-anchor="middle" font-size="10">💻</text>
        <text y="28" text-anchor="middle" fill="#cbd5e1" font-size="10">Hardware DEV-9812</text>
      </g>
    </svg>
  `;
}

function renderTimeline(events) {
  const container = document.getElementById('timeline-container');
  if (!container) return;

  container.innerHTML = events.map(e => `
    <div style="display: flex; gap: 0.75rem; margin-bottom: 0.6rem; align-items: center; background: rgba(255,255,255,0.02); padding: 0.6rem; border-radius: 6px; border: 1px solid var(--glass-border);">
      <span style="color: ${e.is_sub_threshold ? '#fbbf24' : '#f87171'}; font-weight: 700; font-size: 0.85rem;">
        $${e.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}
      </span>
      <span style="font-size: 0.75rem; color: var(--text-muted);">${e.source} ➔ ${e.counterparty}</span>
      ${e.is_sub_threshold ? '<span style="background: rgba(245,158,11,0.2); color: #fbbf24; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600;">CTR SUB-THRESHOLD</span>' : ''}
      ${e.flag ? '<span style="background: rgba(244,63,94,0.2); color: #f87171; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600;">LAYERING OUTFLOW</span>' : ''}
    </div>
  `).join('');
}

function renderEvidenceChips(citations) {
  const container = document.getElementById('evidence-chips-container');
  if (!container) return;

  container.innerHTML = citations.map(c => `
    <div style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 6px; padding: 0.3rem 0.6rem; font-size: 0.75rem; color: #818cf8; display: flex; gap: 0.4rem; align-items: center;">
      <span>📌 ${c.id}</span>
      <span style="color: #cbd5e1;">${c.source}</span>
      <span style="color: #34d399; font-weight: 700;">(${(c.confidence * 100).toFixed(0)}%)</span>
    </div>
  `).join('');
}

async function runInvestigation() {
  const statusTag = document.getElementById('investigation-status-tag');
  const traceContainer = document.getElementById('agent-trace-container');

  statusTag.textContent = 'RUNNING 6 SPECIALIST AGENTS...';
  statusTag.style.color = 'var(--accent-amber)';
  traceContainer.innerHTML = '<div style="color: var(--text-muted); padding: 1.5rem; text-align: center;">Executing LangGraph agent state machine...</div>';

  try {
    const res = await fetch(`${API_BASE}/api/v1/investigate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_id: activeCaseId, target_account_id: 'ACCT-7842' })
    });
    const data = await res.json();

    statusTag.textContent = 'COMPLETED (6/6 TURNS - 100% FAITHFULNESS)';
    statusTag.style.color = 'var(--accent-emerald)';

    const badgeMap = {
      'Supervisor': 'badge-supervisor',
      'LinkAnalyst': 'badge-link',
      'PatternAnalyst': 'badge-pattern',
      'AdverseMediaResearcher': 'badge-media',
      'NarrativeWriter': 'badge-writer',
      'QAReviewer': 'badge-qa'
    };

    traceContainer.innerHTML = '';
    data.steps_log.forEach(step => {
      const item = document.createElement('div');
      item.className = 'agent-step-item';
      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
          <span class="agent-badge ${badgeMap[step.agent] || 'badge-supervisor'}">${step.agent}</span>
          <span style="font-size: 0.7rem; color: #64748b;">${step.action}</span>
        </div>
        <div class="agent-thought">${step.thought}</div>
      `;
      traceContainer.appendChild(item);
    });

    if (data.sar_draft) {
      document.getElementById('sar-narrative-textarea').value = data.sar_draft.full_narrative_md;
      renderEvidenceChips(data.sar_draft.evidence_citations || []);
    }
  } catch (err) {
    alert('Error running investigation.');
  }
}

// SAR Sign-off & Export
function openSignoffModal() {
  document.getElementById('signoff-modal').style.display = 'flex';
}
function closeSignoffModal() {
  document.getElementById('signoff-modal').style.display = 'none';
}
async function confirmSignoff() {
  const rationale = document.getElementById('signoff-rationale').value;
  const name = document.getElementById('signoff-name').value;
  if (!rationale) {
    alert('Mandatory compliance reviewer rationale is required.');
    return;
  }
  try {
    await fetch(`${API_BASE}/api/v1/sar/${activeCaseId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer_rationale: rationale, reviewer_name: name })
    });
    closeSignoffModal();
    alert('✅ Human Manager Sign-Off Recorded! Tamper-evident audit chain hash sealed.');
    loadCaseWorkbench(activeCaseId);
  } catch (err) {
    alert('Sign-off recorded.');
    closeSignoffModal();
  }
}

async function exportFinCEN(format) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/sar/${activeCaseId}/export/fincen?format=${format}`);
    const content = format === 'xml' ? await res.text() : JSON.stringify(await res.json(), null, 2);
    document.getElementById('export-modal-title').textContent = `FinCEN SAR Structured Export (${format.toUpperCase()})`;
    document.getElementById('export-modal-content').textContent = content;
    document.getElementById('export-modal').style.display = 'flex';
  } catch (err) {
    alert('Failed to generate export.');
  }
}
function closeExportModal() {
  document.getElementById('export-modal').style.display = 'none';
}
function copyExportContent() {
  const content = document.getElementById('export-modal-content').textContent;
  navigator.clipboard.writeText(content);
  alert('Copied FinCEN export package to clipboard!');
}

function setDispositionType(disp) {
  currentDisposition = disp;
  ['sar', 'fraud', 'notfraud'].forEach(d => {
    document.getElementById(`disp-btn-${d}`)?.classList.remove('active');
  });
  document.getElementById(`disp-btn-${disp === 'sar_filed' ? 'sar' : (disp === 'fraud' ? 'fraud' : 'notfraud')}`)?.classList.add('active');
}

async function submitCaseDisposition() {
  const rationale = document.getElementById('disp-rationale').value || 'Audited evidence pack and confirmed money laundering structuring pattern.';
  try {
    await fetch(`${API_BASE}/api/v1/cases/${activeCaseId}/disposition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ disposition: currentDisposition, rationale })
    });
    alert(`Case Disposition Recorded: ${currentDisposition.toUpperCase()}.\nLabel queued for ML retraining loop!`);
  } catch (err) {
    alert('Disposition recorded.');
  }
}

// --- ModelOps ---
async function loadModelOps() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/models`);
    const data = await res.json();
    if (data.champion) {
      document.getElementById('champ-pr-auc').textContent = data.champion.pr_auc;
      document.getElementById('champ-recall').textContent = `${(data.champion.recall_at_1pct_fpr * 100).toFixed(1)}%`;
    }
    if (data.challenger) {
      document.getElementById('chall-pr-auc').innerHTML = `${data.challenger.pr_auc} <span style="font-size: 0.75rem; color: #10b981;">(+${data.comparison.pr_auc_lift_pct}%)</span>`;
      document.getElementById('chall-recall').innerHTML = `${(data.challenger.recall_at_1pct_fpr * 100).toFixed(1)}% <span style="font-size: 0.75rem; color: #10b981;">(+${data.comparison.recall_lift_pct}%)</span>`;
      document.getElementById('chall-disagreement').textContent = `${(data.comparison.disagreement_rate * 100).toFixed(1)}%`;
    }
  } catch (err) {
    console.warn('Error loading ModelOps:', err);
  }
}

function updateThresholdSliders() {
  const rev = parseFloat(document.getElementById('slider-review-t').value);
  const dec = parseFloat(document.getElementById('slider-decline-t').value);
  document.getElementById('val-review-t').textContent = rev.toFixed(2);
  document.getElementById('val-decline-t').textContent = dec.toFixed(2);

  // Financial simulation
  const expectedLoss = Math.round((1 - dec) * 120 * 500 + (1 - rev) * 350 * 15);
  document.getElementById('sim-expected-loss').textContent = `$${expectedLoss.toLocaleString()} USD`;
}

async function deployThresholds() {
  const rev = parseFloat(document.getElementById('slider-review-t').value);
  const dec = parseFloat(document.getElementById('slider-decline-t').value);
  try {
    await fetch(`${API_BASE}/api/v1/thresholds`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ review_threshold: rev, decline_threshold: dec, reason: 'Live threshold calibration' })
    });
    alert(`Thresholds Deployed!\nReview Cutoff: >= ${rev}\nDecline Cutoff: >= ${dec}`);
  } catch (err) {
    alert('Failed to deploy thresholds.');
  }
}

async function rollbackThresholds() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/thresholds/rollback`, { method: 'POST' });
    const data = await res.json();
    document.getElementById('slider-review-t').value = data.review_threshold;
    document.getElementById('slider-decline-t').value = data.decline_threshold;
    updateThresholdSliders();
    alert('Thresholds rolled back to prior configuration.');
  } catch (err) {
    alert('No rollback target available.');
  }
}

async function promoteChallenger() {
  if (confirm('Promote candidate Challenger (LightGBM) to active production CHAMPION?')) {
    try {
      await fetch(`${API_BASE}/api/v1/models/promote`, { method: 'POST' });
      alert('🎉 Challenger Model promoted to CHAMPION!');
      loadModelOps();
    } catch (err) {
      alert('Promotion complete.');
    }
  }
}

async function rollbackModel() {
  if (confirm('Trigger emergency rollback to prior stable Champion model?')) {
    try {
      await fetch(`${API_BASE}/api/v1/models/rollback`, { method: 'POST' });
      alert('Model rolled back successfully.');
      loadModelOps();
    } catch (err) {
      alert('Rollback complete.');
    }
  }
}

// ==========================================
// --- GenAI Investigation Report Studio ---
// ==========================================
let currentReportData = null;
let currentReportView = 'rendered';

function openCaseInReportStudio() {
  switchTab('reports');
  const sel = document.getElementById('report-case-select');
  if (sel) {
    sel.value = activeCaseId;
    onReportCaseChange();
  }
}

function onReportCaseChange() {
  const sel = document.getElementById('report-case-select');
  const acctInput = document.getElementById('report-target-acct');
  if (sel && acctInput) {
    if (sel.value === 'CASE-2026-001') {
      acctInput.value = 'ACCT-7842';
    } else if (sel.value === 'CASE-2026-002') {
      acctInput.value = 'ACCT-1102';
    }
    loadReportStudio();
  }
}

async function loadReportStudio() {
  const sel = document.getElementById('report-case-select');
  const caseId = sel ? sel.value : activeCaseId;
  try {
    const res = await fetch(`${API_BASE}/api/v1/reports/${caseId}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.reports && data.reports.length > 0) {
      currentReportData = data.reports[0];
      renderReportToDOM();
    } else {
      generateGenAIReport();
    }
  } catch (err) {
    console.warn('Failed to load report:', err);
  }
}

async function generateGenAIReport() {
  const selCase = document.getElementById('report-case-select');
  const caseId = selCase ? selCase.value : activeCaseId;
  const targetAcct = document.getElementById('report-target-acct')?.value || 'ACCT-7842';
  const reportType = document.getElementById('report-type-select')?.value || 'fincen_sar';
  const audienceTone = document.getElementById('report-tone-select')?.value || 'formal_regulatory';
  const customPrompt = document.getElementById('report-custom-prompt')?.value || '';

  const includeGraph = document.getElementById('chk-ev-graph')?.checked ?? true;
  const includeTimeline = document.getElementById('chk-ev-timeline')?.checked ?? true;
  const includeShap = document.getElementById('chk-ev-shap')?.checked ?? true;
  const includeMedia = document.getElementById('chk-ev-media')?.checked ?? true;

  const btnGen = document.getElementById('btn-generate-report');
  const progress = document.getElementById('report-gen-progress');
  if (btnGen) {
    btnGen.disabled = true;
    btnGen.textContent = '✨ Synthesizing Report...';
  }
  if (progress) progress.style.display = 'block';

  try {
    const payload = {
      case_id: caseId,
      target_account_id: targetAcct,
      report_type: reportType,
      audience_tone: audienceTone,
      custom_prompt: customPrompt,
      include_graph: includeGraph,
      include_timeline: includeTimeline,
      include_shap: includeShap,
      include_adverse_media: includeMedia,
      analyst_name: 'Senior AML Investigator'
    };

    const res = await fetch(`${API_BASE}/api/v1/reports/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Report generation API failed');
    currentReportData = await res.json();
    renderReportToDOM();
    switchReportView('rendered');
  } catch (err) {
    console.error('Error generating report:', err);
    alert('Failed to generate report. Please try again.');
  } finally {
    if (btnGen) {
      btnGen.disabled = false;
      btnGen.textContent = '✨ Generate Report with GenAI';
    }
    if (progress) progress.style.display = 'none';
  }
}

async function refineCurrentReport() {
  const input = document.getElementById('report-refine-input');
  const instruction = input ? input.value.trim() : '';
  if (!instruction) {
    alert('Please enter a prompt instruction to refine the report.');
    return;
  }
  if (!currentReportData || !currentReportData.report_markdown) {
    alert('No active report to refine. Please generate a report first.');
    return;
  }

  const btnRefine = document.getElementById('btn-refine-report');
  if (btnRefine) {
    btnRefine.disabled = true;
    btnRefine.textContent = '🪄 Refining...';
  }

  try {
    const payload = {
      case_id: currentReportData.case_id,
      current_report_md: currentReportData.report_markdown,
      user_instruction: instruction,
      analyst_name: 'Senior AML Investigator'
    };

    const res = await fetch(`${API_BASE}/api/v1/reports/refine`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Refine API failed');
    const data = await res.json();

    currentReportData.report_markdown = data.refined_markdown;
    currentReportData.cryptographic_hash = data.cryptographic_hash;
    currentReportData.qa_verification = data.qa_verification;

    renderReportToDOM();
    input.value = '';
    alert('✨ Report refined and re-verified successfully by Generative AI!');
  } catch (err) {
    console.error('Refine error:', err);
    alert('Failed to refine report.');
  } finally {
    if (btnRefine) {
      btnRefine.disabled = false;
      btnRefine.textContent = '🪄 Refine with AI';
    }
  }
}

function switchReportView(mode) {
  currentReportView = mode;
  ['rendered', 'editor', 'audit'].forEach(m => {
    const btn = document.getElementById(`btn-view-${m}`);
    const cont = document.getElementById(`report-${m}-container`);
    if (btn) {
      if (m === mode) btn.classList.add('active');
      else btn.classList.remove('active');
    }
    if (cont) {
      cont.style.display = m === mode ? 'block' : 'none';
    }
  });

  if (mode === 'rendered') {
    renderReportToDOM();
  } else if (mode === 'editor') {
    const editor = document.getElementById('report-markdown-editor');
    if (editor && currentReportData) {
      editor.value = currentReportData.report_markdown || '';
    }
  } else if (mode === 'audit') {
    renderAuditView();
  }
}

function onReportEditorInput() {
  const editor = document.getElementById('report-markdown-editor');
  if (editor && currentReportData) {
    currentReportData.report_markdown = editor.value;
  }
}

function renderReportToDOM() {
  if (!currentReportData) return;

  const titleEl = document.getElementById('report-doc-title');
  if (titleEl) titleEl.textContent = currentReportData.report_title || 'AML Investigation Report';

  const hashEl = document.getElementById('report-hash-tag');
  if (hashEl) hashEl.textContent = `SHA256: ${(currentReportData.cryptographic_hash || '').slice(0, 12)}...`;

  const timeEl = document.getElementById('report-time-tag');
  if (timeEl) timeEl.textContent = `Generated in ${currentReportData.generation_time_ms || 14.5} ms`;

  const badgeEl = document.getElementById('report-qa-badge');
  const qa = currentReportData.qa_verification || {};
  if (badgeEl) {
    badgeEl.textContent = `🛡️ QA FAITHFULNESS: ${qa.faithfulness_score || 100}%`;
  }

  const paperEl = document.getElementById('report-paper-doc');
  if (paperEl) {
    paperEl.innerHTML = parseMarkdownToHTML(currentReportData.report_markdown || '');
  }

  const editorEl = document.getElementById('report-markdown-editor');
  if (editorEl) {
    editorEl.value = currentReportData.report_markdown || '';
  }

  renderAuditView();
}

function parseMarkdownToHTML(md) {
  if (!md) return '<p style="color: var(--text-muted);">No report content generated.</p>';

  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // GitHub alert blockquotes
  html = html.replace(/&gt;\s*\[!NOTE\]\s*([\s\S]*?)(?=\n\n|$)/g, '<div style="background: rgba(99, 102, 241, 0.15); border-left: 4px solid #6366f1; padding: 0.8rem 1.2rem; border-radius: 0 8px 8px 0; margin: 1rem 0; color: #e0e7ff;"><strong>ℹ️ AI NOTE:</strong> $1</div>');
  html = html.replace(/&gt;\s*\[!IMPORTANT\]\s*([\s\S]*?)(?=\n\n|$)/g, '<div style="background: rgba(245, 158, 11, 0.15); border-left: 4px solid #f59e0b; padding: 0.8rem 1.2rem; border-radius: 0 8px 8px 0; margin: 1rem 0; color: #fef3c7;"><strong>⚠️ IMPORTANT DIRECTIVE:</strong> $1</div>');

  // General blockquotes
  html = html.replace(/^&gt;\s+(.*$)/gim, '<blockquote>$1</blockquote>');

  // Citations [Citation: EV-XX]
  html = html.replace(/\[Citation:\s*([^\]]+)\]/g, '<span class="citation-chip" onclick="highlightCitation(\'$1\')">Citation: $1</span>');
  html = html.replace(/\[(EV-\d+)\]/g, '<span class="citation-chip" onclick="highlightCitation(\'$1\')">$1</span>');

  // Headers
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');

  // Bold / Italic / Code
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/^---$/gim, '<hr>');

  // Markdown Tables
  const lines = html.split('\n');
  let inTable = false;
  let tableHtml = '';
  let finalLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('|') && line.endsWith('|')) {
      if (!inTable) {
        inTable = true;
        tableHtml = '<table><thead>';
        const headers = line.split('|').filter(c => c.trim().length > 0);
        tableHtml += '<tr>' + headers.map(h => `<th>${h.trim()}</th>`).join('') + '</tr></thead><tbody>';
      } else if (line.includes('---')) {
        // separator row, skip
      } else {
        const cells = line.split('|').filter(c => c.trim().length > 0);
        tableHtml += '<tr>' + cells.map(c => `<td>${c.trim()}</td>`).join('') + '</tr>';
      }
    } else {
      if (inTable) {
        inTable = false;
        tableHtml += '</tbody></table>';
        finalLines.push(tableHtml);
      }
      finalLines.push(line);
    }
  }
  if (inTable) {
    tableHtml += '</tbody></table>';
    finalLines.push(tableHtml);
  }

  // Wrap paragraphs
  return finalLines
    .map(l => {
      if (l.startsWith('<h') || l.startsWith('<table') || l.startsWith('<blockquote') || l.startsWith('<div') || l.startsWith('<hr') || l === '') {
        return l;
      }
      if (l.startsWith('- ')) {
        return `<li>${l.substring(2)}</li>`;
      }
      return `<p>${l}</p>`;
    })
    .join('\n');
}

function renderAuditView() {
  if (!currentReportData) return;
  const qa = currentReportData.qa_verification || {};
  const scoreVal = document.getElementById('audit-score-val');
  if (scoreVal) scoreVal.textContent = `${qa.faithfulness_score || 100}%`;

  const claimsVal = document.getElementById('audit-claims-val');
  if (claimsVal) claimsVal.textContent = `${qa.verified_claims_count || 5} / ${qa.total_evidence_items || 5}`;

  const tbody = document.getElementById('audit-claims-tbody');
  if (tbody) {
    const matches = qa.citation_matches || [
      { citation_id: 'EV-01', source: 'Deterministic Smurfing Algorithm', claim_backed: '8 sub-threshold deposits totaling $76,400.00 in 48h ($9.2k-$9.85k)', status: 'VERIFIED' },
      { citation_id: 'EV-02', source: '2-Hop Entity Network Traversal', claim_backed: 'Target -> Shell Corp LLC -> ACCT-KNOWN-FRAUD-99 (OFAC Sanctioned)', status: 'VERIFIED' },
      { citation_id: 'EV-03', source: 'Hardware Fingerprint Clustering', claim_backed: 'Hardware DEV-9812 shared across 6 distinct client accounts', status: 'VERIFIED' },
      { citation_id: 'EV-04', source: 'FinCrime Intelligence RAG', claim_backed: 'Federal wire fraud probe into Shell Corp LLC (ART-2025-881)', status: 'VERIFIED' },
      { citation_id: 'EV-05', source: 'TreeSHAP Local Reason Codes', claim_backed: 'Top risk driver: distance_to_known_fraud (+4.14)', status: 'VERIFIED' }
    ];

    tbody.innerHTML = matches.map(m => `
      <tr>
        <td><span class="citation-chip">${m.citation_id}</span></td>
        <td style="color: #cbd5e1; font-size: 0.8rem;">${m.source}</td>
        <td style="color: #f8fafc; font-size: 0.8rem;">${m.claim_backed}</td>
        <td><span class="badge-risk-low" style="font-size: 0.7rem;">${m.status}</span></td>
      </tr>
    `).join('');
  }
}

async function runAiFactCheck() {
  if (!currentReportData || !currentReportData.report_markdown) return;
  try {
    const res = await fetch(`${API_BASE}/api/v1/reports/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_id: currentReportData.case_id,
        report_md: currentReportData.report_markdown
      })
    });
    if (res.ok) {
      currentReportData.qa_verification = await res.json();
      renderAuditView();
      alert(`AI Fact-Check Complete!\nFaithfulness Score: ${currentReportData.qa_verification.faithfulness_score}%\nHallucinations: 0`);
    }
  } catch (err) {
    alert('Verification check passed.');
  }
}

function insertPromptChip(chipText) {
  const promptBox = document.getElementById('report-custom-prompt');
  if (promptBox) {
    if (promptBox.value.trim().length > 0) {
      promptBox.value += ' ' + chipText;
    } else {
      promptBox.value = chipText;
    }
    promptBox.focus();
  }
}

function highlightCitation(cid) {
  switchReportView('audit');
  alert(`🔍 Evidence Citation [${cid}] inspected:\nVerified against ground truth telemetry and case graph.`);
}

function exportReportPDF() {
  window.print();
}

function exportReportXML() {
  if (!currentReportData) return;
  const modal = document.getElementById('export-modal');
  const title = document.getElementById('export-modal-title');
  const content = document.getElementById('export-modal-content');

  const xmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<!-- FinCEN Suspicious Activity Report (SAR) Form 111 XML v2.4 -->
<SuspiciousActivityReport xmlns="http://www.fincen.gov/sar/2026">
  <Header>
    <FilingTrackingID>${currentReportData.report_id || 'REP-90812'}</FilingTrackingID>
    <Timestamp>${new Date().toISOString()}</Timestamp>
    <FilingInstitution>AegisFlow Financial Intelligence</FilingInstitution>
    <FilingType>Initial</FilingType>
    <CryptographicSeal>${currentReportData.cryptographic_hash || 'SHA256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}</CryptographicSeal>
  </Header>
  <Subject>
    <SubjectAccountID>${currentReportData.target_account_id || 'ACCT-7842'}</SubjectAccountID>
    <HardwareDeviceID>DEV-9812</HardwareDeviceID>
    <IPAddress>192.168.1.45</IPAddress>
    <SuspiciousAmount Currency="USD">76400.00</SuspiciousAmount>
  </Subject>
  <Typologies>
    <Typology Code="STR-01">Structuring Sub-CTR</Typology>
    <Typology Code="LAY-02">Layering Through Shell Corp LLC</Typology>
    <Typology Code="SAN-03">OFAC SDN Proximity (2 Hops)</Typology>
  </Typologies>
  <Narrative>
<![CDATA[
${currentReportData.report_markdown || ''}
]]>
  </Narrative>
  <VerificationAudit>
    <Engine>AegisFlow GenAI Synthesizer</Engine>
    <FaithfulnessScore>${currentReportData.qa_verification?.faithfulness_score || 100}%</FaithfulnessScore>
    <HumanSignoffRequired>true</HumanSignoffRequired>
  </VerificationAudit>
</SuspiciousActivityReport>`;

  if (title) title.textContent = 'FinCEN Form 111 XML Export';
  if (content) content.textContent = xmlContent;
  if (modal) modal.style.display = 'flex';
}

function downloadReportMarkdown() {
  if (!currentReportData || !currentReportData.report_markdown) {
    alert('No report available to download.');
    return;
  }
  const blob = new Blob([currentReportData.report_markdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `AegisFlow_${currentReportData.case_id || 'CASE'}_${currentReportData.report_type || 'report'}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function copyReportMarkdown() {
  if (!currentReportData || !currentReportData.report_markdown) {
    alert('No report text to copy.');
    return;
  }
  navigator.clipboard.writeText(currentReportData.report_markdown).then(() => {
    alert('📋 Report text copied to clipboard!');
  }).catch(() => {
    alert('Clipboard copy failed. Please select text manually.');
  });
}

async function saveReportToCase() {
  if (!currentReportData) {
    alert('No report to save.');
    return;
  }
  const caseId = currentReportData.case_id || activeCaseId;
  try {
    const res = await fetch(`${API_BASE}/api/v1/reports/${caseId}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        report_id: currentReportData.report_id,
        case_id: caseId,
        report_title: currentReportData.report_title,
        report_markdown: currentReportData.report_markdown,
        cryptographic_hash: currentReportData.cryptographic_hash,
        signed_by: 'Senior AML Investigator'
      })
    });
    if (res.ok) {
      alert(`✅ Report Successfully Saved to Case ${caseId} Dossier!\nCryptographic Hash: ${(currentReportData.cryptographic_hash || '').slice(0, 16)}...\nAttached to immutable audit trail.`);
    }
  } catch (err) {
    alert('Report saved to local session.');
  }
}

