import React, { useState, useEffect } from 'react';
import { CaseItem, getCases } from '../api/client';

interface CaseQueueProps {
  onSelectCase: (caseId: string) => void;
}

export const CaseQueue: React.FC<CaseQueueProps> = ({ onSelectCase }) => {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const fetchCaseList = async () => {
    try {
      const data = await getCases(statusFilter === 'ALL' ? undefined : statusFilter);
      if (data && data.cases) {
        setCases(data.cases);
      }
    } catch (err) {
      console.error('Error fetching cases', err);
    }
  };

  useEffect(() => {
    fetchCaseList();
  }, [statusFilter]);

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'critical':
        return <span style={{ background: 'rgba(244, 63, 94, 0.2)', color: '#f43f5e', border: '1px solid rgba(244, 63, 94, 0.4)', padding: '0.2rem 0.6rem', borderRadius: '4px', fontWeight: 700, fontSize: '0.75rem' }}>CRITICAL</span>;
      case 'high':
        return <span style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b', border: '1px solid rgba(245, 158, 11, 0.4)', padding: '0.2rem 0.6rem', borderRadius: '4px', fontWeight: 700, fontSize: '0.75rem' }}>HIGH</span>;
      default:
        return <span style={{ background: 'rgba(6, 182, 212, 0.2)', color: '#06b6d4', border: '1px solid rgba(6, 182, 212, 0.4)', padding: '0.2rem 0.6rem', borderRadius: '4px', fontWeight: 700, fontSize: '0.75rem' }}>MEDIUM</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      open: '#94a3b8',
      investigating: '#06b6d4',
      pending_review: '#f59e0b',
      closed: '#10b981'
    };
    return (
      <span style={{ color: colors[status] || '#cbd5e1', fontWeight: 600, textTransform: 'capitalize' }}>
        ● {status.replace('_', ' ')}
      </span>
    );
  };

  return (
    <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)' }}>
      
      {/* Header & Filter Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f8fafc' }}>
            AML Case Management Queue
          </h2>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            SLA-Prioritized alert correlation rings requiring agentic evidence assembly & compliance review
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Status Filter:</span>
          {['ALL', 'open', 'investigating', 'pending_review', 'closed'].map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              style={{
                background: statusFilter === s ? '#6366f1' : 'rgba(255, 255, 255, 0.05)',
                color: statusFilter === s ? '#fff' : '#94a3b8',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                padding: '0.35rem 0.75rem',
                borderRadius: '6px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                textTransform: 'capitalize'
              }}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Case Queue Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', textAlign: 'left', color: '#94a3b8' }}>
              <th style={{ padding: '0.85rem 1rem' }}>Case Reference</th>
              <th style={{ padding: '0.85rem 1rem' }}>Title & Typology</th>
              <th style={{ padding: '0.85rem 1rem' }}>Subject Entity</th>
              <th style={{ padding: '0.85rem 1rem' }}>Priority</th>
              <th style={{ padding: '0.85rem 1rem' }}>Status</th>
              <th style={{ padding: '0.85rem 1rem' }}>SLA Due</th>
              <th style={{ padding: '0.85rem 1rem' }}>Assigned</th>
              <th style={{ padding: '0.85rem 1rem' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr
                key={c.case_id}
                style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', transition: 'background 0.2s ease' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={{ padding: '0.85rem 1rem', fontFamily: 'JetBrains Mono', fontWeight: 600, color: '#f8fafc' }}>
                  {c.case_id}
                </td>
                <td style={{ padding: '0.85rem 1rem', color: '#e2e8f0', maxWidth: '300px' }}>
                  <div style={{ fontWeight: 600 }}>{c.title}</div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                    {c.alerts_count} aggregated risk alerts
                  </div>
                </td>
                <td style={{ padding: '0.85rem 1rem', fontFamily: 'JetBrains Mono', color: '#06b6d4' }}>
                  {c.subject_account}
                </td>
                <td style={{ padding: '0.85rem 1rem' }}>
                  {getPriorityBadge(c.priority)}
                </td>
                <td style={{ padding: '0.85rem 1rem' }}>
                  {getStatusBadge(c.status)}
                </td>
                <td style={{ padding: '0.85rem 1rem', color: '#fbbf24', fontSize: '0.8rem', fontFamily: 'JetBrains Mono' }}>
                  ⏳ {new Date(c.sla_due_at).toLocaleDateString()} ({Math.max(1, Math.round((new Date(c.sla_due_at).getTime() - Date.now()) / (1000 * 3600)))}h left)
                </td>
                <td style={{ padding: '0.85rem 1rem', color: '#94a3b8' }}>
                  {c.assigned_analyst}
                </td>
                <td style={{ padding: '0.85rem 1rem' }}>
                  <button
                    onClick={() => onSelectCase(c.case_id)}
                    style={{
                      background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                      color: '#fff',
                      border: 'none',
                      padding: '0.45rem 0.9rem',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      boxShadow: '0 0 10px rgba(99, 102, 241, 0.3)'
                    }}
                  >
                    Open Workbench ➔
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
};
