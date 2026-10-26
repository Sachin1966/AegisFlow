import React, { useState } from 'react';
import { LiveDecisions } from './pages/LiveDecisions';
import { CaseQueue } from './pages/CaseQueue';
import { CaseWorkspace } from './pages/CaseWorkspace';
import { ModelOps } from './pages/ModelOps';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'live' | 'queue' | 'workspace' | 'modelops'>('dashboard');
  const [activeCaseId, setActiveCaseId] = useState<string>('CASE-2026-001');

  const handleSelectCase = (caseId: string) => {
    setActiveCaseId(caseId);
    setActiveTab('workspace');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#070a13', color: '#f3f4f6', fontFamily: 'Inter, sans-serif' }}>
      
      {/* Navigation Header */}
      <nav style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.9rem 2rem',
        background: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }} onClick={() => setActiveTab('dashboard')}>
          <div style={{
            width: '38px',
            height: '38px',
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.2rem',
            boxShadow: '0 0 15px rgba(99, 102, 241, 0.4)'
          }}>
            🛡️
          </div>
          <div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.5px', background: 'linear-gradient(to right, #ffffff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              AegisFlow
            </div>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
              Real-Time Payment Fraud & Agentic AML Platform
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', gap: '0.4rem', background: 'rgba(0, 0, 0, 0.35)', padding: '0.35rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          {[
            { id: 'dashboard', label: 'Executive Dashboard' },
            { id: 'live', label: 'Live Decision Feed' },
            { id: 'queue', label: 'Alerts & Cases' },
            { id: 'workspace', label: '🤖 AML Workbench' },
            { id: 'modelops', label: '⚙️ ModelOps & Governance' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                padding: '0.5rem 1.15rem',
                border: 'none',
                background: activeTab === tab.id ? '#6366f1' : 'transparent',
                color: activeTab === tab.id ? '#fff' : '#94a3b8',
                fontWeight: 600,
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                transition: 'all 0.2s ease',
                boxShadow: activeTab === tab.id ? '0 0 12px rgba(99, 102, 241, 0.4)' : 'none'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Microservice Health Indicators */}
        <div style={{ display: 'flex', gap: '0.6rem', fontSize: '0.75rem' }}>
          {[
            { name: 'Ingestion', port: '8001' },
            { name: 'Scoring', port: '8002' },
            { name: 'Casework', port: '8003' },
            { name: 'Investigator', port: '8004' }
          ].map(svc => (
            <div
              key={svc.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.3rem 0.65rem',
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '20px',
                fontSize: '0.72rem'
              }}
            >
              <span style={{ width: 7, height: 7, borderRadius: '50%', backgroundColor: '#10b981', boxShadow: '0 0 6px #10b981' }} />
              <span style={{ color: '#cbd5e1' }}>{svc.name}</span>
            </div>
          ))}
        </div>
      </nav>

      {/* Main Content Area */}
      <main style={{ maxWidth: '1440px', margin: '2rem auto', padding: '0 2rem' }}>
        
        {/* Tab 1: Executive Dashboard */}
        {activeTab === 'dashboard' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Top Metrics Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.5rem' }}>
              <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)' }}>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase' }}>24h Ingested Volume</div>
                <div style={{ fontSize: '2rem', fontWeight: 700, marginTop: '0.25rem', color: '#f8fafc' }}>$4,821,900</div>
                <div style={{ fontSize: '0.8rem', color: '#10b981', marginTop: '0.2rem' }}>▲ 14.2% vs baseline</div>
              </div>

              <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)' }}>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase' }}>Scoring Latency (p95)</div>
                <div style={{ fontSize: '2rem', fontWeight: 700, marginTop: '0.25rem', color: '#06b6d4' }}>11.4 ms</div>
                <div style={{ fontSize: '0.8rem', color: '#10b981', marginTop: '0.2rem' }}>⚡ XGBoost Champion + SHAP</div>
              </div>

              <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)' }}>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase' }}>Active AML Alerts</div>
                <div style={{ fontSize: '2rem', fontWeight: 700, marginTop: '0.25rem', color: '#f59e0b' }}>4</div>
                <div style={{ fontSize: '0.8rem', color: '#fbbf24', marginTop: '0.2rem' }}>2 Structuring / Smurfing Rings</div>
              </div>

              <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)' }}>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase' }}>Investigation Faithfulness</div>
                <div style={{ fontSize: '2rem', fontWeight: 700, marginTop: '0.25rem', color: '#10b981' }}>100%</div>
                <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.2rem' }}>Zero unbacked claims via QA pass</div>
              </div>
            </div>

            {/* Middle Section: Velocity & Decision Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem' }}>
              
              <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                  <span style={{ fontWeight: 600, fontSize: '1.1rem', color: '#f8fafc' }}>Payment Decision Mix & Velocity</span>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Sliding Windows: 1m / 1h / 24h</span>
                </div>

                <div style={{ height: '180px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', borderBottom: '1px dashed rgba(255, 255, 255, 0.1)', paddingBottom: '0.5rem' }}>
                  <div style={{ width: '18%', height: '88%', background: 'linear-gradient(to top, #10b981, #34d399)', borderRadius: '8px 8px 0 0', position: 'relative' }}>
                    <span style={{ position: 'absolute', top: '-24px', left: '25%', fontWeight: 700, fontSize: '0.8rem' }}>88.4%</span>
                  </div>
                  <div style={{ width: '18%', height: '24%', background: 'linear-gradient(to top, #f59e0b, #fbbf24)', borderRadius: '8px 8px 0 0', position: 'relative' }}>
                    <span style={{ position: 'absolute', top: '-24px', left: '25%', fontWeight: 700, fontSize: '0.8rem' }}>8.1%</span>
                  </div>
                  <div style={{ width: '18%', height: '12%', background: 'linear-gradient(to top, #f43f5e, #fb7185)', borderRadius: '8px 8px 0 0', position: 'relative' }}>
                    <span style={{ position: 'absolute', top: '-24px', left: '25%', fontWeight: 700, fontSize: '0.8rem' }}>3.5%</span>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-around', marginTop: '0.75rem', fontSize: '0.85rem', color: '#94a3b8' }}>
                  <div>APPROVE (88.4%)</div>
                  <div>REVIEW (8.1%)</div>
                  <div>DECLINE (3.5%)</div>
                </div>
              </div>

              {/* Injected Typology Alerts */}
              <div style={{ background: 'rgba(18, 24, 38, 0.75)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '16px', padding: '1.5rem', backdropFilter: 'blur(12px)' }}>
                <div style={{ fontWeight: 600, fontSize: '1.1rem', color: '#f8fafc', marginBottom: '1rem' }}>
                  Active Detected Typologies
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ padding: '0.85rem', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#fbbf24' }}>Smurfing (Structuring)</div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>8 deposits $9.2k-$9.85k within 48h to evade CTR</div>
                  </div>
                  <div style={{ padding: '0.85rem', background: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '8px' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#f87171' }}>Shared Device Hardware Ring</div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>DEV-9812 shared across 6 high-risk accounts</div>
                  </div>
                  <div style={{ padding: '0.85rem', background: 'rgba(6, 182, 212, 0.1)', border: '1px solid rgba(6, 182, 212, 0.3)', borderRadius: '8px' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#22d3ee' }}>Sanctioned Entity Proximity</div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>2-hop connection to OFAC entity ACCT-99</div>
                  </div>
                </div>
              </div>

            </div>

          </div>
        )}

        {/* Tab 2: Live Decision Feed */}
        {activeTab === 'live' && <LiveDecisions />}

        {/* Tab 3: Case Queue */}
        {activeTab === 'queue' && <CaseQueue onSelectCase={handleSelectCase} />}

        {/* Tab 4: Agentic AML Workspace */}
        {activeTab === 'workspace' && <CaseWorkspace caseId={activeCaseId} />}

        {/* Tab 5: ModelOps & Governance */}
        {activeTab === 'modelops' && <ModelOps />}

      </main>

    </div>
  );
};
