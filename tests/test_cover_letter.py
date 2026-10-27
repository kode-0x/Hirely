"""Cover-letter validation-contract tests.

Each missing required input (resume, job description, title, company) must
raise the validation error and make ZERO provider calls. When all inputs are
present the service calls the provider exactly once.

Whether the generated letter invents no experience is not deterministically
testable: it depends on model output and is asserted only by the two-channel
prompt separation, not here.
"""

from __future__ import annotations

import pytest

from hirely.services.cover_letter import CoverLetterValidationError, generate_cover_letter
from tests.conftest import RecordingProvider

_VALID = {
    "resume_text": "Jane Developer, Python, FastAPI",
    "job_description": "Backend role building APIs",
    "job_title": "Backend Engineer",
    "company": "Acme",
}


@pytest.mark.parametrize("missing", ["resume_text", "job_description", "job_title", "company"])
def test_missing_required_input_makes_no_provider_call(missing: str) -> None:
    provider = RecordingProvider()
    kwargs = dict(_VALID)
    kwargs[missing] = "   "
    with pytest.raises(CoverLetterValidationError):
        generate_cover_letter(provider, model="m", **kwargs)
    assert provider.chat_calls == []


def test_valid_inputs_call_provider_once() -> None:
    provider = RecordingProvider(raw_text="Dear hiring manager, ...")
    letter = generate_cover_letter(provider, model="m", **_VALID)
    assert len(provider.chat_calls) == 1
    assert letter.title == "Backend Engineer"
    assert letter.company == "Acme"
    assert letter.body == "Dear hiring manager, ..."
