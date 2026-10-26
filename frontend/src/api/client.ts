export const API_BASE = window.location.origin;

export interface Transaction {
  transaction_id: string;
  timestamp: string;
  source_account: string;
  target_account?: string;
  amount: number;
  currency: string;
  channel: string;
  decision: 'APPROVE' | 'REVIEW' | 'DECLINE';
  probability: number;
  reason_codes: Array<{ code: string; feature: string; impact: number; description: string; value: number }>;
  rule_hits: string[];
  latency_ms: number;
  degraded: boolean;
}

export interface CaseItem {
  id: string;
  case_id: string;
  title: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  priority_score: number;
  status: 'open' | 'investigating' | 'pending_review' | 'closed';
  assigned_analyst: string;
  sla_due_at: string;
  created_at: string;
  alerts_count: number;
  subject_account: string;
  disposition?: string | null;
}

export interface GraphNode {
  id: string;
  type: 'account' | 'device' | 'ip' | 'merchant';
  risk_score: number;
  label: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  amount?: number;
  label?: string;
}

export interface GraphData {
  case_id: string;
  target_account: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  shortest_path_to_fraud: string[];
  distance: number;
}

export interface SARDraft {
  case_id: string;
  version: number;
  subject_entity: string;
  suspicious_activity_amount: number;
  detected_typologies: string[];
  full_narrative_md: string;
  citations: Array<{ id: string; type: string; source: string; confidence: number }>;
  status: 'draft' | 'edited' | 'approved';
  author: string;
  reviewed_by?: string | null;
}

export interface ModelOpsData {
  champion: {
    version: string;
    model_type: string;
    pr_auc: number;
    roc_auc: number;
    recall_at_1pct_fpr: number;
    latency_p95_ms: number;
    status: string;
  };
  challenger: {
    version: string;
    model_type: string;
    pr_auc: number;
    roc_auc: number;
    recall_at_1pct_fpr: number;
    latency_p95_ms: number;
    disagreement_rate: number;
    status: string;
  };
  comparison: {
    pr_auc_lift_pct: number;
    recall_lift_pct: number;
    latency_improvement_pct: number;
    disagreement_rate: number;
    promotion_eligible: boolean;
  };
  shadow_metrics: {
    total_shadow_scores: number;
    disagreement_rate: number;
    mean_probability_delta: number;
  };
}

// Client functions
export async function getLiveStream(): Promise<{ transactions: Transaction[] }> {
  const res = await fetch(`${API_BASE}/api/v1/transactions/live`);
  return res.json();
}

export async function ingestPayment(tx: any): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/transactions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tx)
  });
  return res.json();
}

export async function getCases(status?: string): Promise<{ cases: CaseItem[] }> {
  const url = status ? `${API_BASE}/api/v1/cases?status=${status}` : `${API_BASE}/api/v1/cases`;
  const res = await fetch(url);
  return res.json();
}

export async function getCaseDetail(caseId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/cases/${caseId}`);
  return res.json();
}

export async function getCaseGraph(caseId: string, hops: number = 2): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/api/v1/cases/${caseId}/graph?hops=${hops}`);
  return res.json();
}

export async function runMultiAgentInvestigation(caseId: string, accountId: string = 'ACCT-7842'): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/cases/${caseId}/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_account_id: accountId })
  });
  return res.json();
}

export async function saveSARDraft(caseId: string, narrativeMd: string, author: string = 'analyst.sarah'): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/sar/${caseId}/draft`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ narrative_md: narrativeMd, author })
  });
  return res.json();
}

export async function approveSAR(caseId: string, rationale: string, reviewerName: string = 'Compliance Manager'): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/sar/${caseId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reviewer_rationale: rationale, reviewer_name: reviewerName })
  });
  return res.json();
}

export async function exportFinCEN(caseId: string, format: 'json' | 'xml' = 'json'): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/sar/${caseId}/export/fincen?format=${format}`);
  if (format === 'xml') {
    return res.text();
  }
  return res.json();
}

export async function recordCaseDisposition(caseId: string, disposition: string, rationale: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/cases/${caseId}/disposition`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ disposition, rationale })
  });
  return res.json();
}

export async function getModelOps(): Promise<ModelOpsData> {
  const res = await fetch(`${API_BASE}/api/v1/models`);
  return res.json();
}

export async function getThresholds(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/thresholds`);
  return res.json();
}

export async function updateThresholds(reviewT: number, declineT: number, reason: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/thresholds`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ review_threshold: reviewT, decline_threshold: declineT, reason })
  });
  return res.json();
}

export async function rollbackThresholds(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/thresholds/rollback`, { method: 'POST' });
  return res.json();
}

export async function promoteChallengerModel(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/models/promote`, { method: 'POST' });
  return res.json();
}

export async function rollbackModel(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/models/rollback`, { method: 'POST' });
  return res.json();
}

export async function getDriftReport(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/drift`);
  return res.json();
}

// GenAI Report Studio Client APIs
export interface ReportModelItem {
  name: string;
  model: string;
  size_bytes: number;
  parameter_size: string;
  family: string;
}

export interface ReportModelsResponse {
  ollama_available: boolean;
  default_model: string;
  models: ReportModelItem[];
  providers: Array<{ id: string; name: string; enabled: boolean }>;
}

export interface ReportResponse {
  report_id: string;
  case_id: string;
  target_account_id: string;
  report_type: string;
  report_title: string;
  audience_tone: string;
  created_at: string;
  analyst_name: string;
  cryptographic_hash: string;
  generation_time_ms: number;
  report_markdown: string;
  evidence_citations: Array<{ id: string; type: string; source: string; summary: string }>;
  qa_verification: {
    faithfulness_score: number;
    verified_claims_count: number;
    total_evidence_items: number;
    citation_matches: Array<{ citation_id: string; status: string; source: string; claim_backed: string }>;
    hallucination_detected: boolean;
    qa_status: string;
    qa_analyst_remarks: string;
  };
  status: string;
  metadata: {
    engine: string;
    ollama_available: boolean;
    model_name: string;
    custom_prompt_applied: boolean;
    custom_prompt_text: string;
  };
}

export async function getReportModels(): Promise<ReportModelsResponse> {
  const res = await fetch(`${API_BASE}/api/v1/reports/models`);
  return res.json();
}

export async function generateAIReport(params: {
  case_id: string;
  target_account_id?: string;
  report_type?: string;
  audience_tone?: string;
  custom_prompt?: string;
  llm_provider?: string;
  model_name?: string;
  temperature?: number;
}): Promise<ReportResponse> {
  const res = await fetch(`${API_BASE}/api/v1/reports/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  return res.json();
}

export async function refineAIReport(params: {
  case_id: string;
  current_report_md: string;
  user_instruction: string;
  target_section?: string;
  analyst_name?: string;
  llm_provider?: string;
  model_name?: string;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/reports/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  return res.json();
}

export async function verifyAIReport(case_id: string, report_md: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/reports/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ case_id, report_md })
  });
  return res.json();
}

export async function getSavedReports(case_id: string): Promise<{ case_id: string; reports: ReportResponse[]; total: number }> {
  const res = await fetch(`${API_BASE}/api/v1/reports/${case_id}`);
  return res.json();
}

export async function saveCaseReport(case_id: string, payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/reports/${case_id}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  return res.json();
}

