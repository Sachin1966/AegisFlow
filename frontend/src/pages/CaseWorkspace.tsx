import React, { useState, useEffect } from 'react';
import { getCaseDetail, getCaseGraph, runMultiAgentInvestigation, recordCaseDisposition, GraphData, SARDraft } from '../api/client';
import { EntityGraph } from '../components/EntityGraph';
import { TxnTimeline } from '../components/TxnTimeline';
import { NarrativeEditor } from '../components/NarrativeEditor';

interface CaseWorkspaceProps {
  caseId: string;
}

export const CaseWorkspace: React.FC<CaseWorkspaceProps> = ({ caseId }) => {
  const [caseData, setCaseData] = useState<any>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<any[]>([]);
  const [sarDraft, setSarDraft] = useState<SARDraft | null>(null);
  const [stepsLog, setStepsLog] = useState<any[]>([]);
  const [isRunningInvestigation, setIsRunningInvestigation] = useState(false);
  const [disposition, setDisposition] = useState<'fraud' | 'not_fraud' | 'sar_filed'>('sar_filed');
  const [dispositionRationale, setDispositionRationale] = useState('Confirmed structuring ring and multi-hop connection to OFAC entity.');

  const loadCase = async () => {
    try {
      const res = await getCaseDetail(caseId);
      if (res) {
        setCaseData(res.case);
        if (res.sar_draft) {
          setSarDraft(res.sar_draft);
        }
      }

      const gData = await getCaseGraph(caseId, 2);
      setGraphData(gData);

      // Default mock timeline events for ACCT-7842
      setTimelineEvents([
        { tx_id: 'tx_7812a01', timestamp: new Date(Date.now() - 48 * 3600 * 1000).toISOString(), amount: 9850.0, currency: 'USD', channel: 'mobile_app', source: 'ACCT-7842', counterparty: 'ACCT-9011', type: 'deposit', is_sub_threshold: true },
        { tx_id: 'tx_7812a02', timestamp: new Date(Date.now() - 42 * 3600 * 1000).toISOString(), amount: 9600.0, currency: 'USD', channel: 'mobile_app', source: 'ACCT-7842', counterparty: 'ACCT-9012', type: 'deposit', is_sub_threshold: true },
        { tx_id: 'tx_7812a03', timestamp: new Date(Date.now() - 36 * 3600 * 1000).toISOString(), amount: 9750.0, currency: 'USD', channel: 'mobile_app', source: 'ACCT-7842', counterparty: 'ACCT-9013', type: 'deposit', is_sub_threshold: true },
        { tx_id: 'tx_7812a04', timestamp: new Date(Date.now() - 28 * 3600 * 1000).toISOString(), amount: 9900.0, currency: 'USD', channel: 'mobile_app', source: 'ACCT-7842', counterparty: 'ACCT-9014', type: 'deposit', is_sub_threshold: true },
        { tx_id: 'tx_7812a05', timestamp: new Date(Date.now() - 14 * 3600 * 1000).toISOString(), amount: 39200.0, currency: 'USD', channel: 'wire_transfer', source: 'ACCT-7842', counterparty: 'ACCT-COUNTERPART-1', type: 'consolidation_wire', is_sub_threshold: false, flag: 'IMMEDIATE_LAYERING_OUTFLOW' }
      ]);
    } catch (err) {
      console.error('Error loading case workspace', err);
    }
  };

  useEffect(() => {
    loadCase();
  }, [caseId]);

  const handleRunInvestigation = async () => {
    setIsRunningInvestigation(true);
    try {
      const result = await runMultiAgentInvestigation(caseId, caseData?.subject_account || 'ACCT-7842');
      if (result) {
        setStepsLog(result.steps_log || []);
        if (result.sar_draft) {
          setSarDraft(result.sar_draft);
        }
        if (result.graph_data) {
          setGraphData(result.graph_data);
        }
      }
    } catch (err) {
      alert('Error triggering LangGraph multi-agent team.');
    } finally {
      setIsRunningInvestigation(false);
    }
  };

  const handleSubmitDisposition = async () => {
    try {
      await recordCaseDisposition(caseId, disposition, dispositionRationale);
      alert(`Case disposition (${disposition}) recorded! Feedback label queued for model retraining dataset.`);
      loadCase();
    } catch (err) {
      alert('Error recording disposition.');
    }
  };

  const getBadgeClass = (agent: string) => {
    switch (agent) {
      case 'Supervisor': return 'badge-supervisor';
      case 'LinkAnalyst': return 'badge-link';
      case 'PatternAnalyst': return 'badge-pattern';
      case 'AdverseMediaResearcher': return 'badge-media';
      case 'NarrativeWriter': return 'badge-writer';
      case 'QAReviewer': return 'badge-qa';
      default: return 'badge-supervisor';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Top Banner with Case Info & Launch Button */}
      <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.25rem 1.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc' }}>
              {caseId}: {caseData?.title || 'Suspected Money Laundering Ring'}
            </h2>
            <span style={{ background: 'rgba(244, 63, 94, 0.2)', color: '#f43f5e', border: '1px solid rgba(244, 63, 94, 0.4)', padding: '0.2rem 0.6rem', borderRadius: '4px', fontWeight: 700, fontSize: '0.75rem' }}>
              CRITICAL
            </span>
          </div>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            Subject Account: <strong style={{ color: '#06b6d4', fontFamily: 'JetBrains Mono' }}>{caseData?.subject_account || 'ACCT-7842'}</strong> • Assigned: <strong>{caseData?.assigned_analyst || 'analyst.sarah'}</strong> • Status: <span style={{ textTransform: 'capitalize', color: '#fbbf24', fontWeight: 600 }}>{caseData?.status || 'investigating'}</span>
          </div>
        </div>

        <button
          onClick={handleRunInvestigation}
          disabled={isRunningInvestigation}
          style={{
            background: isRunningInvestigation ? '#64748b' : 'linear-gradient(135deg, #6366f1, #06b6d4)',
            color: '#fff',
            border: 'none',
            padding: '0.65rem 1.4rem',
            borderRadius: '10px',
            fontSize: '0.85rem',
            fontWeight: 700,
            cursor: isRunningInvestigation ? 'not-allowed' : 'pointer',
            boxShadow: '0 0 15px rgba(99, 102, 241, 0.4)'
          }}
        >
          {isRunningInvestigation ? '⚡ Executing LangGraph Agents...' : '🤖 Execute Multi-Agent AML Investigation'}
        </button>
      </div>

      {/* Main Workbench Layout: 2 Columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '1.5rem' }}>
        
        {/* Left Column: Entity Graph, Timeline, and Agent Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Entity Graph Panel */}
          <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.25rem' }}>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Interactive Entity Network (k=2 Hop Neighborhood)</span>
              <span style={{ fontSize: '0.75rem', color: '#f43f5e', fontWeight: 600 }}>⚠️ Path to Sanctioned OFAC Entity Found</span>
            </div>
            <EntityGraph data={graphData} />
          </div>

          {/* LangGraph Agent Trace Execution Panel */}
          <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.25rem' }}>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between' }}>
              <span>Multi-Agent LangGraph Execution Trajectory</span>
              <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
                {stepsLog.length ? `${stepsLog.length}/6 Specialized Agents` : 'Standby'}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '280px', overflowY: 'auto' }}>
              {stepsLog.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '1.5rem', color: '#94a3b8', fontSize: '0.85rem' }}>
                  Click 'Execute Multi-Agent AML Investigation' to trigger Supervisor, Link Analyst, Pattern Analyst, Adverse Media, Narrative Writer, and QA Reviewer.
                </div>
              ) : (
                stepsLog.map((step, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                      borderRadius: '8px',
                      padding: '0.75rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                      <span className={`agent-badge ${getBadgeClass(step.agent)}`}>
                        {step.agent}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Step {step.step_index} • {step.action}</span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                      {step.thought}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Transaction Timeline */}
          <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.25rem' }}>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem' }}>
              Structuring & Layering Timeline (Sub-CTR Inflow Window)
            </div>
            <TxnTimeline events={timelineEvents} />
          </div>

        </div>

        {/* Right Column: FinCEN SAR Draft Editor & Disposition Feedback Loop */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.25rem' }}>
            <NarrativeEditor
              draft={sarDraft}
              caseId={caseId}
              targetAccountId={caseData?.subject_account || 'ACCT-7842'}
              onDraftSaved={() => loadCase()}
              onDraftApproved={() => loadCase()}
            />
          </div>

          {/* Disposition & Feedback Loop Box */}
          <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.25rem' }}>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
              Close Case & Record Training Label Feedback
            </div>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem' }}>
              Analyst dispositions flow back into the feature store and training dataset for nightly model retraining.
            </p>

            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
              {[
                { val: 'sar_filed', label: 'SAR Filed (Fraud = 1)', color: '#f43f5e' },
                { val: 'fraud', label: 'Internal Fraud Block (Fraud = 1)', color: '#f59e0b' },
                { val: 'not_fraud', label: 'False Positive (Fraud = 0)', color: '#10b981' }
              ].map(opt => (
                <button
                  key={opt.val}
                  onClick={() => setDisposition(opt.val as any)}
                  style={{
                    flex: 1,
                    background: disposition === opt.val ? opt.color : 'rgba(255, 255, 255, 0.04)',
                    color: disposition === opt.val ? '#fff' : '#94a3b8',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    padding: '0.5rem',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <textarea
              value={dispositionRationale}
              onChange={(e) => setDispositionRationale(e.target.value)}
              placeholder="Enter final case disposition rationale..."
              rows={2}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '6px',
                padding: '0.6rem',
                color: '#fff',
                fontSize: '0.8rem',
                marginBottom: '0.75rem'
              }}
            />

            <button
              onClick={handleSubmitDisposition}
              style={{
                width: '100%',
                background: 'linear-gradient(135deg, #10b981, #059669)',
                color: '#fff',
                border: 'none',
                padding: '0.6rem',
                borderRadius: '8px',
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              Submit Disposition & Close Loop
            </button>
          </div>

        </div>

      </div>

    </div>
  );
};
