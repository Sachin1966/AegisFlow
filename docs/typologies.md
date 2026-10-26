# AegisFlow AML Typologies & Fraud Ring Specification

## 1. Smurfing (Structuring)
- **Concept**: A primary entity orchestrates multiple sub-threshold deposits ($9,000–$9,800) across fan-in accounts to bypass statutory regulatory reporting thresholds (e.g. $10,000).
- **Pattern**:
  - Phase 1: Multiple source accounts receive rapid, round-number cash/digital deposits under $10,000.
  - Phase 2: Fan-in transfer to a single master account within a short temporal window (< 24 hours).
- **Detection Method**: Deterministic aggregation tool (`smurfing_detector`) checking deposit count, amount bounds, and fan-in ratio.

## 2. Layering
- **Concept**: Rapid, multi-hop transaction sequences traversing intermediary accounts to obscure audit trails and origin of illicit funds.
- **Pattern**:
  - Account A transfers funds to B; B immediately transfers to C; C transfers to D across short time deltas (< 15 minutes per hop).
- **Detection Method**: Directed multi-hop path search and timestamp delta verification (`layering_detector`).

## 3. Round-Tripping
- **Concept**: Circular transaction flows where money exits an account, passes through one or more intermediate nodes, and returns back to the originator.
- **Pattern**:
  - Graph cycle: A -> B -> C -> A within a designated time window.
- **Detection Method**: Directed cycle detection algorithms in NetworkX entity graph processing.

## 4. Shared-Device / IP Fraud Rings
- **Concept**: Multiple distinct customer accounts operating from identical hardware device fingerprints or IP addresses within high velocity windows.
- **Pattern**:
  - High degree centrality on Device or IP nodes in `entity_edges`.
- **Detection Method**: K-hop neighborhood analysis and device sharing degree metrics.
