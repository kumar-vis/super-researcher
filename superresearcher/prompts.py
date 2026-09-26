from __future__ import annotations

from typing import Any


ARCHETYPES = [
    "General Research",
    "Exploratory Research",
    "Background Research",
    "Explainer / Primer",
    "Deep Dive",
    "State of the Field",
    "State of the Art",
    "Evidence Review",
    "Decision Support Memo",
    "Executive Brief",
    "Publication-Grade Research Paper",
    "Market Landscape",
    "Market Sizing",
    "Market Forecast",
    "Market Entry Analysis",
    "Market Opportunity Assessment",
    "Industry Analysis",
    "TAM / SAM / SOM Analysis",
    "Pricing Analysis",
    "Unit Economics Analysis",
    "Business Model Analysis",
    "Competitive Intelligence",
    "Competitor Benchmarking",
    "Company Deep Dive",
    "Startup Landscape",
    "Public Company Analysis",
    "Private Company Analysis",
    "Vendor Evaluation",
    "Strategic Positioning Analysis",
    "Product Comparison",
    "Business Strategy",
    "Product Strategy",
    "Corporate Strategy",
    "Build vs Buy Analysis",
    "Cost-Benefit Analysis",
    "ROI Analysis",
    "Scenario Planning",
    "Emerging Technology Feasibility",
    "Technical Feasibility Study",
    "Technology Landscape",
    "Systems Architecture Research",
    "Technical Due Diligence",
    "Infrastructure Analysis",
    "Security Architecture Review",
    "Standards / Protocol Analysis",
    "Scientific Literature Review",
    "Academic Survey",
    "Systematic Review",
    "Meta-Analysis",
    "Hypothesis Validation",
    "Research Gap Analysis",
    "Prior Art Review",
    "Data / Dataset Analysis",
    "Statistical Analysis",
    "Quantitative Modeling",
    "Forecast Modeling",
    "Scenario Modeling",
    "Sensitivity Analysis",
    "Benchmark Dataset Review",
    "Policy Analysis",
    "Regulatory Analysis",
    "Legal Research",
    "Compliance Research",
    "Standards Compliance Analysis",
    "International Regulatory Comparison",
    "Investment Thesis",
    "Venture Investment Analysis",
    "Public Equity Research",
    "Financial Due Diligence",
    "Market Comparables Analysis",
    "Economic Impact Analysis",
    "Macroeconomic Analysis",
    "Geopolitical Analysis",
    "Historical Analysis",
    "Historical Case Study",
    "Technology History",
    "Failure Case Study",
    "Foresight / Futures Study",
    "Long-Term Trend Analysis",
    "Product Research",
    "User Research",
    "Customer Discovery",
    "UX Benchmarking",
    "Operations Research",
    "Supply Chain Analysis",
    "Manufacturing Analysis",
    "Risk Assessment",
    "Safety Analysis",
    "Security Research",
    "Cybersecurity Threat Analysis",
    "Red-Team Review",
    "Ethics / Safety Analysis",
    "Patent Landscape",
    "IP Landscape",
    "Freedom-To-Operate Research",
    "Standards Landscape",
    "Open Source Landscape",
    "Knowledge Base Construction",
    "Healthcare / Clinical Evidence Review",
    "Drug / Therapeutics Research",
    "Public Health Analysis",
    "Climate / Sustainability Analysis",
    "Energy Systems Analysis",
    "Defense / National Security Research",
    "Consumer Behavior Research",
]


RUBRIC_DIMENSIONS = [
    "Research Objective",
    "Decision Context",
    "Audience",
    "Evidence Standard",
    "Research Depth",
    "Research Breadth",
    "Final Source Count",
    "Topic Boundary",
    "Geographic Scope",
    "Time Horizon",
    "Historical Depth",
    "Currentness Requirement",
    "Source Classes",
    "Source Preferences",
    "Inclusion Criteria",
    "Exclusion Criteria",
    "Comparison Set",
    "Key Variables",
    "Analytical Methods",
    "Modeling Depth",
    "Data Requirements",
    "Experiment Requirement",
    "Success Criteria",
    "Claim Granularity",
    "Citation Requirement",
    "Contradiction Handling",
    "Risk Treatment",
    "Assumption Policy",
    "Stakeholder Lens",
    "Confidentiality Boundary",
    "Deliverable Constraints",
    "Follow-Up Interaction",
]


def classifier_prompt(topic: str, context: str) -> str:
    return f"""You are the Archetype Classifier for SuperResearcher.

Classify the user's research request into exactly one primary archetype and zero to eight secondary archetypes.
Use only the allowed archetypes below. Return strict JSON only.

Allowed archetypes:
{ARCHETYPES}

User request:
{topic}

User context:
{context}

Return this JSON shape:
{{
  "primary_archetype": "string",
  "secondary_archetypes": ["string"],
  "rejected_archetypes": [{{"archetype": "string", "reason": "string"}}],
  "classification_rationale": {{
    "primary_reason": "string",
    "secondary_reasons": [{{"archetype": "string", "reason": "string"}}],
    "key_signals": ["string"],
    "ambiguities": ["string"]
  }},
  "expected_research_implications": {{
    "clarification_dimensions": ["string"],
    "source_classes": ["string"],
    "quality_gates": ["string"],
    "analysis_methods": ["string"],
    "report_sections": ["string"]
  }},
  "user_confirmation_required": true
}}
"""


def rubric_prompt(topic: str, context: str, archetypes: dict[str, Any]) -> str:
    return f"""You are the Clarification Rubric Assessor for SuperResearcher.

Assess whether each rubric dimension is explicit, inferable, ambiguous, missing, or not_applicable.
Do not perform research. Return strict JSON only.

Topic:
{topic}

Context:
{context}

Selected archetypes:
{archetypes}

Rubric dimensions:
{RUBRIC_DIMENSIONS}

Return this JSON shape:
{{
  "rubric_assessment": [
    {{
      "dimension": "string",
      "rubric_question": "string",
      "status": "explicit | inferable | ambiguous | missing | not_applicable",
      "known_or_inferred_value": "string | null",
      "basis": "string",
      "why_it_matters": "string",
      "risk_if_unresolved": "string",
      "downstream_impact": {{
        "clarification_questions": true,
        "source_strategy": true,
        "quality_gates": true,
        "analysis_methods": true,
        "report_structure": true,
        "publication_quality": true
      }},
      "should_ask": true,
      "default_assumption": "string | null"
    }}
  ],
  "summary": {{
    "explicit_count": 0,
    "inferable_count": 0,
    "ambiguous_count": 0,
    "missing_count": 0,
    "not_applicable_count": 0,
    "ask_count": 0,
    "highest_risk_missing_dimensions": ["string"],
    "safe_defaults": [{{"dimension": "string", "default_assumption": "string"}}]
  }}
}}
"""


def heuristic_prompt(level: int, protocol: dict[str, Any]) -> str:
    topic = protocol["research_topic"]["user_input"]
    scope = protocol["scope"]
    source = protocol["source_requirements"]
    analysis = protocol["analysis_requirements"]
    level_names = {
        1: "baseline orientation: vocabulary, definitions, synonyms, acronyms, core concepts, entities, taxonomy, obvious source classes",
        2: "structured domain mapping: subtopics, stakeholders, ecosystem players, variables, drivers, constraints, use cases, source targets",
        3: "evidence and analysis mapping: research questions, indicators, datasets, benchmarks, methods, model inputs, assumptions",
        4: "critical and historical mapping: historical threads, prior attempts, opposing views, failure modes, criticism, contradictions, risks",
        5: "frontier and synthesis mapping: future work, novel hypotheses, analogy domains, cross-domain applications, emerging signals, second-order effects",
    }
    query_key = {
        1: "baseline_search_queries",
        2: "structured_search_queries",
        3: "analysis_ready_search_queries",
        4: "critical_search_queries",
        5: "frontier_search_queries",
    }[level]
    return f"""You are generating a Level {level} heuristic map for SuperResearcher.

Level {level} means {level_names[level]}.
Generate search-planning heuristics only. Do not cite sources or make final claims.
Return strict JSON only. Include at least 12 useful query objects in `{query_key}`.

Input:
{{
  "research_topic": {topic!r},
  "objective": {scope.get("objective", "")!r},
  "decision_context": {scope.get("decision_context", "")!r},
  "audience": {scope.get("audience", "")!r},
  "topic_boundary": {scope.get("topic_boundary", "")!r},
  "geographic_scope": {scope.get("geographic_scope", "")!r},
  "time_horizon": {scope.get("time_horizon", "")!r},
  "historical_depth": {scope.get("historical_depth", "")!r},
  "must_include": {scope.get("must_include", [])},
  "must_exclude": {scope.get("must_exclude", [])},
  "required_source_classes": {source.get("required_source_classes", [])},
  "preferred_sources": {source.get("preferred_sources", [])},
  "time_buckets": {source.get("time_buckets", [])},
  "source_recency_policy": {source.get("source_recency_policy", "")!r},
  "evidence_dimensions": {source.get("evidence_dimensions", [])},
  "key_variables": {analysis.get("key_variables", [])},
  "analytical_methods": {analysis.get("analytical_methods", [])}
}}

Return JSON with these required top-level keys:
{{
  "level": {level},
  "purpose": "string",
  "canonical_topic": "string",
  "scope_interpretation": {{
    "included": [],
    "excluded": [],
    "geographic_focus": "string",
    "time_focus": "string",
    "historical_depth_needed": "string"
  }},
  "focus_areas": [
    {{
      "name": "string",
      "why_it_matters_for_search": "string",
      "candidate_query_patterns": ["string"],
      "source_classes": ["string"],
      "evidence_dimensions": ["string"]
    }}
  ],
  "{query_key}": [
    {{
      "query": "string",
      "intended_use": "string",
      "expected_source_class": "string",
      "linked_item": "string"
    }}
  ]
}}
"""
