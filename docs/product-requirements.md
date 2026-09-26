# SuperResearcher — Product Requirements Brief

## 1. What We Are Building

SuperResearcher is a research tool that takes a broad topic from a user and produces a durable, evidence-backed research dossier.

It should help a user answer questions like:

- What is the opportunity?
- Is it feasible?
- What is the market size or scaling potential?
- What are the major risks?
- What evidence supports or contradicts the thesis?
- Where is the evidence weak or missing?

The goal is not to generate a quick AI essay. The goal is to build a reusable research corpus with sources, extracted evidence, quality checks, and eventually a polished report.

---

## 2. Core User Experience

A user should be able to start a research run by providing:

1. A research topic
2. Research depth
3. Research breadth
4. Desired final source count

Before the run starts, the product should clearly show the user the major settings and ask for confirmation if the run is large or expensive.

Example user input:

```text
Topic: <research topic>
Research depth: high
Research breadth: high
Final sources: 120
```

The user should not need to know internal implementation details. They should understand the practical impact:

- Depth = how many results are checked per query
- Breadth = how widely the system explores different angles
- Final sources = how many sources make it into the final research corpus

---

## 3. Required User Controls

### 3.1 Research Depth

Research depth controls how many search results are reviewed per query.

| User setting | Results per query |
|---|---:|
| Low | 3 |
| Medium | 7 |
| High | 10 |
| Extra high | 15 |
| Ludicrous | 50 |

If the user chooses “high,” every query should collect 10 results unless they explicitly override this.

### 3.2 Research Breadth

Research breadth controls how many layers of research planning the system performs.

| User setting | Meaning |
|---|---|
| Low | Basic topic coverage and obvious sources |
| Medium | Adds subtopics, stakeholders, datasets, and major evidence angles |
| High | Adds historical context, counterarguments, risks, future scenarios, and adjacent domains |

The user should see this in plain English, not as technical “levels.”

### 3.3 Final Source Count

The system should let the user choose how many sources should make it into the final corpus.

Defaults:

| Setting | Value |
|---|---:|
| Default final sources | 120 |
| Maximum final sources | 500 |

If the user does not choose, use 120.

If the user requests more than 500, cap it at 500 unless an admin/config override exists.

Important: this setting must be shown upfront. It should not be hidden as an advanced technical option.

---

## 4. Progress Updates

Research runs may take several minutes or longer. The user must receive progress updates.

Default behavior:

- Send an update every 5 minutes during long-running work.
- Also send updates at major milestones.

Required milestones:

1. Run started
2. Dossier created
3. Research plan created
4. Candidate source discovery completed
5. Source ranking and selection completed
6. Source ingestion in progress
7. Corpus quality check completed
8. Run completed or failed

Each update should be short and useful.

Good update example:

```text
Still working. Discovery complete: 1,430 candidate sources found, 260 deduped. Now selecting final sources.
```

Bad update example:

```text
Internal processing step completed. candidate_count=1430
```

The update system should be channel-agnostic. It should work whether the product is used from chat, web app, email, Slack, SMS, or another interface.

---

## 5. Source and Corpus Requirements

The system must preserve the original source material.

When it finds and ingests a source, it should keep:

- The original file or web content
- A clean readable text/Markdown version
- Metadata about where it came from
- Any extracted assets, such as images, tables, or attachments

Markdown is a sidecar, not a replacement.

Do not delete or overwrite original source files.

Supported source types should include, where possible:

- PDFs
- HTML/web pages
- CSV/data files
- Excel files
- Word documents
- images/tables extracted from documents
- videos or presentation links as metadata if full extraction is not possible

---

## 6. Storage Requirements

Research dossiers should be stored separately from any curated knowledge base or wiki.

Reason: the research corpus is raw working material. The knowledge base/wiki should only receive curated outputs later, not every raw source and intermediate artifact.

The storage location should be configurable.

The product must avoid silently writing to the wrong place if an external drive, network mount, or configured storage path is unavailable.

Before writing a large run, the system should verify:

- storage path exists
- storage path is writable
- enough space is available

---

## 7. Search and Source Discovery Requirements

The system should search broadly and intentionally, not just use generic web search.

It should look for different types of evidence:

- Academic research
- Government/regulatory sources
- Datasets
- Standards/specifications
- Company primary sources
- Market reports
- Credible news reporting
- Expert analysis
- Counterarguments and failure cases

Search queries should include source-intent terms such as:

- report
- PDF
- dataset
- data
- market size
- forecast
- analysis
- presentation
- study
- risks
- criticism
- regulation

PDF links must be downloaded and parsed locally before being treated as usable evidence.

A search result snippet alone is not enough for citation-quality evidence.

---

## 8. Quality Requirements

Every run should produce a corpus quality report.

The system should check whether the corpus has enough diversity and evidence quality.

Quality checks should include:

- Did we collect enough sources?
- Are there enough independent publishers?
- Are there too many sources from the same class?
- Are key source types missing?
- Are publication dates missing too often?
- Is there historical context?
- Is there current/recent evidence?
- Is there forward-looking evidence?
- Are there counterarguments and risk sources?
- Are important evidence dimensions missing?

The system should distinguish between:

- Pass
- Pass with warnings
- Fail

If a run fails quality checks, the user should still be able to inspect what was collected, unless they requested strict failure behavior.

---

## 9. LLM Behavior Requirements

The LLM should help plan the research, but it should not be treated as evidence.

LLM-generated planning should be used for:

- topic decomposition
- synonyms and related terms
- source categories
- risk areas
- historical context
- counterarguments
- future scenarios
- search query ideas

LLM output must not be cited as a source.

Required LLM settings for planning calls:

| Setting | Value |
|---|---|
| Temperature | 0.7 |
| Thinking / reasoning effort | High |

If an LLM planning call fails or times out, the run should continue using deterministic fallback planning.

The user should not lose the whole research run because one planning call failed.

---

## 10. Dossier Output Requirements

Each research run should create a durable dossier containing:

- Research topic
- User-selected settings
- Research plan
- Search queries used
- Candidate sources found
- Deduped sources
- Final selected sources
- Ingested source corpus
- Source metadata
- Quality report
- Run summary
- Extracted claims, if later phases are run
- Draft report artifacts, if later phases are run

The dossier should be understandable to a human reviewer.

A user or researcher should be able to open the folder and understand:

- what was searched
- what was found
- what was selected
- what failed
- what evidence exists
- what evidence is weak or missing

---

## 11. Expected Run Summary

At the end of a run, the user should receive a concise summary like:

```text
Research run complete.

Topic: <topic>
Depth: high
Breadth: high
Final source target: 120

Candidate sources found: 1,431
Deduped candidates: 259
Selected sources: 120
Ingested sources: 120
Quality verdict: Pass with warnings

Main warning: some sources are missing publication dates.
Dossier path: <path>
Quality report: <path>
```

---

## 12. Non-Goals

This product should not:

- Produce unsupported AI-written conclusions without sources
- Treat search snippets as evidence
- Delete or replace original source files
- Hide important run settings from the user
- Store raw research corpora inside a curated wiki by default
- Fail the entire run just because one LLM planning call fails
- Require users to understand internal engineering details

---

## 13. Acceptance Criteria

The product is acceptable when:

1. A user can start a research run from a topic.
2. The user can set research depth, breadth, and final source count before execution.
3. The default final source target is 120.
4. The maximum final source target is 500.
5. The system sends progress updates every 5 minutes during long runs.
6. The system preserves original sources and creates readable sidecars.
7. The system creates a human-readable dossier for every run.
8. The system produces a corpus quality report for every run.
9. The system clearly reports pass, pass-with-warnings, or fail.
10. The system separates raw research storage from curated wiki/knowledge-base storage.
11. LLM planning uses temperature 0.7 and high reasoning effort.
12. LLM planning failures do not kill the full run.
13. The user receives a concise final summary with source counts, quality verdict, and dossier location.

---

## 14. One-Sentence Product Principle

SuperResearcher should feel less like “ask an AI a question” and more like “commission a junior research analyst who saves every source, shows their work, flags weak evidence, and keeps you updated while they work.”
