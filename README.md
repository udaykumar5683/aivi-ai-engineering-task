# AIVI AI Engineering Task

Standalone Python pipeline for evaluating a raw resume against a Job Description with LLMs.

## Assessment alignment

The assessment asks for a Gemini based Python script that accepts resume text plus a sample Job Description and returns:

- match_score: integer from 0 to 100
- top_strengths
- missing_skills
- a two line summary

This repository supports both providers behind one interface:

- Groq for fast local development and testing
- Gemini for the assessment compatible run

Select the provider with LLM_PROVIDER or the CLI --provider option.

## Architecture

Resume text + Job Description
    ->
Input validation
    ->
LLM provider
    ->
Provider side structured JSON
    ->
JSON sanitization
    ->
Pydantic validation
    ->
One shot schema repair when model output is invalid
    ->
Validated JSON result or structured fallback

Provider failures are handled separately from model output validation. This prevents an
authentication or service failure from triggering an unnecessary repair request.

## Project structure

```
aivi-ai-engineering-task/
├── main.py
├── config.py
├── models.py
├── prompts.py
├── providers/
│   ├── __init__.py
│   ├── base.py
│   ├── groq_provider.py
│   └── gemini_provider.py
├── services/
│   ├── __init__.py
│   ├── evaluator.py
│   ├── retry.py
│   └── sanitizer.py
├── tests/
│   ├── test_schema.py
│   ├── test_sanitizer.py
│   ├── test_injection.py
│   ├── test_fallback.py
│   └── test_retry.py
├── samples/
│   ├── resume.txt
│   └── job_description.txt
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

Python 3.10 or newer is recommended.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Create a local .env file from .env.example.

Never commit the .env file.

## Environment variables

```env
LLM_PROVIDER=groq

GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

MAX_INPUT_LENGTH=50000
LLM_TIMEOUT_SECONDS=30
```

## Run with Groq

```powershell
python main.py samples/resume.txt samples/job_description.txt --provider groq
```

## Run with Gemini

```powershell
python main.py samples/resume.txt samples/job_description.txt --provider gemini
```

The application prints only the final JSON result to stdout.

## Output contract

Example:

```json
{
  "match_score": 82,
  "top_strengths": [
    "Python development experience",
    "Generative AI project experience"
  ],
  "missing_skills": [
    "Kubernetes"
  ],
  "summary": "Good alignment with the core AI engineering requirements.\nKubernetes experience is not documented in the supplied resume."
}
```

The example is illustrative only.

## Structured output

### Groq

The Groq provider uses strict Structured Outputs with:

- response format type json_schema
- strict true
- required fields
- additionalProperties false

The provider side schema is intentionally conservative. Detailed constraints such as the
0 to 100 score range, list limits, strict types and exactly two summary lines are enforced
again with Pydantic.

### Gemini

The Gemini provider uses the Google GenAI SDK with JSON MIME type plus the Pydantic
MatchResult class as response_schema.

The response is then validated again through MatchResult.

## Prompt engineering

The system prompt treats the resume and Job Description as untrusted data.

It explicitly prevents document text from changing:

- system instructions
- scoring rules
- output schema
- role definition

The prompt also requires evidence grounded output and prohibits invented performance
numbers, record counts, skills, technologies, certifications, employers and experience.

Few shot examples cover:

1. Prompt injection
2. Unsupported metrics
3. Complete matches with an empty missing_skills list
4. Semantic REST API matching

## JSON sanitization

services/sanitizer.py safely extracts a JSON object from model output.

It accepts:

- raw JSON
- fenced JSON
- JSON surrounded by normal text

It uses json.JSONDecoder.raw_decode and json.loads only. No executable parsing is used.

## Error handling

The pipeline separates two failure classes.

### Provider/API failure

Examples:

- 429 rate limit
- 408 timeout
- 5xx service failure
- network connection failure

These enter the bounded retry layer.

Permanent errors such as invalid credentials or model not found do not trigger retries.

### Model output failure

Examples:

- malformed JSON
- schema validation failure

These trigger one repair request using the same resume and Job Description.

If repair also fails, the pipeline returns a structured fallback.

## Retry policy

Transient errors use exponential backoff with jitter.

Default delay sequence:

```
1 second + jitter
2 seconds + jitter
4 seconds + jitter
```

There are at most three retries after the initial request.

The timeout is configurable through LLM_TIMEOUT_SECONDS.

## Input validation

The evaluator rejects:

- empty resume text
- empty Job Description
- inputs exceeding MAX_INPUT_LENGTH

Whitespace is trimmed before evaluation.

## Pydantic validation

MatchResult uses strict Pydantic v2 validation:

- strict integer score
- score range 0 to 100
- 1 to 5 top strengths
- 0 to 5 missing skills
- blank list items rejected
- exactly two non-empty summary lines
- unexpected top level fields rejected

## Testing

Run:

```powershell
pytest tests/ -v
```

The test suite covers:

- schema boundaries
- strict types
- empty missing_skills
- extra fields
- JSON sanitization
- malformed JSON
- braces inside JSON strings
- prompt injection as adversarial input
- one shot repair
- permanent provider failure
- fallback behavior
- retry classification
- bounded retry behavior

The prompt injection unit test intentionally does not claim to prove LLM level security.
Actual model resistance must be validated with an integration test, as was done in the AIVI
Campus audit.

## Security

- API keys are read from environment variables.
- .env is ignored by Git.
- API keys are never hard coded.
- Raw resume and Job Description text are not logged by the evaluator.
- JSON parsing never executes arbitrary code.

## Limitations

- Resume and Job Description inputs are text files in this deliverable.
- PDF, DOCX and OCR processing are outside Deliverable 3.
- The prompt injection unit test is deterministic and does not replace real model testing.
- Provider side structured output does not replace application side Pydantic validation.

## Development notes

The original assessment requested Gemini. Groq was added only as a development provider so
the same evaluation logic can be tested quickly. The provider abstraction keeps the business
logic independent of the model vendor.
