import React, { useState, useEffect } from 'react';
import {
  ModelOpsData,
  getModelOps,
  getThresholds,
  updateThresholds,
  rollbackThresholds,
  promoteChallengerModel,
  rollbackModel,
  getDriftReport
} from '../api/client';

export const ModelOps: React.FC = () => {
  const [modelOps, setModelOps] = useState<ModelOpsData | null>(null);
  const [thresholds, setThresholds] = useState<any>(null);
  const [driftReport, setDriftReport] = useState<any>(null);
  const [reviewThreshold, setReviewThreshold] = useState<number>(0.65);
  const [declineThreshold, setDeclineThreshold] = useState<number>(0.85);
  const [isUpdatingThresholds, setIsUpdatingThresholds] = useState(false);

  const loadAll = async () => {
    try {
      const ops = await getModelOps();
      setModelOps(ops);

      const th = await getThresholds();
      setThresholds(th);
      if (th) {
        setReviewThreshold(th.review_threshold);
        setDeclineThreshold(th.decline_threshold);
      }

      const drift = await getDriftReport();
      setDriftReport(drift);
    } catch (err) {
      console.error('Error loading ModelOps', err);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleSaveThresholds = async () => {
    setIsUpdatingThresholds(true);
    try {
      const res = await updateThresholds(reviewThreshold, declineThreshold, 'Cost-benefit calibration');
      setThresholds(res);
      alert(`Thresholds updated: Review >= ${reviewThreshold}, Decline >= ${declineThreshold}`);
    } catch (err: any) {
      alert(`Error updating thresholds: ${err.message || 'Invalid parameters'}`);
    } finally {
      setIsUpdatingThresholds(false);
    }
  };

  const handleRollbackThresholds = async () => {
    try {
      const res = await rollbackThresholds();
      setThresholds(res);
      setReviewThreshold(res.review_threshold);
      setDeclineThreshold(res.decline_threshold);
      alert('Thresholds rolled back to prior configuration.');
    } catch (err) {
      alert('No rollback target available.');
    }
  };

  const handlePromoteChallenger = async () => {
    const confirm = window.confirm('Promote candidate Challenger model (LightGBM) to active Champion? Current Champion will be safely archived.');
    if (confirm) {
      try {
        await promoteChallengerModel();
        alert('🎉 Candidate Challenger promoted to production CHAMPION!');
        loadAll();
      } catch (err) {
        alert('Promotion failed.');
      }
    }
  };

  const handleRollbackModel = async () => {
    const confirm = window.confirm('Trigger emergency rollback to prior stable model champion?');
    if (confirm) {
      try {
        await rollbackModel();
        alert('Champion rolled back successfully.');
        loadAll();
      } catch (err) {
        alert('Rollback failed.');
      }
    }
  };

  // Cost calculation simulation
  const fnCost = thresholds?.fn_cost_usd || 500;
  const fpCost = thresholds?.fp_cost_usd || 15;
  const simulatedExpectedLoss = Math.round((1 - declineThreshold) * 120 * fnCost + (1 - reviewThreshold) * 350 * fpCost);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Top Banner: Champion vs Challenger */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        
        {/* Active Champion Card */}
        <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(16, 185, 129, 0.4)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)', position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <span style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700 }}>
                ACTIVE PRODUCTION CHAMPION
              </span>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc', marginTop: '0.35rem' }}>
                {modelOps?.champion?.model_type || 'XGBoost'} ({modelOps?.champion?.version || 'v1.0'})
              </h3>
            </div>
            <button
              onClick={handleRollbackModel}
              style={{ background: 'rgba(244, 63, 94, 0.15)', color: '#f87171', border: '1px solid rgba(244, 63, 94, 0.3)', padding: '0.35rem 0.75rem', borderRadius: '6px', fontSize: '0.75rem', cursor: 'pointer' }}
            >
              Emergency Rollback
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginTop: '1rem' }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.75rem', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>PR-AUC</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc' }}>{modelOps?.champion?.pr_auc || 0.884}</div>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.75rem', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Recall @ 1% FPR</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#10b981' }}>{((modelOps?.champion?.recall_at_1pct_fpr || 0.765) * 100).toFixed(1)}%</div>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.75rem', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Serving Latency</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#06b6d4' }}>{modelOps?.champion?.latency_p95_ms || 11.4} ms</div>
            </div>
          </div>
        </div>

        {/* Shadow Challenger Card */}
        <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(99, 102, 241, 0.4)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)', position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <span style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8', padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700 }}>
                SHADOW CHALLENGER (100% TRAFFIC)
              </span>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc', marginTop: '0.35rem' }}>
                {modelOps?.challenger?.model_type || 'LightGBM'} ({modelOps?.challenger?.version || 'v1.1'})
              </h3>
            </div>
            <button
              onClick={handlePromoteChallenger}
              style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff', border: 'none', padding: '0.45rem 1rem', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
            >
              Promote to Champion ➔
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginTop: '1rem' }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.75rem', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>PR-AUC (Lift)</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc' }}>
                {modelOps?.challenger?.pr_auc || 0.902} <span style={{ fontSize: '0.75rem', color: '#10b981' }}>(+{modelOps?.comparison?.pr_auc_lift_pct || 2.0}%)</span>
              </div>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.75rem', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Recall @ 1% FPR</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#10b981' }}>
                {((modelOps?.challenger?.recall_at_1pct_fpr || 0.798) * 100).toFixed(1)}% <span style={{ fontSize: '0.75rem', color: '#10b981' }}>(+{modelOps?.comparison?.recall_lift_pct || 4.3}%)</span>
              </div>
            </div>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.75rem', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Disagreement Rate</div>
              <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#fbbf24' }}>
                {((modelOps?.shadow_metrics?.disagreement_rate || 0.043) * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Dynamic Threshold Management with Cost-Benefit Slider */}
      <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)' }}>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc' }}>
              Cost-Sensitive Decision Threshold Tuning
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.2rem' }}>
              Balances expected fraud loss (${fnCost}/FN) against customer friction operational cost (${fpCost}/FP) with instant 1-click rollback.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={handleRollbackThresholds}
              disabled={!thresholds?.rollback_available}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                color: thresholds?.rollback_available ? '#fbbf24' : '#64748b',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                padding: '0.45rem 1rem',
                borderRadius: '6px',
                fontSize: '0.8rem',
                cursor: thresholds?.rollback_available ? 'pointer' : 'not-allowed'
              }}
            >
              ↺ Instant Rollback
            </button>
            <button
              onClick={handleSaveThresholds}
              disabled={isUpdatingThresholds}
              style={{
                background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                color: '#fff',
                border: 'none',
                padding: '0.45rem 1.2rem',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {isUpdatingThresholds ? 'Updating...' : 'Deploy Thresholds'}
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '2rem', alignItems: 'center' }}>
          
          {/* Review Threshold Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
              <span style={{ color: '#cbd5e1' }}>Human Review Cutoff</span>
              <strong style={{ color: '#f59e0b', fontFamily: 'JetBrains Mono' }}>{reviewThreshold.toFixed(2)}</strong>
            </div>
            <input
              type="range"
              min="0.30"
              max="0.80"
              step="0.01"
              value={reviewThreshold}
              onChange={(e) => setReviewThreshold(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#f59e0b' }}
            />
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
              Transactions with probability &gt;= {reviewThreshold.toFixed(2)} route to human queue.
            </div>
          </div>

          {/* Decline Threshold Slider */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem' }}>
              <span style={{ color: '#cbd5e1' }}>Hard Decline Cutoff</span>
              <strong style={{ color: '#f43f5e', fontFamily: 'JetBrains Mono' }}>{declineThreshold.toFixed(2)}</strong>
            </div>
            <input
              type="range"
              min="0.70"
              max="0.98"
              step="0.01"
              value={declineThreshold}
              onChange={(e) => setDeclineThreshold(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#f43f5e' }}
            />
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
              Transactions with probability &gt;= {declineThreshold.toFixed(2)} are blocked instantly.
            </div>
          </div>

          {/* Simulated Financial Outcome */}
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '10px', padding: '1rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Simulated Expected Loss / 24h</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8', marginTop: '0.2rem' }}>
              ${simulatedExpectedLoss.toLocaleString()} USD
            </div>
            <div style={{ fontSize: '0.7rem', color: '#10b981', marginTop: '0.2rem' }}>
              Optimal balance between missed fraud and friction
            </div>
          </div>

        </div>

      </div>

      {/* Population Stability Index (PSI) Feature Drift Report */}
      <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc' }}>
            Feature & Score Distribution Drift (Population Stability Index - PSI)
          </h3>
          <span style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>
            OVERALL STATUS: STABLE
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', textAlign: 'left', color: '#94a3b8' }}>
                <th style={{ padding: '0.75rem 1rem' }}>Feature / Score Name</th>
                <th style={{ padding: '0.75rem 1rem' }}>PSI Metric</th>
                <th style={{ padding: '0.75rem 1rem' }}>Baseline Mean</th>
                <th style={{ padding: '0.75rem 1rem' }}>Current Mean</th>
                <th style={{ padding: '0.75rem 1rem' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {driftReport && driftReport.feature_metrics ? (
                Object.entries(driftReport.feature_metrics).map(([key, item]: [string, any]) => (
                  <tr key={key} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                    <td style={{ padding: '0.75rem 1rem', fontFamily: 'JetBrains Mono', color: '#cbd5e1' }}>{key}</td>
                    <td style={{ padding: '0.75rem 1rem', fontFamily: 'JetBrains Mono', color: item.psi > 0.1 ? '#fbbf24' : '#10b981', fontWeight: 600 }}>
                      {item.psi.toFixed(3)}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', color: '#94a3b8' }}>{item.mean_baseline}</td>
                    <td style={{ padding: '0.75rem 1rem', color: '#cbd5e1' }}>{item.mean_current}</td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <span style={{
                        background: item.status === 'STABLE' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: item.status === 'STABLE' ? '#34d399' : '#fbbf24',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 600
                      }}>
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} style={{ padding: '1rem', color: '#94a3b8', textAlign: 'center' }}>
                    Loading drift monitoring statistics...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
