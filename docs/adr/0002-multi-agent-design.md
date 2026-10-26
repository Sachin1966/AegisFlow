# ADR 0002: Multi-Agent Architecture for AML Case Investigation

## Status
Accepted

## Context
Investigating anti-money-laundering (AML) cases and drafting Suspicious Activity Reports (SARs) requires multi-faceted analysis across transaction networks, behavioral typologies, entity relationships, and public adverse media. Single monolithic LLM prompts suffer from hallucinations, context truncation, and lack of deterministic validation.

## Decision
We implement a multi-agent investigation workbench orchestrated via **LangGraph**:
1. **Supervisor Agent**: Manages execution order, evaluates evidence sufficiency, enforces turn limits (max 12 turns).
2. **Link Analyst Agent**: Examines entity graph relationships, k-hop neighborhoods, and paths to known fraud.
3. **Pattern Analyst Agent**: Runs deterministic typology algorithms for smurfing, layering, and round-tripping.
4. **Adverse Media Researcher**: Queries dense + sparse hybrid RAG index in Qdrant with entity filtering and cross-encoder reranking.
5. **Narrative Writer Agent**: Constructs SAR narratives strictly from typed evidence findings.
6. **QA Reviewer Agent**: Performs adversarial verification of narrative claims against evidence packs.

## Principles
- LLM agents interpret data; deterministic Python tools compute graph metrics and typology hits.
- Autonomous SAR submission is strictly forbidden. Human analyst sign-off is required for final export.
