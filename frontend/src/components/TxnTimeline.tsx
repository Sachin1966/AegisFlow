import React from 'react';

interface TimelineEvent {
  tx_id: string;
  timestamp: string;
  amount: number;
  currency: string;
  channel: string;
  source: string;
  counterparty: string;
  type: string;
  is_sub_threshold: boolean;
  flag?: string;
}

interface TxnTimelineProps {
  events: TimelineEvent[];
}

export const TxnTimeline: React.FC<TxnTimelineProps> = ({ events }) => {
  if (!events || events.length === 0) {
    return (
      <div style={{ padding: '1rem', color: '#94a3b8', fontSize: '0.85rem' }}>
        No historical transaction timeline available.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', position: 'relative' }}>
      {/* Vertical line indicator */}
      <div style={{ position: 'absolute', top: '10px', bottom: '10px', left: '15px', width: '2px', background: 'rgba(255, 255, 255, 0.1)' }} />

      {events.map((evt, idx) => {
        const isStructuring = evt.is_sub_threshold || (evt.amount >= 9000 && evt.amount <= 10000);

        return (
          <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', position: 'relative' }}>
            {/* Timeline bullet */}
            <div
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                background: isStructuring ? '#f59e0b' : '#6366f1',
                boxShadow: isStructuring ? '0 0 8px #f59e0b' : '0 0 6px #6366f1',
                marginTop: '6px',
                zIndex: 2,
                flexShrink: 0
              }}
            />

            {/* Event Card */}
            <div
              style={{
                flex: 1,
                background: 'rgba(255, 255, 255, 0.03)',
                border: isStructuring ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '0.75rem 1rem'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#f8fafc' }}>
                  ${evt.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} {evt.currency}
                </span>
                {isStructuring && (
                  <span style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600 }}>
                    CTR SUB-THRESHOLD ($9.8k)
                  </span>
                )}
                {evt.flag === 'IMMEDIATE_LAYERING_OUTFLOW' && (
                  <span style={{ background: 'rgba(244, 63, 94, 0.2)', color: '#f87171', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600 }}>
                    LAYERING OUTFLOW
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8' }}>
                <span>From <code>{evt.source}</code> ➔ To <code>{evt.counterparty}</code></span>
                <span>Channel: <strong>{evt.channel}</strong></span>
              </div>

              <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.35rem' }}>
                TX ID: <code>{evt.tx_id}</code> • {new Date(evt.timestamp).toLocaleString()}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
