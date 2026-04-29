import pytest
from unittest.mock import patch, MagicMock
from pipeline.processors.sentiment import analyze_sentiment, _score_from_label


def test_score_from_label_negative():
    assert _score_from_label("negative", 0.9) == -0.9


def test_score_from_label_positive():
    assert _score_from_label("positive", 0.8) == 0.8


def test_score_from_label_neutral():
    assert _score_from_label("neutral", 0.7) == 0.0


def test_analyze_sentiment_no_token():
    """When no HF token is set, should return neutral fallback."""
    with patch("pipeline.processors.sentiment.HF_API_TOKEN", ""):
        result = analyze_sentiment("Iran launched missiles")
        assert result["label"] == "neutral"


def test_analyze_sentiment_api_response():
    """Mocks a successful HuggingFace API response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        [
            {"label": "LABEL_0", "score": 0.92},
            {"label": "LABEL_1", "score": 0.05},
            {"label": "LABEL_2", "score": 0.03},
        ]
    ]

    with patch("pipeline.processors.sentiment.HF_API_TOKEN", "hf_fake_token"):
        with patch("requests.post", return_value=mock_response):
            result = analyze_sentiment("Missiles were launched in an attack")
            assert result["label"] == "negative"
            assert result["score"] < 0


def test_analyze_sentiment_empty_text():
    result = analyze_sentiment("")
    assert result["label"] == "neutral"