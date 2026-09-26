Leveling is decided directly from Phase 1’s `research_depth` field. For example, `quick` may run Level 1 only, `standard` runs Levels 1-2, `analytical` runs Levels 1-3, `deep` runs Levels 1-4, and `frontier/arxiv-grade` runs Levels 1-5. Phase 2 should not infer depth unless `research_depth` is missing, in which case it should ask Phase 1 to clarify.

**Phase 2 Algorithmic Structure**

1. **Generate Heuristic Maps**

Run heuristic generation only up to the level required by `research_depth`.

Use placeholders:

`[LLM_PROMPT_LEVEL_1_BASELINE_ORIENTATION]`, definitions, current state, synonyms, acronyms, core terms, obvious source classes.

`[LLM_PROMPT_LEVEL_2_STRUCTURED_DOMAIN_MAP]`, subtopics, stakeholders, ecosystem players, variables, constraints, use cases, canonical source targets.

`[LLM_PROMPT_LEVEL_3_EVIDENCE_ANALYSIS_MAP]`, research questions, evidence dimensions, indicators, datasets, benchmarks, analytical methods, model inputs.

`[LLM_PROMPT_LEVEL_4_CRITICAL_HISTORICAL_MAP]`, historical threads, prior attempts, opposing views, criticism, failure modes, contradictions, counterevidence.

`[LLM_PROMPT_LEVEL_5_FRONTIER_SYNTHESIS_MAP]`, future work, novel hypotheses, analogy domains, cross-domain applications, nuanced ideas, second-order effects.

Output: `search_heuristics.json`


2. **Create Parallel Search Plan**

Turn focus areas into a search matrix that can run multiple searches in parallel. Each planned search should specify query, focus area, source class, time bucket, evidence dimension, priority, search mechanism, fallback mechanism, and expected artifact type.

Search mechanisms should include general web search, domain-restricted search, PDF/doc search, academic search, government/regulatory search, dataset search, company/filing search, standards/patent search, and citation-chasing. Fallbacks should include alternate terminology, historical terms, known-source direct search, source-site search, browser fetch, API search where available, and citation/backward-reference expansion.

Output: `parallel-search-batches.json`.

3. **Run Candidate Acquisition**

Execute the search plan and build a large candidate pool, capture 10 results per search term, prioritizing high-quality sources over shallow SEO content. Strong source types include pdf links, peer-reviewed papers, arXiv/preprints, university reports, consulting company reports (McKinsey, BCG, Deloitte etc), government reports, regulatory documents, standards, patents, technical PDFs, whitepapers, corporate technical pages, investor decks, annual reports, SEC filings, market research reports, industry association reports, datasets, conference proceedings, books/chapters, credible trade publications, primary interviews/transcripts, and reputable long-form analysis.

Avoid or heavily downgrade tabloids, low-quality blogs, generic SEO pages, content farms, unsourced summaries, and duplicate rewritten articles.

All candidates should be saved locally under:

`<Research_Short_Desc>_Corpus/` (no subfolder over organization, put content here directly)
- Ensure no broken PDFs or broken links
- Ensure that you download the actual data at the link not just the html. Data is often in csvs or zip files or other data formats not html. This data will enable you to run analyses necessary for the research.

Each candidate record should include URL, title, publisher, source type, discovery query, search mechanism, focus area, time bucket, expected usefulness, artifact type, fetch status, and local path if downloaded.

4. **Normalize, Dedupe, and convert to Markdown**

Normalize URLs, remove tracking parameters, merge duplicate discoveries, dedupe by canonical URL, DOI, arXiv ID, SEC accession, title/year/author similarity, and content hash where available. Convert all text content to markdowns and link any images in the content into the markdown. Put images in an /assets subfolder. Data content should be downloaded (no html page download, download the actual data)

Output: `dedupe-report.md`. `research_corpus_index.md`. 

```text
You are generating a Level 1 heuristic map for a deep research system.

Level 1 means: Establishing a baseline. Your job is to expand the user’s research topic into the essential vocabulary, definitions, current-state angles, synonyms, acronyms, core concepts, key entities, basic taxonomy, and obvious source classes needed before search begins. Include anything else you think may be relevant to the topic baseline.

You goal: Generate search-term heuristics only.

Input:
{
  "research_topic": "{{research_topic.user_input}}",
  "objective": "{{scope.objective}}",
  "topic_boundary": "{{scope.topic_boundary}}",
  "geographic_scope": "{{scope.geographic_scope}}",
  "time_horizon": "{{scope.time_horizon}}",
  "historical_depth": "{{scope.historical_depth}}",
  "must_include": {{scope.must_include}},
  "must_exclude": {{scope.must_exclude}},
  "required_source_classes": {{source_requirements.required_source_classes}},
  "preferred_sources": {{source_requirements.preferred_sources}},
  "source_recency_policy": "{{source_requirements.source_recency_policy}}"
}

Return only valid JSON in this shape:

{
  "level": 1,
  "purpose": "baseline_orientation",
  "canonical_topic": "...",
  "scope_interpretation": {
    "included": [],
    "excluded": [],
    "geographic_focus": "...",
    "time_focus": "...",
    "historical_depth_needed": "..."
  },
  "definitions": [
    {
      "terms":[]
    }
  ],
  "synonyms_and_variants": {
    "synonyms_aka": [],
    "alternate_phrases": [],
    "acronyms": [],
    "technical_terms": [],
    "legacy_terms": [],
    "commercial_terms": []
  },
  "core_concepts": [
    {
      "concept_one": "...",
      "concept_two": "...",
      "concept_three": "...",
      "concept_four": "...",
      "concept_five": "..."
    }
  ],
  "current_state_angles": [
    {
      "angle_one": "...",
      "angle_two": "...",
      "angle_three": "...",
      "angle_four": "...",
      "angle_five": "..."
    }
  ],
  "key_entities_to_search": {
    "organizations": [],
    "companies": [],
    "regulators_or_government_bodies": [],
    "standards_bodies": [],
    "research_institutions": [],
    "products_or_technologies": []
  },
  "basic_taxonomy": [
    {
      "category": "...",
      "subcategories": []
    }
  ],
  "obvious_source_classes": [
    {
      "source_class": "...",
      "query_patterns": [],
      "additional_query_patterns": []
    }
  ],
  "baseline_search_queries": [
    {
      "query": "...",
      "intended_use": "definition | current_state | taxonomy | entity_discovery | source_discovery",
      "query": "...",
      "intended_use": "definition | current_state | taxonomy | entity_discovery | source_discovery",
      "query": "...",
      "intended_use": "definition | current_state | taxonomy | entity_discovery | source_discovery",
      "query": "...",
      "intended_use": "definition | current_state | taxonomy | entity_discovery | source_discovery",
      "query": "...",
      "intended_use": "definition | current_state | taxonomy | entity_discovery | source_discovery",
      "query": "...",
      "intended_use": "definition | current_state | taxonomy | entity_discovery | source_discovery",      
    }
  ]
}

Requirements:
- Be comprehensive for synonyms, acronyms, alternate phrases, technical terms, and obvious source classes.
- If the topic has historical depth, include legacy terms that may appear in older literature.
- If geography is specified, include geography-specific query variants.
- Prefer useful search language over generic academic wording. Keep entries concise but specific.
```



```text
You are generating a Level 2 heuristic map for a deep research system.

Level 2 means: Structured domain mapping. Your job is to expand the user's research topic into the major subtopics, stakeholder groups, ecosystem players, key variables, drivers, constraints, use cases, analytical dimensions, and source-acquisition targets needed before serious source collection begins. Include anything else that clarifies the domain structure and improves search coverage.

Your goal: Generate search-planning heuristics only.

Input:
{
  "research_topic": "{{research_topic.user_input}}",
  "objective": "{{scope.objective}}",
  "decision_context": "{{scope.decision_context}}",
  "audience": "{{scope.audience}}",
  "topic_boundary": "{{scope.topic_boundary}}",
  "geographic_scope": "{{scope.geographic_scope}}",
  "time_horizon": "{{scope.time_horizon}}",
  "historical_depth": "{{scope.historical_depth}}",
  "must_include": {{scope.must_include}},
  "must_exclude": {{scope.must_exclude}},
  "required_source_classes": {{source_requirements.required_source_classes}},
  "preferred_sources": {{source_requirements.preferred_sources}},
  "source_recency_policy": "{{source_requirements.source_recency_policy}}",
  "evidence_dimensions": {{source_requirements.evidence_dimensions}},
  "key_variables": {{analysis_requirements.key_variables}}
}

Return only valid JSON in this shape:

{
  "level": 2,
  "purpose": "structured_domain_map",
  "canonical_topic": "...",
  "scope_interpretation": {
    "included": [],
    "excluded": [],
    "geographic_focus": "...",
    "time_focus": "...",
    "historical_depth_needed": "..."
  },
  "domain_decomposition": [
    {
      "subtopic": "...",
      "why_it_matters_for_search": "...",
      "included_angles": [],
      "related_terms": [],
      "candidate_query_patterns": []
    }
  ],
  "stakeholder_map": [
    {
      "stakeholder_type": "...",
      "role_in_topic": "...",
      "questions_they_help_answer": [],
      "information_they_may_produce": [],
      "candidate_query_patterns": []
    }
  ],
  "ecosystem_players": {
    "companies": [],
    "government_or_regulators": [],
    "research_institutions": [],
    "standards_bodies": [],
    "industry_groups": [],
    "customers_or_users": [],
    "critics_or_watchdogs": []
  },
  "key_variables": [
    {
      "variable": "...",
      "why_it_matters": "...",
      "related_metrics_or_terms": [],
      "likely_source_classes": [],
      "candidate_query_patterns": []
    }
  ],
  "drivers_and_mechanisms": [
    {
      "driver_or_mechanism": "...",
      "affected_subtopics": [],
      "search_angles": [],
      "likely_source_classes": []
    }
  ],
  "constraints_and_bottlenecks": [
    {
      "constraint": "...",
      "constraint_type": "technical | economic | regulatory | operational | social | scientific | market | other",
      "search_angles": [],
      "likely_source_classes": []
    }
  ],
  "use_cases_or_applications": [
    {
      "use_case": "...",
      "why_it_matters": "...",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "analytical_dimensions": [
    {
      "dimension": "...",
      "sub_questions": [],
      "required_source_classes": [],
      "candidate_query_patterns": []
    }
  ],
  "canonical_source_targets": [
    {
      "source_target": "...",
      "source_class": "...",
      "why_needed": "...",
      "search_pattern": "..."
    }
  ],
  "structured_search_queries": [
    {
      "query": "...",
      "intended_use": "subtopic | stakeholder | ecosystem_player | variable | driver | constraint | use_case | analytical_dimension | source_discovery",
      "expected_source_class": "...",
      "linked_item": "..."
    }
  ]
}

Requirements:
- Make the decomposition comprehensive enough to drive source acquisition.
- Prioritize dimensions that matter for the stated objective, decision_context, audience, geography, and time horizon.
- Include regulatory, technical, economic, operational, market, scientific, and user/stakeholder dimensions only when relevant.
- Use specific search language and source targets, not vague categories.
- If geography is specified, include geography-specific query variants.
- Respect must_include, must_exclude, required_source_classes, preferred_sources, and source_recency_policy.
- Do not include citations, factual claims, confidence scores, or final analysis.
```

## Level 3 Prompt

```text
You are generating a Level 3 heuristic map for a deep research system.

Level 3 means: Evidence and analysis mapping. Your job is to expand the user's research topic into research questions, evidence dimensions, measurable indicators, datasets, benchmarks, analytical methods, model inputs, assumptions, dependencies, and uncertainty areas needed for serious source acquisition and later analysis. Include anything else that turns the topic into measurable, source-acquirable evidence.

Your goal: Generate search-planning and analysis-planning heuristics only.

Input:
{
  "research_topic": "{{research_topic.user_input}}",
  "objective": "{{scope.objective}}",
  "decision_context": "{{scope.decision_context}}",
  "audience": "{{scope.audience}}",
  "evidence_standard": "{{scope.evidence_standard}}",
  "topic_boundary": "{{scope.topic_boundary}}",
  "geographic_scope": "{{scope.geographic_scope}}",
  "time_horizon": "{{scope.time_horizon}}",
  "historical_depth": "{{scope.historical_depth}}",
  "must_include": {{scope.must_include}},
  "must_exclude": {{scope.must_exclude}},
  "required_source_classes": {{source_requirements.required_source_classes}},
  "preferred_sources": {{source_requirements.preferred_sources}},
  "time_buckets": {{source_requirements.time_buckets}},
  "source_recency_policy": "{{source_requirements.source_recency_policy}}",
  "evidence_dimensions": {{source_requirements.evidence_dimensions}},
  "minimum_coverage": {{source_requirements.minimum_coverage}},
  "key_variables": {{analysis_requirements.key_variables}},
  "analytical_methods": {{analysis_requirements.analytical_methods}},
  "modeling_depth": "{{analysis_requirements.modeling_depth}}",
  "experiment_requirement": "{{analysis_requirements.experiment_requirement}}"
}

Return only valid JSON in this shape:

{
  "level": 3,
  "purpose": "evidence_and_analysis_map",
  "canonical_topic": "...",
  "scope_interpretation": {
    "included": [],
    "excluded": [],
    "geographic_focus": "...",
    "time_focus": "...",
    "historical_depth_needed": "..."
  },
  "research_questions": [
    {
      "question": "...",
      "why_it_matters": "...",
      "evidence_dimensions": [],
      "minimum_evidence_needed": "...",
      "candidate_query_patterns": []
    }
  ],
  "evidence_dimensions": [
    {
      "dimension": "...",
      "what_to_prove_or_measure": "...",
      "required_source_classes": [],
      "candidate_query_patterns": []
    }
  ],
  "measurable_indicators": [
    {
      "indicator": "...",
      "definition": "...",
      "unit_or_measure": "...",
      "likely_source_classes": [],
      "candidate_query_patterns": []
    }
  ],
  "dataset_targets": [
    {
      "dataset_or_data_type": "...",
      "why_needed": "...",
      "likely_hosts_or_publishers": [],
      "coverage_requirements": [],
      "candidate_query_patterns": []
    }
  ],
  "benchmarks_and_comparables": [
    {
      "benchmark": "...",
      "comparison_purpose": "...",
      "required_data": [],
      "candidate_query_patterns": []
    }
  ],
  "analytical_methods": [
    {
      "method": "...",
      "use_for": "...",
      "inputs_needed": [],
      "outputs_expected": [],
      "source_requirements": []
    }
  ],
  "model_inputs": [
    {
      "input": "...",
      "used_in": "...",
      "likely_source_classes": [],
      "uncertainty_risk": "low | medium | high",
      "candidate_query_patterns": []
    }
  ],
  "assumptions_to_test": [
    {
      "assumption": "...",
      "why_it_matters": "...",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "dependencies": [
    {
      "dependency": "...",
      "dependent_questions": [],
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "uncertainty_areas": [
    {
      "uncertainty": "...",
      "why_it_matters": "...",
      "how_to_reduce_uncertainty": "...",
      "candidate_query_patterns": []
    }
  ],
  "analysis_ready_search_queries": [
    {
      "query": "...",
      "intended_use": "research_question | evidence_dimension | indicator | dataset | benchmark | method | model_input | assumption_test | dependency | uncertainty_reduction",
      "expected_source_class": "...",
      "linked_item": "..."
    }
  ]
}

Requirements:
- Focus on evidence and analysis planning, not conclusions.
- Make the output comprehensive enough to support later modeling, experiments, and analytical reporting.
- Respect evidence_standard, minimum_coverage, time_buckets, source_recency_policy, topic_boundary, geographic_scope, must_include, and must_exclude.
- If modeling_depth or experiment_requirement is non-trivial, include concrete model inputs, datasets, assumptions, and methods.
- Include historical indicators or datasets when historical_depth requires them.
- Prefer measurable, source-acquirable evidence over vague concepts.
- Do not include citations, factual claims, confidence scores, or final analysis.
```

## Level 4 Prompt

```text
You are generating a Level 4 heuristic map for a deep research system.

Level 4 means: Critical and historical mapping. Your job is to expand the user's research topic into historical threads, predecessor ideas, prior attempts, opposing views, counter-topics, failure modes, criticism, contradictions, risks, negative evidence, edge cases, and boundary conditions that should guide source acquisition. Include anything else that helps find counterevidence, older terminology, failed attempts, and limitations.

Your goal: Generate critical search-planning heuristics only.

Input:
{
  "research_topic": "{{research_topic.user_input}}",
  "objective": "{{scope.objective}}",
  "decision_context": "{{scope.decision_context}}",
  "evidence_standard": "{{scope.evidence_standard}}",
  "topic_boundary": "{{scope.topic_boundary}}",
  "geographic_scope": "{{scope.geographic_scope}}",
  "time_horizon": "{{scope.time_horizon}}",
  "historical_depth": "{{scope.historical_depth}}",
  "must_include": {{scope.must_include}},
  "must_exclude": {{scope.must_exclude}},
  "required_source_classes": {{source_requirements.required_source_classes}},
  "preferred_sources": {{source_requirements.preferred_sources}},
  "time_buckets": {{source_requirements.time_buckets}},
  "source_recency_policy": "{{source_requirements.source_recency_policy}}",
  "evidence_dimensions": {{source_requirements.evidence_dimensions}},
  "minimum_coverage": {{source_requirements.minimum_coverage}}
}

Return only valid JSON in this shape:

{
  "level": 4,
  "purpose": "critical_and_historical_map",
  "canonical_topic": "...",
  "scope_interpretation": {
    "included": [],
    "excluded": [],
    "geographic_focus": "...",
    "time_focus": "...",
    "historical_depth_needed": "..."
  },
  "historical_search_frame": {
    "time_periods_to_search": [],
    "legacy_terms_or_names": [],
    "older_source_classes": [],
    "geography_specific_history_queries": []
  },
  "historical_threads": [
    {
      "thread": "...",
      "why_it_matters": "...",
      "time_periods_to_search": [],
      "legacy_terms_or_names": [],
      "candidate_query_patterns": []
    }
  ],
  "predecessor_ideas_and_prior_attempts": [
    {
      "idea_or_attempt": "...",
      "relationship_to_topic": "...",
      "what_to_investigate": [],
      "candidate_query_patterns": []
    }
  ],
  "opposing_views": [
    {
      "view": "...",
      "who_might_hold_it": [],
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "counter_topics": [
    {
      "counter_topic": "...",
      "why_it_is_relevant": "...",
      "comparison_or_tension": "...",
      "candidate_query_patterns": []
    }
  ],
  "failure_modes": [
    {
      "failure_mode": "...",
      "failure_type": "technical | economic | regulatory | operational | market | social | scientific | organizational | other",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "criticism_and_negative_evidence": [
    {
      "criticism_or_negative_signal": "...",
      "why_it_matters": "...",
      "likely_source_classes": [],
      "candidate_query_patterns": []
    }
  ],
  "contradiction_targets": [
    {
      "potential_contradiction": "...",
      "claims_or_assumptions_in_tension": [],
      "evidence_needed_to_resolve": [],
      "candidate_query_patterns": []
    }
  ],
  "risk_register_inputs": [
    {
      "risk": "...",
      "risk_category": "technical | economic | regulatory | operational | market | social | scientific | legal | safety | other",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "edge_cases_and_boundary_conditions": [
    {
      "edge_case": "...",
      "why_it_matters": "...",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "negative_search_terms": {
    "failure_terms": [],
    "criticism_terms": [],
    "legal_or_regulatory_terms": [],
    "safety_or_risk_terms": [],
    "market_or_adoption_terms": [],
    "scientific_or_methodological_terms": []
  },
  "critical_search_queries": [
    {
      "query": "...",
      "intended_use": "historical_thread | prior_attempt | opposing_view | counter_topic | failure_mode | criticism | contradiction | risk | edge_case | negative_evidence",
      "expected_source_class": "...",
      "linked_item": "..."
    }
  ]
}

Requirements:
- Focus on counterevidence, historical depth, failure analysis, and boundary conditions.
- Respect topic_boundary, geographic_scope, time_horizon, historical_depth, must_include, must_exclude, and source_recency_policy.
- Use historical_depth and time_buckets to identify older terminology and prior-art search paths.
- Include opposing views and criticism even if they challenge the user's likely hypothesis.
- Include negative search patterns such as failure, bankruptcy, delay, safety concern, criticism, lawsuit, opposition, limitation, debunking, replication failure, and cost overrun when relevant.
- Do not include citations, factual claims, confidence scores, or final analysis.
```

## Level 5 Prompt

```text
You are generating a Level 5 heuristic map for a deep research system.

Level 5 means: Frontier and synthesis mapping. Your job is to expand the user's research topic into future-facing research directions, novel hypotheses, analogy domains, cross-domain applications, nuanced ideas, emerging signals, second-order effects, strategic implications, open problems, and synthesis paths that should guide deeper source acquisition. Treat all novel ideas as hypotheses to investigate, not conclusions.

Your goal: Generate frontier search-planning and idea-discovery heuristics only.

Input:
{
  "research_topic": "{{research_topic.user_input}}",
  "objective": "{{scope.objective}}",
  "decision_context": "{{scope.decision_context}}",
  "audience": "{{scope.audience}}",
  "topic_boundary": "{{scope.topic_boundary}}",
  "geographic_scope": "{{scope.geographic_scope}}",
  "time_horizon": "{{scope.time_horizon}}",
  "historical_depth": "{{scope.historical_depth}}",
  "must_include": {{scope.must_include}},
  "must_exclude": {{scope.must_exclude}},
  "required_source_classes": {{source_requirements.required_source_classes}},
  "preferred_sources": {{source_requirements.preferred_sources}},
  "source_recency_policy": "{{source_requirements.source_recency_policy}}",
  "evidence_dimensions": {{source_requirements.evidence_dimensions}},
  "key_variables": {{analysis_requirements.key_variables}},
  "analytical_methods": {{analysis_requirements.analytical_methods}},
  "modeling_depth": "{{analysis_requirements.modeling_depth}}",
  "experiment_requirement": "{{analysis_requirements.experiment_requirement}}"
}

Return only valid JSON in this shape:

{
  "level": 5,
  "purpose": "frontier_and_synthesis_map",
  "canonical_topic": "...",
  "scope_interpretation": {
    "included": [],
    "excluded": [],
    "geographic_focus": "...",
    "time_focus": "...",
    "historical_depth_needed": "..."
  },
  "frontier_search_frame": {
    "near_term_extensions": [],
    "long_term_possibilities": [],
    "signals_to_watch": [],
    "source_classes_to_prioritize": []
  },
  "future_work_directions": [
    {
      "direction": "...",
      "why_it_might_matter": "...",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "novel_hypotheses": [
    {
      "hypothesis": "...",
      "why_it_is_interesting": "...",
      "what_would_support_it": [],
      "what_would_falsify_it": [],
      "candidate_query_patterns": []
    }
  ],
  "analogy_domains": [
    {
      "analogy_domain": "...",
      "relevance_to_topic": "...",
      "transferable_patterns_to_investigate": [],
      "candidate_query_patterns": []
    }
  ],
  "cross_domain_applications": [
    {
      "application_area": "...",
      "connection_to_topic": "...",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "nuanced_ideas": [
    {
      "idea": "...",
      "nuance_or_tension": "...",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "emerging_signals": [
    {
      "signal_type": "...",
      "why_to_watch_it": "...",
      "likely_source_classes": [],
      "candidate_query_patterns": []
    }
  ],
  "second_order_effects": [
    {
      "effect": "...",
      "trigger_or_mechanism": "...",
      "who_or_what_is_affected": [],
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "strategic_implications": [
    {
      "implication": "...",
      "decision_relevance": "...",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "open_problems": [
    {
      "problem": "...",
      "why_unresolved_or_hard": "...",
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "synthesis_paths": [
    {
      "synthesis_path": "...",
      "items_to_connect": [],
      "evidence_needed": [],
      "candidate_query_patterns": []
    }
  ],
  "frontier_search_queries": [
    {
      "query": "...",
      "intended_use": "future_work | novel_hypothesis | analogy | cross_domain_application | nuanced_idea | emerging_signal | second_order_effect | strategic_implication | open_problem | synthesis_path",
      "expected_source_class": "...",
      "speculation_level": "low | medium | high",
      "linked_item": "..."
    }
  ]
}

Requirements:
- Focus on frontier search directions and synthesis paths, not conclusions.
- Respect topic_boundary, geographic_scope, time_horizon, historical_depth, must_include, must_exclude, and source_recency_policy.
- Include both practical near-term extensions and more speculative long-term directions when relevant.
- Include analogy domains only when they create useful search paths or transferable models.
- Include falsification paths for novel hypotheses.
- Keep ideas specific enough to become search queries.
- Avoid hype, generic futurism, and unsupported claims.
- Do not include citations, factual claims, confidence scores, or final analysis.
```