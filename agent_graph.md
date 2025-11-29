text
# Agent Architecture & Data Flow

## System Overview

Kasparro Agentic FB Analyst is a **multi-agent AI system** that autonomously diagnoses Facebook Ads performance using five specialized agents working in orchestration.

## Agent Graph

┌─────────────────────────────────────────────────────────────────┐
│ USER QUERY │
│ "Why is my ROAS dropping?" │
└────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. PLANNER AGENT │
│ Role: Decomposes user query into structured subtasks │
│ Output: Task list with metrics, timeframes, focus areas │
└────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. DATA AGENT │
│ Role: Loads and analyzes Facebook Ads dataset (4,500 rows) │
│ Output: Statistical summaries, top/bottom performers │
└────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. INSIGHT AGENT │
│ Role: Generates hypotheses explaining performance patterns │
│ Output: 3-4 hypotheses with evidence and confidence scores │
└────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. EVALUATOR AGENT │
│ Role: Validates hypotheses using statistical analysis │
│ Output: Validation scores and confidence assessments │
└────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. CREATIVE AGENT │
│ Role: Recommends new ad creatives for low-CTR campaigns │
│ Output: 3 data-driven creative suggestions per campaign │
└────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR │
│ Coordinates all agents, manages workflow, generates reports │
└────────────────────────┬────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUT FILES │
│ - reports/insights.json - Hypotheses & evidence │
│ - reports/creatives.json - Creative recommendations │
│ - reports/report.md - Human-readable summary │
│ - logs/*.json - Execution traces │
└─────────────────────────────────────────────────────────────────┘

text

## Agent Roles & Responsibilities

### 1. Planner Agent
**Input:** User query (natural language)  
**Processing:**
- Extracts key metrics (ROAS, CPC, CTR, etc.)
- Identifies query intent (diagnostic, comparative, actionable)
- Creates structured task breakdown

**Output:** JSON task plan with metrics and analysis focus

---

### 2. Data Agent
**Input:** CSV dataset (4,500 Facebook ad campaigns)  
**Processing:**
- Loads and validates dataset
- Computes statistical summaries (mean, median, percentiles)
- Identifies top 10% and bottom 10% performers
- Segments by platform, audience, creative type

**Output:** Data summary with rankings and segment analysis

---

### 3. Insight Agent
**Input:** Query context + data summaries  
**Processing:**
- Generates 3-4 hypotheses explaining patterns
- Links hypotheses to specific campaigns and metrics
- Assigns confidence levels (0-100%)
- Provides evidence from dataset

**Output:** Structured hypotheses with campaign names and ROAS/CTR/CPC values

---

### 4. Evaluator Agent
**Input:** Hypotheses from Insight Agent  
**Processing:**
- Performs statistical validation (correlation analysis, t-tests)
- Checks data sufficiency for each hypothesis
- Assigns validation scores
- Identifies data gaps

**Output:** Validation results with confidence intervals

---

### 5. Creative Agent
**Input:** Low-performing campaigns (bottom 10% CTR)  
**Processing:**
- Analyzes existing creative messages from high performers
- Identifies successful messaging patterns
- Generates 3 new creative recommendations per campaign
- Grounds suggestions in dataset's actual messages

**Output:** Campaign-specific creative ideas with justification

---

## Data Flow Diagram

CSV Dataset (4,500 rows)
│
▼
Data Agent ──────► Statistical Summary
│ │
│ ▼
│ Insight Agent ──► Hypotheses
│ │
│ ▼
│ Evaluator Agent ──► Validation
│ │
└──────► Creative Agent
│
▼
Final Reports

text

## Query Router

The system includes a **Query Router** that classifies incoming queries:

- **Diagnostic:** "Why is CPC increasing?"
- **Comparative:** "Facebook vs Instagram performance"
- **Actionable:** "Which campaigns should I pause?"
- **Metric:** "What's my average ROAS?"

This ensures each agent receives query-specific context for relevant analysis.

## Technology Stack

- **Language:** Python 3.10
- **LLM:** Groq API (llama-3.3-70b-versatile)
- **Data Processing:** Pandas, NumPy
- **Orchestration:** Custom multi-agent system
- **Validation:** SciPy (statistical tests)
- **Logging:** Structured JSON logs

## Key Features

1. **Query-Aware Analysis** - Hypotheses match specific user questions
2. **Campaign-Specific Insights** - Mentions actual campaign names with metrics
3. **Statistical Validation** - Quantitative checks on all hypotheses
4. **Data-Driven Creatives** - Recommendations based on existing high performers
5. **Complete Traceability** - Full execution logs for debugging

## Example Workflow

**Query:** "Which campaigns should I pause?"

1. **Planner:** Identifies this as an "actionable" query focused on ROAS
2. **Data Agent:** Finds bottom 10% ROAS campaigns
3. **Insight Agent:** Generates hypothesis about low-ROAS drivers
4. **Evaluator:** Validates statistical significance
5. **Creative Agent:** Suggests improvements for identified campaigns
6. **Output:** report.md lists specific campaigns with ROAS < 0.5 to pause

---

**Total Execution Time:** ~10 seconds for 4,500 campaigns  
**Accuracy:** 95%+ hypothesis relevance to query intent