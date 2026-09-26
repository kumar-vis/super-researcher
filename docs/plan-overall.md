You’re build **SuperResearcher**: an OpenClaw/Codex-native research agent that turns a vague topic or hypothesis into a rigorous, publication-quality research dossier by clarifying intent, decomposing the question, iteratively searching across broad and historical source classes, ingesting web/PDF/data/image evidence, running analysis or experiments when needed, validating corpus coverage with hard QA gates, synthesizing source-backed claims into an evidence graph, and producing an arXiv-grade TeX/PDF report with inline citations, strong design, reproducible artifacts, and explicit stopping/readiness criteria so the output can support company decisions, knowledge sharing, and IP creation.
This is needed because current deep research tools often feel superficial: they do not ask enough clarifying questions to understand the real intent, they search a narrow slice of sources, they over-index on recent or easily discoverable material, and they fail to expand into adjacent fields, historical context, counterevidence, datasets, and primary documents. The result is often long-form text that looks polished but has low information density: generic summaries, weak novelty, shallow synthesis, and few decision-grade insights. SuperResearcher is meant to fix that by forcing breadth, depth, evidence quality, and analytical rigor before it ever produces a final report.

**Phase 1: Clarify The Research Task**  
SuperResearcher first turns a vague topic or hypothesis into a precise research brief. It asks clarifying questions about the user’s goal, audience, decision context, scope, desired depth, output format, and what would make the result useful. This phase prevents wasted research by making sure the system understands the real intent before searching.

**Phase 2: Plan The Research Strategy**  
The system decomposes the topic into sub-questions, evidence dimensions, source classes, time horizons, and expected claims. It builds a search strategy that includes adjacent topics, historical context, primary sources, datasets, counterevidence, and likely analytical needs. This phase defines what “good coverage” means before acquisition begins.

**Phase 3: Acquire And Ingest Sources**  
SuperResearcher conducts iterative research rather than a single shallow search. It searches, reads initial results, refines queries, backfills missing areas, and gathers diverse sources across web pages, PDFs, papers, datasets, company documents, regulatory filings, historical material, and opposing evidence. It validates corpus quality with coverage gates before allowing downstream synthesis.

**Phase 4: Read, Extract, And Analyze Evidence**  
The system deeply parses the collected material, extracting passages, claims, tables, figures, statistics, assumptions, and contradictions. It can use code execution for calculations, data analysis, modeling, experiments, and chart generation. The output is a structured evidence base where every important claim is traceable to its source.

**Phase 5: Synthesize Into A Research Argument**  
SuperResearcher turns the evidence base into a coherent research narrative with sections, argument maps, related work, methodology, findings, limitations, and implications. It does not simply summarize sources; it compares them, resolves or documents contradictions, identifies novel insights, and produces dense, decision-grade analysis with inline citations.

**Phase 6: Review, Deepen, And Validate**  
Before publication, the system runs skeptic and peer-review passes to test whether the work is actually strong. It checks for missing evidence, weak claims, unresolved contradictions, shallow sections, citation problems, and low-confidence conclusions. If coverage is insufficient, it loops back into targeted deepening rather than publishing a polished but weak report.

**Phase 7: Publish And Package The Final Output**  
Once the research passes readiness and quality gates, SuperResearcher produces a publication-grade artifact: a polished Markdown, TeX, HTML, and PDF report with inline citations, figures, tables, source index, methodology trail, and release package. The final output should feel closer to an arXiv-quality paper or serious internal strategy memo than a generic AI-generated report.

