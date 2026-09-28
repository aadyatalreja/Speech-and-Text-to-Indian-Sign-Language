import pytest
from services.llm_service import mock_transform, parse_llm_json, LLMError
from services.sequence_service import SignSequenceService

CASES = {
    "Hello.": ["HELLO"], "Thank you.": ["THANK_YOU"], "I need help.": ["I", "HELP", "NEED"],
    "I am going to college tomorrow.": ["TOMORROW", "I", "COLLEGE", "GO"],
    "Where is the hospital?": ["HOSPITAL", "WHERE"], "Can you help me?": ["YOU", "HELP", "ME"],
    "See you tomorrow.": ["TOMORROW", "SEE", "YOU"],
}

@pytest.mark.parametrize("text,gloss", CASES.items())
def test_mock(text, gloss):
    assert mock_transform(text).gloss == gloss

def test_other_sentences():
    for t in ["I do not understand.", "What is your name?", "I want water."]:
        r = mock_transform(t)
        assert r.gloss and 0 <= r.confidence <= 1

def test_malformed_json_recovery():
    r = parse_llm_json('Sure! ```json\n{"intent":"statement","gloss":["i","go home"],"confidence":0.8}\n```')
    assert r.gloss == ["I", "GO_HOME"]
    with pytest.raises(LLMError):
        parse_llm_json("nonsense")

def test_unknown_sign_does_not_crash():
    seq, unknown = SignSequenceService().build(["I", "QUANTUM", "COMPUTER"])
    assert unknown == ["QUANTUM", "COMPUTER"] and len(seq) == 3 and not seq[1].available
