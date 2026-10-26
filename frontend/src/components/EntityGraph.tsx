import React, { useState } from 'react';
import { GraphData, GraphNode, GraphEdge } from '../api/client';

interface EntityGraphProps {
  data: GraphData | null;
  onNodeSelect?: (node: GraphNode) => void;
}

export const EntityGraph: React.FC<EntityGraphProps> = ({ data, onNodeSelect }) => {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div style={{ height: '320px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
        No entity network graph data loaded.
      </div>
    );
  }

  // Pre-calculated force layout coordinates for clean deterministic visual rendering
  const positions: Record<string, { x: number; y: number }> = {
    [data.target_account]: { x: 200, y: 160 },
    'ACCT-COUNTERPART-1': { x: 380, y: 120 },
    'DEV-9812': { x: 280, y: 260 },
    'IP-192.168.1.45': { x: 120, y: 260 },
    'ACCT-KNOWN-FRAUD-99': { x: 520, y: 180 }
  };

  const getNodeColor = (node: GraphNode) => {
    if (node.risk_score >= 0.90) return '#f43f5e'; // Rose (Critical)
    if (node.risk_score >= 0.70) return '#f59e0b'; // Amber (High/Medium)
    return '#10b981'; // Emerald (Low)
  };

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'account': return '🏦';
      case 'device': return '💻';
      case 'ip': return '🌐';
      case 'merchant': return '🛍️';
      default: return '📍';
    }
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '360px', background: 'rgba(0, 0, 0, 0.4)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)', overflow: 'hidden' }}>
      
      {/* Graph Toolbar / Legend */}
      <div style={{ position: 'absolute', top: '12px', left: '16px', zIndex: 10, display: 'flex', gap: '1rem', fontSize: '0.75rem', background: 'rgba(15, 23, 42, 0.8)', padding: '0.4rem 0.8rem', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f43f5e' }}></span> Sanctioned / Fraud</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b' }}></span> Intermediary Shell</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#6366f1' }}></span> Target Subject</span>
      </div>

      <svg width="100%" height="100%" viewBox="0 0 640 360" style={{ cursor: 'grab' }}>
        <defs>
          <linearGradient id="fraudPathGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#f43f5e" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Edges */}
        {data.edges.map((edge, idx) => {
          const p1 = positions[edge.source] || { x: 150 + (idx * 60), y: 150 };
          const p2 = positions[edge.target] || { x: 300 + (idx * 50), y: 200 };
          const isFraudPath = data.shortest_path_to_fraud.includes(edge.source) && data.shortest_path_to_fraud.includes(edge.target);

          return (
            <g key={idx}>
              <line
                x1={p1.x}
                y1={p1.y}
                x2={p2.x}
                y2={p2.y}
                stroke={isFraudPath ? '#f43f5e' : 'rgba(255, 255, 255, 0.2)'}
                strokeWidth={isFraudPath ? 3 : 1.5}
                strokeDasharray={edge.type === 'SHARED_HARDWARE' ? '4 3' : undefined}
                filter={isFraudPath ? 'url(#glow)' : undefined}
              />
              {edge.label && (
                <text
                  x={(p1.x + p2.x) / 2}
                  y={(p1.y + p2.y) / 2 - 6}
                  fill="#94a3b8"
                  fontSize="10"
                  textAnchor="middle"
                  fontFamily="Inter"
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {data.nodes.map((node) => {
          const pos = positions[node.id] || { x: 300, y: 180 };
          const isTarget = node.id === data.target_account;
          const nodeColor = getNodeColor(node);

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              onClick={() => {
                setSelectedNode(node);
                if (onNodeSelect) onNodeSelect(node);
              }}
              style={{ cursor: 'pointer' }}
            >
              {/* Outer pulsing ring for target */}
              {isTarget && (
                <circle r="26" fill="none" stroke="#6366f1" strokeWidth="2" opacity="0.6">
                  <animate attributeName="r" values="24;32;24" dur="2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.8;0.1;0.8" dur="2s" repeatCount="indefinite" />
                </circle>
              )}

              <circle
                r="18"
                fill={nodeColor}
                stroke="#ffffff"
                strokeWidth="2"
                filter="url(#glow)"
              />
              <text y="5" textAnchor="middle" fontSize="12">
                {getNodeIcon(node.type)}
              </text>
              <text
                y="32"
                textAnchor="middle"
                fill="#f8fafc"
                fontSize="11"
                fontWeight="600"
                fontFamily="Inter"
              >
                {node.label}
              </text>
              <text
                y="44"
                textAnchor="middle"
                fill="#94a3b8"
                fontSize="9"
                fontFamily="JetBrains Mono"
              >
                Risk: {(node.risk_score * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}
      </svg>

      {/* Node Inspector Drawer */}
      {selectedNode && (
        <div style={{ position: 'absolute', bottom: '12px', right: '16px', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(99, 102, 241, 0.4)', borderRadius: '10px', padding: '0.85rem 1.2rem', backdropFilter: 'blur(12px)', fontSize: '0.8rem', minWidth: '220px', zIndex: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
            <span style={{ fontWeight: 700, color: '#f8fafc' }}>{selectedNode.label}</span>
            <button onClick={() => setSelectedNode(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>✕</button>
          </div>
          <div style={{ color: '#cbd5e1' }}>Entity ID: <code>{selectedNode.id}</code></div>
          <div style={{ color: '#cbd5e1' }}>Type: <strong style={{ textTransform: 'capitalize' }}>{selectedNode.type}</strong></div>
          <div style={{ color: getNodeColor(selectedNode), fontWeight: 600, marginTop: '0.2rem' }}>
            Calculated Risk Score: {(selectedNode.risk_score * 100).toFixed(1)}%
          </div>
        </div>
      )}
    </div>
  );
};
