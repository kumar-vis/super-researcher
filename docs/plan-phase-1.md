#Phase 1#

**Phase 1: Clarify Key Steps**

1. Parse the user’s topic/request.

2. Infer the research archetype,

3. Identify ambiguous or missing research dimensions.

4. Rank missing dimensions by downstream impact.

5. Ask the minimum necessary clarifying questions.

6. Apply explicit default assumptions for anything not asked or not answered.

7. Convert answers into a structured research-protocol.

9. Pass the protocol to Phase 2 as the source-of-truth research contract.

When SuperResearcher is called in OpenClaw (command /SuperResearcher) - it will ask the user for two things:
1. Research Topic
2. Research context (Why this research is needed, Who is the audience)

The user inputs are saved in variables as user input, because we will need to reference them later and will serve as anchor of project goals. The user inputs here are then passed to an LLM to classify research archetypes, in the following list. LLM prompt for classification is listed below as well.


```md
### Research Archetypes

**General Purpose**
- General Research
- Exploratory Research
- Background Research
- Explainer / Primer
- Deep Dive
- State of the Field
- State of the Art
- Evidence Review
- Decision Support Memo
- Executive Brief
- Publication-Grade Research Paper

**Market / Industry**
- Market Landscape
- Market Sizing
- Market Forecast
- Market Entry Analysis
- Market Opportunity Assessment
- Demand Analysis
- Supply Analysis
- Demand-Supply Outlook
- Industry Analysis
- Industry Structure Analysis
- Industry Value Chain
- Industry Profit Pool Analysis
- Industry Trend Analysis
- Sector Deep Dive
- TAM / SAM / SOM Analysis
- Pricing Analysis
- Unit Economics Analysis
- Business Model Analysis
- Adoption Curve Analysis
- Customer Segment Analysis
- Go-To-Market Research
- Distribution Channel Analysis

**Competitive / Company**
- Competitive Intelligence
- Competitor Benchmarking
- Company Deep Dive
- Startup Landscape
- Public Company Analysis
- Private Company Analysis
- Vendor Evaluation
- Partner Evaluation
- M&A Target Research
- Strategic Positioning Analysis
- Moat Analysis
- Product Comparison
- Feature Benchmarking
- Pricing Benchmarking
- Customer Review Analysis

**Strategy / Business**
- Business Strategy
- Product Strategy
- Corporate Strategy
- Customer Strategy
- Operating Strategy
- Growth Strategy
- Platform Strategy
- Ecosystem Strategy
- Monetization Strategy
- Procurement Strategy
- Build vs Buy Analysis
- Make vs Partner Analysis
- Cost-Benefit Analysis
- ROI Analysis
- Risk-Reward Analysis
- Scenario Planning
- Strategic Options Analysis

**Technology / Engineering**
- Emerging Technology Feasibility
- Technical Feasibility Study
- Technology Landscape
- Technology Roadmap
- Systems Architecture Research
- Engineering Design Review
- Technical Due Diligence
- Infrastructure Analysis
- Scalability Analysis
- Reliability Analysis
- Performance Benchmarking
- Security Architecture Review
- Software Architecture Review
- Hardware Architecture Review
- Manufacturing Feasibility
- Deployment Feasibility
- Interoperability Analysis
- Standards / Protocol Analysis

**Science / Academic**
- Scientific Literature Review
- Academic Survey
- Systematic Review
- Meta-Analysis
- Theory Review
- Methods Review
- Experimental Design
- Hypothesis Validation
- Replication Study Planning
- Research Gap Analysis
- Citation Network Analysis
- Prior Art Review
- Field Mapping
- Research Agenda Development

**Data / Quantitative**
- Data / Dataset Analysis
- Statistical Analysis
- Quantitative Modeling
- Forecast Modeling
- Scenario Modeling
- Sensitivity Analysis
- Causal Analysis
- Econometric Analysis
- Simulation Study
- Benchmark Dataset Review
- Metrics Definition
- Measurement Framework
- Model Evaluation
- Error Analysis

**Policy / Legal / Regulatory**
- Policy Analysis
- Regulatory Analysis
- Legal Research
- Compliance Research
- Standards Compliance Analysis
- Rulemaking Analysis
- Public Policy Impact Assessment
- Government Program Analysis
- Legislative Analysis
- Litigation / Case Law Review
- Antitrust Analysis
- Privacy / Data Governance Research
- Safety Regulation Analysis
- International Regulatory Comparison

**Finance / Investment**
- Investment Thesis
- Venture Investment Analysis
- Public Equity Research
- Private Market Research
- Financial Due Diligence
- Market Comparables Analysis
- Valuation Research
- Business Risk Analysis
- Capital Allocation Analysis
- Fundraising Landscape
- Macro Investment Research
- Sector Investment Outlook

**Economics / Geopolitics**
- Economic Impact Analysis
- Macroeconomic Analysis
- Microeconomic Analysis
- Labor Market Analysis
- Productivity Analysis
- Trade Analysis
- Industrial Policy Analysis
- Geopolitical Analysis
- Country Risk Analysis
- Regional Market Analysis
- Supply Chain Geopolitics
- Resource / Commodity Analysis

**Historical / Foresight**
- Historical Analysis
- Historical Case Study
- Technology History
- Business History
- Policy History
- Failure Case Study
- Lessons-Learned Analysis
- Foresight / Futures Study
- Long-Term Trend Analysis
- Horizon Scanning
- Weak Signal Analysis
- Future Scenario Analysis

**Product / User / Design**
- Product Research
- User Research
- Customer Discovery
- Jobs-To-Be-Done Research
- Persona Research
- Workflow Analysis
- UX Benchmarking
- Usability Research
- Product-Market Fit Analysis
- Feature Opportunity Analysis
- Roadmap Research
- Design Pattern Research

**Operations / Supply Chain**
- Operations Research
- Process Analysis
- Workflow Optimization
- Supply Chain Analysis
- Logistics Analysis
- Procurement Analysis
- Capacity Planning
- Manufacturing Analysis
- Quality Control Research
- Cost Structure Analysis
- Bottleneck Analysis
- Resilience Analysis

**Risk / Safety / Security**
- Risk Assessment
- Safety Analysis
- Security Research
- Cybersecurity Threat Analysis
- Incident Analysis
- Crisis Analysis
- Failure Mode Analysis
- Hazard Analysis
- Reliability / Resilience Research
- Red-Team Review
- Ethics / Safety Analysis
- Trust and Safety Research

**IP / Standards / Knowledge Assets**
- Patent Landscape
- IP Landscape
- Prior Art Search
- Freedom-To-Operate Research
- Standards Landscape
- Protocol Landscape
- Open Source Landscape
- Knowledge Base Construction
- Taxonomy Construction
- Ontology Research

**Domain-Specific**
- Healthcare / Clinical Evidence Review
- Drug / Therapeutics Research
- Public Health Analysis
- Education / Learning Research
- Climate / Sustainability Analysis
- Environmental Impact Analysis
- Energy Systems Analysis
- Transportation Systems Analysis
- Aerospace / Aviation Research
- Defense / National Security Research
- Agriculture / Food Systems Research
- Real Estate / Urban Planning Research
- Media / Narrative Analysis
- Social / Cultural Analysis
- Consumer Behavior Research
```


```md
You are the Archetype Classifier for SuperResearcher.

Your job is to classify a user's research request into one primary research archetype and a small set of secondary archetypes. Archetypes determine clarification questions, source strategy, quality gates, analysis methods, and report structure, so precision matters.

## Inputs

You will receive the following variables:

- `{{USER_REQUEST}}`
  - The raw research topic or question from the user.

- `{{AVAILABLE_ARCHETYPES}}`
  - The complete allowed archetype taxonomy.
  - You must only choose archetypes from this list.

- `{{USER_CONTEXT}}`
  - Optional known user preferences, audience, organization, prior answers, or constraints.
  - If no context is available, this may be empty.

## Core Rules

1. Choose exactly one `primary_archetype`.
2. Choose zero to 10 `secondary_archetypes`.
3. Use only archetypes from `{{AVAILABLE_ARCHETYPES}}`.
4. Do not invent new archetype names.
5. Prefer fewer, stronger archetypes over many weakly related ones.
6. Select an archetype only if it changes at least one of:
   - clarification questions
   - source classes
   - quality gates
   - analysis methods
   - report structure
7. Do not select archetypes merely because they are adjacent or interesting.
8. If the request is vague, use the closest broad archetype from `{{AVAILABLE_ARCHETYPES}}` and mark uncertainty in `ambiguities`.
9. If the request asks for a publication-quality paper, include the closest publication/reporting archetype from `{{AVAILABLE_ARCHETYPES}}` as a secondary archetype unless it is already the dominant intent.
10. If the request asks for opportunity, market, business potential, or commercial prospects, consider market/business archetypes.
11. If the request asks for feasibility, whether something can work, technical constraints, or scaling, consider technical/feasibility archetypes.
12. If the request asks for forecast, projection, future, outlook, or a time-based estimate, consider forecast/scenario archetypes.
13. If the request mentions laws, agencies, jurisdictions, certification, compliance, or regulation, consider policy/regulatory archetypes.
14. If the request mentions companies, competitors, vendors, startups, products, or market players, consider competitive/company archetypes.
15. If the request mentions research papers, science, literature, studies, evidence, or academic debate, consider science/academic archetypes.
16. If the request implies calculations, modeling, scenarios, sensitivity, data analysis, charts, or experiments, consider data/quantitative archetypes.
17. If the request involves historical lessons, prior attempts, old reports, prior art, or long timelines, consider historical/foresight archetypes.
18. If multiple archetypes overlap, choose the one that most directly affects the research plan.
19. Do not overfit to keywords. Use the full meaning of `{{USER_REQUEST}}`.
20. Always identify ambiguity and explain what would change the classification.

## Selection Heuristics

Choose the `primary_archetype` based on the dominant job-to-be-done in `{{USER_REQUEST}}`.

Use these general patterns:

- If the request is broad understanding, choose the closest broad/background/deep-dive archetype.
- If the request is commercial opportunity or business attractiveness, choose the closest market/business archetype.
- If the request is whether something can work or scale, choose the closest feasibility/technical archetype.
- If the request is projection, outlook, future scenarios, or adoption over time, choose the closest forecast/scenario archetype.
- If the request is academic-style evidence synthesis, choose the closest literature-review or publication-grade archetype.
- If the request is comparing companies, products, vendors, or market players, choose the closest competitive/company archetype.
- If the request is legal, policy, compliance, or government-facing, choose the closest policy/legal/regulatory archetype.
- If the request is investment-oriented, choose the closest finance/investment archetype.
- If the request is validating a claim or hypothesis, choose the closest hypothesis/evidence-review archetype.
- If the request is about designing, building, or evaluating a system, choose the closest engineering/systems archetype.

## Precision Guardrails

Before finalizing, silently ask:

1. Would removing this archetype change the clarifying questions?
2. Would removing this archetype change source acquisition?
3. Would removing this archetype change quality gates?
4. Would removing this archetype change analysis methods?
5. Would removing this archetype change the final report structure?

If the answer is no to all five, remove the archetype.

## Output Requirements

Return strict JSON only. No markdown, no commentary.

Use this schema:

{
  "primary_archetype": "string",
  "secondary_archetypes": ["string"],
  "rejected_archetypes": [
    {
      "archetype": "string",
      "reason": "string"
    }
  ],
  "classification_rationale": {
    "primary_reason": "string",
    "secondary_reasons": [
      {
        "archetype": "string",
        "reason": "string"
      }
    ],
    "key_signals": ["string"],
    "ambiguities": ["string"]
  },
  "expected_research_implications": {
    "clarification_dimensions": ["string"],
    "source_classes": ["string"],
    "quality_gates": ["string"],
    "analysis_methods": ["string"],
    "report_sections": ["string"]
  },
  "user_confirmation_required": true
}

## Validation Rules

Before returning, verify:

1. `primary_archetype` exactly matches one item from `{{AVAILABLE_ARCHETYPES}}`.
2. Every item in `secondary_archetypes` exactly matches one item from `{{AVAILABLE_ARCHETYPES}}`.
3. Every item in `rejected_archetypes[].archetype` exactly matches one item from `{{AVAILABLE_ARCHETYPES}}`.
4. `secondary_archetypes` does not include `primary_archetype`.
5. `secondary_archetypes` has no duplicates.
6. `secondary_archetypes` has no more than eight items.
7. The JSON is valid and parseable.
```

User will then be asked clarifying questions based on results of a rubric

| Rubric Dimension | Atomic Rubric Question |
|---|---|
| Research Objective | Is the primary objective of the research known, including whether the user wants to learn, decide, compare, forecast, validate, publish, invest, build, or persuade? |
| Decision Context | Is the real-world decision, action, or strategic judgment that this research is meant to inform known? |
| Audience | Is the intended audience for the research output known, including their expected expertise level, role, and tolerance for technical detail? |
| Evidence Standard | Is the required evidence standard known, including whether the output should be exploratory, decision-grade, publication-grade, legally defensible, scientifically rigorous, or directionally useful? |
| Research Depth | Is the desired depth of research known, including whether the user expects a quick overview, comprehensive deep dive, systematic review, or original analysis? |
| Topic Boundary | Is the boundary of the topic known, including what subdomains, applications, technologies, markets, actors, or use cases should be included or excluded? |
| Geographic Scope | Is the geographic or jurisdictional scope of the research known, including whether the research should be global, country-specific, regional, city-specific, or comparative across geographies? |
| Time Horizon | Is the time horizon to be used for searching, forecasting, analysis, and conclusions known? |
| Historical Depth | Is the historical lookback period known, including whether older literature, prior art, failed attempts, legacy systems, or long-run historical analogs should be included? |
| Currentness Requirement | Is the required freshness of sources known, including whether recent developments, current market conditions, latest regulations, or real-time data materially matter? |
| Source Classes | Are the required classes of sources known, such as academic papers, government documents, company filings, patents, standards, datasets, news, expert commentary, market reports, or primary interviews? |
| Source Preferences | Are any preferred, trusted, disallowed, or mandatory sources known? |
| Inclusion Criteria | Are the criteria for deciding which sources, cases, companies, datasets, studies, or examples belong in the research corpus known? |
| Exclusion Criteria | Are the criteria for deciding which sources, cases, companies, datasets, studies, or examples should be excluded from the research corpus known? |
| Comparison Set | Is the comparison set known, including alternatives, competitors, historical analogs, substitute technologies, benchmark companies, or baseline scenarios? |
| Key Variables | Are the core variables the research must analyze known, such as cost, adoption, performance, risk, demand, supply, regulation, technical maturity, or user behavior? |
| Analytical Methods | Are the analytical methods expected by the user known, such as qualitative synthesis, market sizing, scenario modeling, sensitivity analysis, statistical analysis, causal analysis, simulation, or technical modeling? |
| Modeling Depth | Is the expected depth of quantitative modeling known, including whether the report needs explicit assumptions, formulas, scenarios, sensitivity ranges, and reproducible calculations? |
| Data Requirements | Are the datasets, metrics, measurements, or quantitative inputs needed for the research known? |
| Experiment Requirement | Is it known whether the research should include code execution, data analysis, simulations, experiments, charts, or reproducible computational work? |
| Success Criteria | Are the criteria for judging whether the final research output is successful known? |
| Claim Granularity | Is the desired granularity of claims known, including whether the user wants high-level conclusions, section-level findings, atomic cited claims, or full evidence tables? |
| Citation Requirement | Is the required citation style and traceability level known, including whether every factual claim needs inline citations and source-line support? |
| Contradiction Handling | Is it known how the report should handle conflicting evidence, uncertainty, unresolved disagreements, and competing interpretations? |
| Risk Treatment | Is it known how conservative the research should be when evidence is weak, uncertain, biased, stale, or contradictory? |
| Assumption Policy | Is it known which assumptions the system may safely make by default and which assumptions require explicit user confirmation? |
| Stakeholder Lens | Is the stakeholder perspective known, including whether the research should be written from the view of an operator, investor, policymaker, customer, researcher, founder, executive, or engineer? |
| Confidentiality Boundary | Is it known whether the research may use private context, company information, internal assumptions, or only public sources? |
| Deliverable Constraints | Are any constraints on length, style, tone, language, citation format, deadline, file format, or publication venue known? |
| Follow-Up Interaction | Is it known whether the user wants an interactive workflow with section-by-section feedback or a mostly autonomous end-to-end research run? |




```md
You are the Clarification Rubric Assessor for SuperResearcher.

Your job is to inspect a user's research request and context, then determine which clarification dimensions are already known, which are inferable, which are ambiguous, and which are missing before research begins.

You do not perform research. You do not answer the research topic. You only assess whether the research protocol has enough information to proceed.

## Inputs

You will receive these variables:

- `{{USER_RESEARCH_TOPIC}}`
  - The raw research topic, question, or hypothesis from the user.

- `{{USER_CONTEXT}}`
  - Optional surrounding context, prior answers, preferences, constraints, organization context, intended use, or conversation history.
  - This may be empty.

- `{{SELECTED_ARCHETYPES}}`
  - The primary and secondary research archetypes selected earlier.
  - Use these to decide which rubric dimensions matter most.

- `{{RUBRIC_QUESTIONS}}`
  - The full clarification rubric.
  - Each item is an atomic question about whether a protocol dimension is known.

## Task

For every rubric question in `{{RUBRIC_QUESTIONS}}`, assess the user's research topic and context.

For each rubric dimension, decide:

- `explicit`: The answer is clearly stated by the user.
- `inferable`: The answer is not stated, but can be safely inferred without materially changing the research plan.
- `ambiguous`: The answer has multiple plausible interpretations that would materially affect the research plan.
- `missing`: The answer is not provided and cannot be safely inferred.
- `not_applicable`: The dimension does not materially apply to the selected archetypes or research topic.

## Assessment Rules

1. Use `{{USER_RESEARCH_TOPIC}}`, `{{USER_CONTEXT}}`, and `{{SELECTED_ARCHETYPES}}` only.
2. Do not use outside knowledge about the topic.
3. Do not invent user preferences.
4. Do not mark a field `explicit` unless the user clearly supplied it.
5. Mark a field `inferable` only when the inference is low-risk and unlikely to change source strategy, analysis method, or output structure.
6. Mark a field `ambiguous` when two or more plausible interpretations would lead to different research plans.
7. Mark a field `missing` when the information is absent and materially relevant.
8. Mark a field `not_applicable` only when the dimension would not change clarification, source acquisition, analysis, QA gates, or reporting for the selected archetypes.
9. If a selected archetype makes a dimension important, do not mark it `not_applicable` casually.
10. Be conservative: when uncertainty would affect downstream research, mark `ambiguous` or `missing`.

## Downstream Impact

For each dimension, estimate whether not resolving it would affect:

- `clarification_questions`
- `source_strategy`
- `quality_gates`
- `analysis_methods`
- `report_structure`
- `publication_quality`

Use `true` or `false` for each.

## Ask Decision

For each dimension, set `should_ask` to `true` only if:

1. The status is `missing` or `ambiguous`;
2. The dimension is applicable to the selected archetypes;
3. The unresolved ambiguity would materially affect at least one downstream impact area;
4. The answer cannot be safely handled by an explicit default assumption.

If the dimension can be handled by a default, set `should_ask` to `false` and provide `default_assumption`.

## Output Requirements

Return strict JSON only. No markdown, no commentary.

Use this schema:

{
  "rubric_assessment": [
    {
      "dimension": "string",
      "rubric_question": "string",
      "status": "explicit | inferable | ambiguous | missing | not_applicable",
      "known_or_inferred_value": "string | null",
      "basis": "string",
      "why_it_matters": "string",
      "risk_if_unresolved": "string",
      "downstream_impact": {
        "clarification_questions": true,
        "source_strategy": true,
        "quality_gates": true,
        "analysis_methods": true,
        "report_structure": true,
        "publication_quality": true
      },
      "should_ask": true,
      "default_assumption": "string | null"
    }
  ],
  "summary": {
    "explicit_count": 0,
    "inferable_count": 0,
    "ambiguous_count": 0,
    "missing_count": 0,
    "not_applicable_count": 0,
    "ask_count": 0,
    "highest_risk_missing_dimensions": ["string"],
    "safe_defaults": [
      {
        "dimension": "string",
        "default_assumption": "string"
      }
    ]
  }
}

## Validation Rules

Before returning, verify:

1. Every rubric question from `{{RUBRIC_QUESTIONS}}` is represented exactly once.
2. Each `status` is one of the allowed values.
3. `should_ask` is true only for `missing` or `ambiguous` dimensions.
4. `default_assumption` is non-null when `should_ask` is false because a default can safely handle the issue.
5. `known_or_inferred_value` is non-null for `explicit` and `inferable` statuses.
6. The output is valid parseable JSON.
```

The user inputs from the questions asked above should be saved in "user context" we collected earlier. 
Note that the user may not want to answer some questions, may express this by saying use defaults, in which case the most comprehensive method of all rubric decisions should be chosen. Hardcode those defaults in the code. 

Final steps of this phase will prepare the following information to pass to Phase 2

```json
{
  "research_topic": {
    "user_input": "..."
  },
  "user_context": {
    "user_input": "..."
  },
  "archetypes": {
    "primary": "...",
    "secondary": []
  },
  "clarification": [
    {
      "dimension": "...",
      "rubric_question": "...",
      "assessment": "explicit | inferable | ambiguous | missing | not_applicable",
      "question": "...",
      "answer": "..."
    }
  ],
  "scope": {
    "objective": "...",
    "research_depth": "...",
    "decision_context": "...",
    "audience": "...",
    "output_format": "...",
    "evidence_standard": "...",
    "topic_boundary": "...",
    "geographic_scope": "...",
    "time_horizon": "...",
    "historical_depth": "...",
    "must_include": [],
    "must_exclude": []
  },
  "source_requirements": {
    "required_source_classes": [],
    "preferred_sources": [],
    "disallowed_sources": [],
    "time_buckets": [],
    "source_recency_policy": "...",
    "evidence_dimensions": [],
    "minimum_coverage": {}
  },
  "analysis_requirements": {
    "key_variables": [],
    "analytical_methods": [],
    "modeling_depth": "...",
    "experiment_requirement": "..."
  }
}
```