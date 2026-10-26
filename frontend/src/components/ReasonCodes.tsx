import React from 'react';

interface ReasonCodeItem {
  code: string;
  feature: string;
  value: number;
  impact: number;
  description: string;
}

interface ReasonCodesProps {
  reasonCodes: ReasonCodeItem[];
}

export const ReasonCodes: React.FC<ReasonCodesProps> = ({ reasonCodes }) => {
  if (!reasonCodes || reasonCodes.length === 0) {
    return (
      <div style={{ padding: '1rem', color: '#94a3b8', fontSize: '0.85rem' }}>
        No anomalous TreeSHAP feature attributions flagged for this transaction.
      </div>
    );
  }

  const maxImpact = Math.max(...reasonCodes.map(r => Math.abs(r.impact)), 0.1);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {reasonCodes.map((item, idx) => {
        const isRiskIncrease = item.impact > 0;
        const barWidth = Math.min(100, Math.round((Math.abs(item.impact) / maxImpact) * 100));
        const barColor = isRiskIncrease ? 'linear-gradient(90deg, #f43f5e, #fb7185)' : 'linear-gradient(90deg, #10b981, #34d399)';

        return (
          <div
            key={idx}
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
              padding: '0.75rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.35rem'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#f8fafc' }}>
                {item.feature}
              </span>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: isRiskIncrease ? '#fb7185' : '#34d399' }}>
                {isRiskIncrease ? '+' : ''}{item.impact.toFixed(3)} SHAP
              </span>
            </div>

            {/* Impact Bar */}
            <div style={{ width: '100%', height: '6px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{ width: `${barWidth}%`, height: '100%', background: barColor, borderRadius: '3px', transition: 'width 0.4s ease' }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
              <span>Value: <strong style={{ color: '#cbd5e1' }}>{typeof item.value === 'number' ? item.value.toFixed(2) : item.value}</strong></span>
              <span style={{ fontStyle: 'italic' }}>{item.description}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
