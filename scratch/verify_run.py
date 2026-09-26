import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_injection import MockInjectionProvider
from services.evaluator import evaluate_resume

sample_json = '''{
  "match_score": 92,
  "top_strengths": [
    "Extensive hands-on experience with Python, Generative AI, and LLM APIs",
    "Proven background with prompt engineering and structured model outputs"
  ],
  "missing_skills": [
    "AWS or enterprise cloud infrastructure experience"
  ],
  "summary": "Candidate demonstrates excellent alignment with core required AI Engineer Intern responsibilities.\\nSlight gap in enterprise cloud deployment experience which can be easily onboarded."
}'''

provider = MockInjectionProvider(sample_json)
result = evaluate_resume("Sample Resume", "Sample Job Description", provider)
print(result.model_dump_json(indent=2))
