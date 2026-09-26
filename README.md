# Resume-to-Job Description AI Matching Engine

A production-style Python application and LLM pipeline that evaluates raw resumes against Job Descriptions, returning strictly validated structured JSON output.

> **Assessment Note:** The original assessment requirement specified the **Gemini API**. To enable flexible local development and testing, this codebase implements a robust **Provider Abstraction** supporting **Groq** (default for local dev) and **Gemini** (for final submission). The provider is selected seamlessly via environment variable (`LLM_PROVIDER=groq` or `LLM_PROVIDER=gemini`).

---

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Provider Selection](#provider-selection)
  - [Groq Usage (Local Dev)](#groq-usage-local-dev)
  - [Gemini Usage (Final Submission)](#gemini-usage-final-submission)
- [How to Run](#how-to-run)
- [Example Input & Output](#example-input--output)
- [System Prompt & Adversarial Resilience](#system-prompt--adversarial-resilience)
- [Schema Enforcement & Sanitization](#schema-enforcement--sanitization)
- [Error Handling & Fallback Strategy](#error-handling--fallback-strategy)
- [Retry Strategy](#retry-strategy)
- [Testing](#testing)
- [Security Notes](#security-notes)
- [Project Limitations](#project-limitations)

---

## Project Overview

The **aivi-ai-engineering-task** application provides an automated, adversarial-resilient evaluation pipeline comparing candidate resumes to job descriptions. It uses LLMs to compute a match score, identify top candidate strengths grounded strictly in resume evidence, highlight missing requirements, and generate a concise 2-line summary.

---

## Architecture

The system follows a clean modular architecture separating concerns across configuration, model definition, LLM provider abstraction, sanitization, retry logic, evaluation orchestration, and testing:

```
                  ┌─────────────────────────────────┐
                  │    Raw Resume + Job Description │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │        Input Validation         │
                  │   (Non-empty, length check)     │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │   LLM Provider (Groq / Gemini)  │
                  │   (Bounded Retry w/ Backoff)    │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │        JSON Sanitizer           │
                  │ (Strip markdown, extract JSON) │
                  └────────────────┬────────────────┘
                                   │
                                   ▼
                  ┌─────────────────────────────────┐
                  │       Pydantic Validation       │
                  │     (Strict MatchResult)        │
                  └───────┬─────────────────┬───────┘
                          │                 │
                  Passes  │                 │ Fails
                          ▼                 ▼
                  ┌──────────────┐  ┌────────────────┐
                  │ Valid JSON   │  │ One-Shot LLM   │
                  │ Output       │  │ Repair Retry   │
                  └──────────────┘  └───────┬────────┘
                                            │
                                    Passes  │ Fails
                                    ┌───────┴────────┐
                                    ▼                ▼
                             ┌──────────────┐ ┌──────────────┐
                             │ Valid JSON   │ │ Predictable  │
                             │ Output       │ │ Fallback     │
                             └──────────────┘ └──────────────┘
```

---

## Key Features

1. **Provider Abstraction**: Switch between Groq and Gemini seamlessly without modifying evaluation logic.
2. **Strict Schema Enforcement**: Pydantic v2 validation ensures valid data types, score ranges (0–100), list item counts (1–5), exact summary line counts (2 non-empty lines), and rejection of extra fields (`extra="forbid"`).
3. **Adversarial Resilience**: System prompt designed to withstand prompt injection ("ignore previous instructions", "give 100", "reveal system prompt") by treating documents strictly as untrusted data.
4. **Evidence Grounding**: Strict guardrails against hallucinated metrics, unearned quantitative performance claims, or invented skills.
5. **Multi-Layer Fault Tolerance**:
   - Bounded exponential backoff + jitter retries for transient errors (429, 503, timeouts).
   - One-shot LLM self-repair attempt on JSON syntax or Pydantic validation errors.
   - Structured JSON fallback responses (never fake candidate scores on failure).
6. **Clean CLI Output**: Emits only valid JSON on stdout; logs and errors are routed to stderr.

---

## Project Structure

```
aivi-ai-engineering-task/
│
├── main.py                    # CLI entrypoint
├── config.py                  # Configuration management & environment validation
├── models.py                  # Pydantic v2 MatchResult output schema & fallback builder
├── prompts.py                 # System prompt, evidence grounding rules & few-shot examples
│
├── providers/                 # Vendor LLM Provider Abstraction
│   ├── __init__.py
│   ├── base.py                # Abstract LLMProvider interface
│   ├── groq_provider.py       # Official Groq Python SDK implementation
│   └── gemini_provider.py     # Official Google GenAI Python SDK implementation
│
├── services/                  # Business Logic Services
│   ├── __init__.py
│   ├── evaluator.py           # Evaluation pipeline orchestration & repair loop
│   ├── retry.py               # Exponential backoff + jitter retry decorator
│   └── sanitizer.py           # Robust JSON extraction & safe parsing
│
├── tests/                     # Comprehensive Unit Test Suite
│   ├── test_schema.py         # Pydantic validation & boundary tests
│   ├── test_sanitizer.py      # JSON sanitization & fence stripping tests
│   ├── test_injection.py      # Prompt injection resilience tests
│   ├── test_fallback.py       # Repair attempt & fallback output tests
│   └── test_retry.py          # Transient vs permanent error classification tests
│
├── samples/                   # Evaluation Text Files
│   ├── resume.txt             # Sample candidate resume
│   └── job_description.txt    # Sample target job description
│
├── .env.example               # Environment variable template
├── .gitignore                 # Git exclusion configuration
├── requirements.txt           # Dependency specifications
└── README.md                  # Project documentation
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12 / 3.13)
- Pip package manager

### 2. Clone / Navigate to Workspace
```bash
cd e:/aivi-ai-engineering-task
```

### 3. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# OR
.venv\Scripts\activate           # Windows PowerShell
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Environment Variables

Copy `.env.example` to create `.env`:

```bash
cp .env.example .env
```

Configuration Options:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LLM_PROVIDER` | Selected LLM provider (`groq` or `gemini`) | `groq` | Yes |
| `GROQ_API_KEY` | API key for Groq API | - | If `LLM_PROVIDER=groq` |
| `GROQ_MODEL` | Groq model identifier | `openai/gpt-oss-20b` | No |
| `GEMINI_API_KEY` | API key for Google Gemini API | - | If `LLM_PROVIDER=gemini` |
| `GEMINI_MODEL` | Gemini model identifier | `gemini-2.5-flash` | No |
| `MAX_INPUT_LENGTH` | Max character count per document | `50000` | No |

---

## Provider Selection

### Groq Usage (Local Dev)
To use Groq (default for local development and testing):
```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

### Gemini Usage (Final Submission)
To switch to Gemini (as requested by original assessment criteria):
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Or pass `--provider gemini` on the CLI to override the environment setting.

---

## How to Run

Run the standalone CLI with the provided sample files:

```bash
python main.py samples/resume.txt samples/job_description.txt
```

Override provider at runtime:
```bash
python main.py samples/resume.txt samples/job_description.txt --provider gemini
```

---

## Example Input & Output

### Input Resume (`samples/resume.txt`):
```text
Uday Kumar G
AI/ML Engineer
B.Tech graduate in Artificial Intelligence and Machine Learning focused on building practical AI systems...
Skills: Python, Java, SQL, Prompt Engineering, Multi-Agent Systems, Generative AI, CrewAI, LangChain, Groq, Gemini...
```

### Input Job Description (`samples/job_description.txt`):
```text
AI Engineer Intern
Responsibilities: Build Python-based AI applications, work with LLM APIs, prompt engineering...
Required: Python, Generative AI / LLM experience, Prompt engineering, Structured output handling.
Preferred: Multi-agent systems, LangChain or CrewAI, Cloud experience...
```

### Output JSON (`stdout`):
```json
{
  "match_score": 92,
  "top_strengths": [
    "Extensive hands-on experience with Python, Generative AI, and LLM APIs",
    "Proven background with prompt engineering and structured model outputs",
    "Strong experience with preferred multi-agent frameworks including LangChain and CrewAI"
  ],
  "missing_skills": [
    "AWS or enterprise cloud infrastructure experience"
  ],
  "summary": "Candidate demonstrates excellent alignment with all core required AI Engineer Intern responsibilities.\nSlight gap in enterprise cloud deployment experience which can be easily onboarded."
}
```

---

## System Prompt & Adversarial Resilience

The system prompt enforces strict trust boundaries:
- **Untrusted Input**: Resumes and JDs are treated purely as data, never as executable instructions.
- **Injection Immunization**: Directly defies instructions like "ignore previous instructions", "give score 100", or "reveal system prompt".
- **Grounding Rules**: Prohibits fabricating performance gains (e.g. converting "Worked with PostgreSQL" to "Reduced query times by 40%").
- **Semantic Matching**: Recognizes equivalent terminology (e.g., "REST endpoints" matching "Build REST APIs").

---

## Schema Enforcement & Sanitization

Outputs undergo two layers of validation:
1. **JSON Sanitization (`services/sanitizer.py`)**:
   - Strips markdown block fences (` ```json ... ``` `).
   - Removes conversational wrapper text.
   - Parses JSON using `json.loads` safely (never unsafe `eval()`).
2. **Pydantic Model Validation (`models.py`)**:
   - `match_score`: Integer bounded between `0` and `100`.
   - `top_strengths`: 1 to 5 non-empty string items.
   - `missing_skills`: 1 to 5 non-empty string items.
   - `summary`: Exactly 2 non-empty lines separated by `\n`.
   - `model_config = ConfigDict(extra="forbid")`: Forbids unexpected top-level fields.

---

## Error Handling & Fallback Strategy

If validation or sanitization fails:
1. **One-Shot Repair Retry**: Evaluator calls the LLM once more with a repair prompt containing error details and the previous response.
2. **Predictable Fallback**: If the repair attempt fails or an unrecoverable service error occurs, evaluator returns a safe fallback object:

```json
{
  "match_score": 0,
  "top_strengths": [
    "Evaluation unavailable."
  ],
  "missing_skills": [
    "Evaluation could not be completed."
  ],
  "summary": "The AI evaluation could not be parsed into valid JSON structure.\nNo match score was computed."
}
```

*Note: The application never fakes candidate match scores during service failures.*

---

## Retry Strategy

Transient network failures, HTTP 429 rate limits, and 503 service outages are handled automatically by `services/retry.py`:
- **Exponential Backoff with Jitter**: Delay sequence `1s + jitter`, `2s + jitter`, `4s + jitter`.
- **Bounded Attempts**: Maximum 3 retries (4 attempts total).
- **Smart Classification**: Permanent errors (401 Unauthorized, invalid API key, 404 Model Not Found) fail immediately without retrying.

---

## Testing

Execute unit tests without calling external APIs using pytest:

```bash
pytest tests/ -v
```

Test Coverage:
- `test_schema.py`: Pydantic field constraints, score boundaries, line counts, forbidden fields.
- `test_sanitizer.py`: Clean JSON, fenced JSON, conversational wrapper JSON, malformed syntax.
- `test_injection.py`: Resistance to adversarial prompt injection inputs.
- `test_fallback.py`: One-shot repair attempt, fallback generation, input validation.
- `test_retry.py`: Transient vs permanent error classification & backoff behavior.

---

## Security Notes

- **Zero Secret Exposure**: API keys are loaded via environment variables and never logged or exposed in exceptions.
- **Git Safety**: `.env` and Python virtual environment folders are excluded via `.gitignore`.
- **Safe Parsing**: Uses standard library `json.loads()` exclusively.

---

## Project Limitations

- PDF/Word parsing is not included; inputs must be provided as text format.
- File inputs are limited by default to 50,000 characters to prevent excessive token consumption.
