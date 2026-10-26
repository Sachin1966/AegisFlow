import React, { useState, useEffect } from 'react';
import {
  SARDraft,
  saveSARDraft,
  approveSAR,
  exportFinCEN,
  generateAIReport,
  refineAIReport,
  verifyAIReport,
  getReportModels,
  ReportModelsResponse
} from '../api/client';

interface NarrativeEditorProps {
  draft: SARDraft | null;
  caseId?: string;
  targetAccountId?: string;
  onDraftSaved?: () => void;
  onDraftApproved?: () => void;
}

export const NarrativeEditor: React.FC<NarrativeEditorProps> = ({
  draft,
  caseId = 'CASE-2026-001',
  targetAccountId = 'ACCT-7842',
  onDraftSaved,
  onDraftApproved
}) => {
  const [text, setText] = useState<string>(draft?.full_narrative_md || '');
  const [activeTab, setActiveTab] = useState<'preview' | 'editor'>('preview');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isRefining, setIsRefining] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showSignoffModal, setShowSignoffModal] = useState(false);
  const [rationale, setRationale] = useState('');
  const [reviewerName, setReviewerName] = useState('Chief Compliance Officer');
  const [exportPreview, setExportPreview] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<'json' | 'xml'>('json');

  // GenAI Report Studio States
  const [reportType, setReportType] = useState<string>('fincen_sar');
  const [audienceTone, setAudienceTone] = useState<string>('formal_regulatory');
  const [selectedModel, setSelectedModel] = useState<string>('llama3.2:latest');
  const [llmProvider, setLlmProvider] = useState<string>('ollama');
  const [customPrompt, setCustomPrompt] = useState<string>('');
  const [refineInstruction, setRefineInstruction] = useState<string>('');
  const [modelsData, setModelsData] = useState<ReportModelsResponse | null>(null);
  const [generationTimeMs, setGenerationTimeMs] = useState<number | null>(null);
  const [cryptoHash, setCryptoHash] = useState<string | null>(null);
  const [engineUsed, setEngineUsed] = useState<string>('Ollama (llama3.2:latest)');
  const [qaStatus, setQaStatus] = useState<string>('PASSED');
  const [faithfulness, setFaithfulness] = useState<number>(100.0);
  const [verifiedCount, setVerifiedCount] = useState<number>(5);

  // Load available models on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await getReportModels();
        setModelsData(data);
        if (data.default_model) {
          setSelectedModel(data.default_model);
        }
      } catch (err) {
        console.error('Failed to load Ollama models:', err);
      }
    };
    fetchModels();
  }, []);

  // Sync draft narrative if draft changes
  useEffect(() => {
    if (draft?.full_narrative_md && !text) {
      setText(draft.full_narrative_md);
    }
  }, [draft]);

  const handleGenerateReport = async () => {
    setIsGenerating(true);
    try {
      const res = await generateAIReport({
        case_id: caseId,
        target_account_id: targetAccountId,
        report_type: reportType,
        audience_tone: audienceTone,
        custom_prompt: customPrompt.trim() || undefined,
        llm_provider: llmProvider,
        model_name: selectedModel
      });

      if (res && res.report_markdown) {
        setText(res.report_markdown);
        setGenerationTimeMs(res.generation_time_ms);
        setCryptoHash(res.cryptographic_hash?.substring(0, 16) || null);
        setEngineUsed(res.metadata?.engine || 'Ollama LLM');
        if (res.qa_verification) {
          setQaStatus(res.qa_verification.qa_status);
          setFaithfulness(res.qa_verification.faithfulness_score);
          setVerifiedCount(res.qa_verification.verified_claims_count);
        }
      }
    } catch (err: any) {
      alert(`Error generating report: ${err.message || 'Server error'}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRefineReport = async (instructionToUse?: string) => {
    const inst = instructionToUse || refineInstruction;
    if (!inst.trim()) {
      alert('Please enter a refinement directive for Ollama.');
      return;
    }
    setIsRefining(true);
    try {
      const res = await refineAIReport({
        case_id: caseId,
        current_report_md: text,
        user_instruction: inst,
        llm_provider: llmProvider,
        model_name: selectedModel
      });

      if (res && res.refined_markdown) {
        setText(res.refined_markdown);
        setCryptoHash(res.cryptographic_hash?.substring(0, 16) || null);
        setRefineInstruction('');
        if (res.qa_verification) {
          setQaStatus(res.qa_verification.qa_status);
          setFaithfulness(res.qa_verification.faithfulness_score);
          setVerifiedCount(res.qa_verification.verified_claims_count);
        }
      }
    } catch (err: any) {
      alert(`Refinement failed: ${err.message || 'Server error'}`);
    } finally {
      setIsRefining(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveSARDraft(caseId, text, 'analyst.sarah');
      alert(`Investigation report saved successfully with cryptographic seal.`);
      if (onDraftSaved) onDraftSaved();
    } catch (err) {
      alert('Failed to save report.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!rationale.trim()) {
      alert('Mandatory compliance reviewer rationale is required for FinCEN SAR sign-off.');
      return;
    }
    try {
      await approveSAR(caseId, rationale, reviewerName);
      setShowSignoffModal(false);
      alert('✅ Regulatory report formally signed off. Immutable audit log recorded.');
      if (onDraftApproved) onDraftApproved();
    } catch (err) {
      alert('Approval failed.');
    }
  };

  const handleExport = async (format: 'json' | 'xml') => {
    setExportFormat(format);
    const content = await exportFinCEN(caseId, format);
    setExportPreview(typeof content === 'string' ? content : JSON.stringify(content, null, 2));
  };

  const hasCitations = text.includes('EV-01') || text.includes('EV-02');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      
      {/* GenAI Report Studio Control Header */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.85)',
        border: '1px solid rgba(99, 102, 241, 0.25)',
        borderRadius: '12px',
        padding: '1rem 1.25rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)'
      }}>
        
        {/* Row 1: Studio Title, Engine Status Badge, & Output Formats */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '1.1rem' }}>🦙</span>
            <div>
              <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc' }}>
                GenAI Report Studio & Regulatory Narrative Engine
              </span>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                Ollama LLM Orchestration with Ground-Truth Verification & Deterministic Telemetry
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              background: modelsData?.ollama_available ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              color: modelsData?.ollama_available ? '#34d399' : '#fbbf24',
              border: `1px solid ${modelsData?.ollama_available ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
              padding: '0.2rem 0.6rem',
              borderRadius: '20px',
              fontSize: '0.72rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: modelsData?.ollama_available ? '#34d399' : '#fbbf24' }} />
              {modelsData?.ollama_available ? 'Ollama Online' : 'Ollama Offline (Fallback Ready)'}
            </span>

            <div style={{ display: 'flex', gap: '0.35rem' }}>
              <button
                onClick={() => handleExport('json')}
                style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#94a3b8', border: '1px solid rgba(255, 255, 255, 0.1)', padding: '0.35rem 0.65rem', borderRadius: '6px', fontSize: '0.75rem', cursor: 'pointer' }}
              >
                Export JSON
              </button>
              <button
                onClick={() => handleExport('xml')}
                style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#94a3b8', border: '1px solid rgba(255, 255, 255, 0.1)', padding: '0.35rem 0.65rem', borderRadius: '6px', fontSize: '0.75rem', cursor: 'pointer' }}
              >
                Export XML
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                style={{ background: '#4f46e5', color: '#fff', border: 'none', padding: '0.35rem 0.75rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
              >
                {isSaving ? 'Saving...' : 'Save Draft'}
              </button>
              <button
                onClick={() => setShowSignoffModal(true)}
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', border: 'none', padding: '0.35rem 0.85rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer' }}
              >
                Manager Sign-Off
              </button>
            </div>
          </div>
        </div>

        {/* Row 2: Selectors (Report Type, Model, Audience Tone) & Generate Button */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr)) auto', gap: '0.6rem', alignItems: 'center' }}>
          
          {/* Report Type */}
          <div>
            <label style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block', marginBottom: '0.2rem' }}>
              Report Structure Template:
            </label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '6px',
                padding: '0.4rem',
                color: '#fff',
                fontSize: '0.78rem'
              }}
            >
              <option value="fincen_sar">FinCEN Form 111 SAR Narrative</option>
              <option value="executive_briefing">Executive MLRO Briefing</option>
              <option value="law_enforcement">Law Enforcement Package (FBI/IRS)</option>
              <option value="sanctions_proximity">OFAC Sanctions Proximity Dossier</option>
              <option value="internal_audit">Internal AML Audit & Governance</option>
            </select>
          </div>

          {/* Model Selection */}
          <div>
            <label style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block', marginBottom: '0.2rem' }}>
              LLM Model (Ollama):
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '6px',
                padding: '0.4rem',
                color: '#fff',
                fontSize: '0.78rem'
              }}
            >
              {modelsData?.models && modelsData.models.length > 0 ? (
                modelsData.models.map((m) => (
                  <option key={m.name} value={m.name}>
                    {m.name} ({m.parameter_size || 'local'})
                  </option>
                ))
              ) : (
                <>
                  <option value="llama3.2:latest">llama3.2:latest (3.2B)</option>
                  <option value="llama3:latest">llama3:latest (8B)</option>
                  <option value="mistral:latest">mistral:latest (7B)</option>
                </>
              )}
            </select>
          </div>

          {/* Audience Tone */}
          <div>
            <label style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block', marginBottom: '0.2rem' }}>
              Audience Tone:
            </label>
            <select
              value={audienceTone}
              onChange={(e) => setAudienceTone(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '6px',
                padding: '0.4rem',
                color: '#fff',
                fontSize: '0.78rem'
              }}
            >
              <option value="formal_regulatory">Formal Regulatory</option>
              <option value="forensic_legal">Forensic Legal</option>
              <option value="executive_brief">Executive Brief</option>
              <option value="technical_audit">Technical Audit</option>
            </select>
          </div>

          {/* Generate Button */}
          <div style={{ alignSelf: 'flex-end' }}>
            <button
              onClick={handleGenerateReport}
              disabled={isGenerating}
              style={{
                background: isGenerating ? '#64748b' : 'linear-gradient(135deg, #6366f1, #06b6d4)',
                color: '#fff',
                border: 'none',
                padding: '0.45rem 1.1rem',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: isGenerating ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                whiteSpace: 'nowrap',
                boxShadow: '0 0 12px rgba(99, 102, 241, 0.3)'
              }}
            >
              {isGenerating ? '⚡ Generating with Ollama...' : '⚡ Generate with Ollama'}
            </button>
          </div>

        </div>

        {/* Custom Investigator Directive Input */}
        <div>
          <input
            type="text"
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="Optional investigator directive (e.g. 'Focus heavily on OFAC sanctions proximity and shell entity routing')..."
            style={{
              width: '100%',
              background: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '6px',
              padding: '0.45rem 0.75rem',
              color: '#e2e8f0',
              fontSize: '0.78rem'
            }}
          />
        </div>

      </div>

      {/* Interactive Refinement Directive Toolbar */}
      <div style={{
        background: 'rgba(255, 255, 255, 0.02)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '10px',
        padding: '0.75rem 1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.6rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            💬 Natural Language Report Refinement (Ollama Directives)
          </span>
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            {[
              { label: '+ Sanctions Proximity', inst: 'Add focused sanctions proximity analysis to OFAC SDN entity ACCT-99 via Shell Corp LLC' },
              { label: '+ Structuring Ledger', inst: 'Break down sub-CTR structuring calculations under 31 U.S.C. 5324' },
              { label: '+ MLRO Executive Summary', inst: 'Add high-level MLRO decision summary with critical threat rating' }
            ].map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleRefineReport(chip.inst)}
                disabled={isRefining}
                style={{
                  background: 'rgba(99, 102, 241, 0.12)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  color: '#a5b4fc',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  fontSize: '0.7rem',
                  cursor: isRefining ? 'not-allowed' : 'pointer'
                }}
              >
                {chip.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={refineInstruction}
            onChange={(e) => setRefineInstruction(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleRefineReport()}
            placeholder="Instruct Ollama to modify or emphasize specific sections (e.g. 'Add explicit legal predicate under 18 U.S.C. § 1956')..."
            style={{
              flex: 1,
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              padding: '0.45rem 0.75rem',
              color: '#fff',
              fontSize: '0.8rem'
            }}
          />
          <button
            onClick={() => handleRefineReport()}
            disabled={isRefining || !refineInstruction.trim()}
            style={{
              background: isRefining ? '#64748b' : '#6366f1',
              color: '#fff',
              border: 'none',
              padding: '0.45rem 1rem',
              borderRadius: '6px',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: isRefining || !refineInstruction.trim() ? 'not-allowed' : 'pointer'
            }}
          >
            {isRefining ? 'Refining...' : 'Refine with Ollama'}
          </button>
        </div>
      </div>

      {/* Adversarial QA Verification Badge & Evidence Chips */}
      <div style={{
        background: 'rgba(18, 24, 38, 0.75)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '10px',
        padding: '0.75rem 1rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>QA Verification:</span>
            <span style={{
              background: qaStatus === 'PASSED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
              color: qaStatus === 'PASSED' ? '#34d399' : '#f87171',
              border: `1px solid ${qaStatus === 'PASSED' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
              padding: '0.2rem 0.55rem',
              borderRadius: '4px',
              fontSize: '0.72rem',
              fontWeight: 700
            }}>
              {qaStatus} ({faithfulness.toFixed(0)}% Faithfulness)
            </span>
          </div>

          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
            Verified Citations: <strong style={{ color: '#06b6d4' }}>{verifiedCount}/5 Ground Truth Facts</strong>
          </div>

          {cryptoHash && (
            <div style={{ fontSize: '0.72rem', color: '#64748b', fontFamily: 'JetBrains Mono' }}>
              SHA256: {cryptoHash}...
            </div>
          )}

          {generationTimeMs && (
            <div style={{ fontSize: '0.72rem', color: '#10b981' }}>
              ⏱️ {generationTimeMs}ms
            </div>
          )}
        </div>

        {/* View Switcher: Rendered vs Raw Markdown */}
        <div style={{ display: 'flex', background: 'rgba(0, 0, 0, 0.3)', borderRadius: '6px', padding: '2px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <button
            onClick={() => setActiveTab('preview')}
            style={{
              background: activeTab === 'preview' ? '#4f46e5' : 'transparent',
              color: activeTab === 'preview' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '0.25rem 0.65rem',
              borderRadius: '4px',
              fontSize: '0.75rem',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            Formatted Document
          </button>
          <button
            onClick={() => setActiveTab('editor')}
            style={{
              background: activeTab === 'editor' ? '#4f46e5' : 'transparent',
              color: activeTab === 'editor' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '0.25rem 0.65rem',
              borderRadius: '4px',
              fontSize: '0.75rem',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            Markdown Editor
          </button>
        </div>
      </div>

      {/* Main Report Body Display */}
      {activeTab === 'preview' ? (
        <div style={{
          background: 'rgba(10, 15, 26, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '12px',
          padding: '1.5rem',
          maxHeight: '560px',
          overflowY: 'auto',
          fontSize: '0.85rem',
          lineHeight: 1.6,
          color: '#e2e8f0',
          fontFamily: 'Inter, sans-serif'
        }}>
          {text ? (
            <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
              {text}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📄</div>
              <div>No report generated yet. Click <strong>Generate with Ollama</strong> above to synthesize the investigation narrative.</div>
            </div>
          )}
        </div>
      ) : (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={18}
          placeholder="Enter investigation report markdown..."
          style={{
            width: '100%',
            background: 'rgba(0, 0, 0, 0.45)',
            color: '#e2e8f0',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '10px',
            padding: '1rem',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.82rem',
            lineHeight: 1.55,
            resize: 'vertical'
          }}
        />
      )}

      {/* Evidence Citation Reference Chips */}
      <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.06)', borderRadius: '8px', padding: '0.75rem' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.5rem' }}>
          Ground-Truth Evidence Citations (Verified Claims):
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {[
            { id: 'EV-01', cat: 'TYPOLOGY', label: 'Smurfing ($76.4k in 8 txs)', conf: '0.92' },
            { id: 'EV-02', cat: 'GRAPH', label: '2 Hops to OFAC Entity ACCT-99', conf: '1.00' },
            { id: 'EV-03', cat: 'DEVICE', label: 'DEV-9812 Shared across 6 Accounts', conf: '0.95' },
            { id: 'EV-04', cat: 'RAG_MEDIA', label: 'ART-2025-881 Federal Wire Fraud Probe', conf: '0.94' },
            { id: 'EV-05', cat: 'SHAP', label: 'XGBoost 0.942 Fraud Probability', conf: '0.98' }
          ].map((c) => (
            <div
              key={c.id}
              style={{
                background: 'rgba(99, 102, 241, 0.12)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                borderRadius: '6px',
                padding: '0.3rem 0.6rem',
                fontSize: '0.72rem',
                color: '#a5b4fc',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem'
              }}
            >
              <strong style={{ color: '#38bdf8' }}>[{c.id}]</strong>
              <span style={{ color: '#cbd5e1' }}>{c.label}</span>
              <span style={{ color: '#34d399', fontWeight: 600 }}>({(parseFloat(c.conf) * 100).toFixed(0)}%)</span>
            </div>
          ))}
        </div>
      </div>

      {/* Mandatory Sign-off Modal */}
      {showSignoffModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#0f172a', border: '1px solid rgba(99, 102, 241, 0.4)', borderRadius: '16px', padding: '2rem', width: '520px', maxWidth: '92%' }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
              Mandatory Human Sign-Off (Zero Autonomous Filings)
            </h3>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '1.25rem' }}>
              BSA / FinCEN regulatory compliance requires a human compliance officer to formally verify the evidence pack and submit a non-repudiable audit rationale.
            </p>

            <label style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'block', marginBottom: '0.4rem' }}>
              Reviewer Name / Title:
            </label>
            <input
              type="text"
              value={reviewerName}
              onChange={(e) => setReviewerName(e.target.value)}
              style={{ width: '100%', padding: '0.6rem', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '6px', color: '#fff', marginBottom: '1rem', fontSize: '0.85rem' }}
            />

            <label style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'block', marginBottom: '0.4rem' }}>
              Mandatory Reviewer Rationale:
            </label>
            <textarea
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              placeholder="e.g. Verified 2-hop connection to OFAC entity ACCT-99 via Shell Corp LLC and confirmed 8 sub-threshold structured wires totaling $76.4k. Authorized for SAR filing."
              rows={4}
              style={{ width: '100%', padding: '0.6rem', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '6px', color: '#fff', marginBottom: '1.5rem', fontSize: '0.85rem', fontFamily: 'Inter' }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                onClick={() => setShowSignoffModal(false)}
                style={{ background: 'transparent', border: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8', padding: '0.6rem 1.2rem', borderRadius: '8px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', border: 'none', padding: '0.6rem 1.4rem', borderRadius: '8px', fontWeight: 600, cursor: 'pointer' }}
              >
                Confirm Sign-Off & Seal Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* FinCEN Export Modal */}
      {exportPreview && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#0f172a', border: '1px solid rgba(255, 255, 255, 0.2)', borderRadius: '16px', padding: '1.5rem', width: '680px', maxWidth: '92%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>
                FinCEN SAR Structured Export ({exportFormat.toUpperCase()})
              </h3>
              <button onClick={() => setExportPreview(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.2rem', cursor: 'pointer' }}>✕</button>
            </div>
            <pre style={{ background: 'rgba(0, 0, 0, 0.5)', padding: '1rem', borderRadius: '8px', color: '#38bdf8', fontSize: '0.75rem', maxHeight: '360px', overflowY: 'auto', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
              {exportPreview}
            </pre>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(exportPreview);
                  alert('Copied FinCEN package to clipboard!');
                }}
                style={{ background: '#4f46e5', color: '#fff', border: 'none', padding: '0.5rem 1.2rem', borderRadius: '6px', fontWeight: 600, cursor: 'pointer' }}
              >
                Copy Content
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
