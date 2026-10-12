import pytest
from execution.spotlight_indexer import SpotlightEngine, SafeMathEvaluator, SpotlightItem

def test_safe_math_evaluator():
    evaluator = SafeMathEvaluator()
    assert evaluator.evaluate("45 * 12") == 540.0
    assert evaluator.evaluate("100 / 4 + 25") == 50.0
    assert evaluator.evaluate("2 ^ 8") == 256.0
    assert evaluator.evaluate("sqrt(144)") == 12.0
    assert evaluator.evaluate("15% of 850") == 127.5
    assert evaluator.evaluate("invalid syntax here") is None

def test_spotlight_engine_math_search():
    engine = SpotlightEngine()
    results = engine.search("50 * 4")
    assert len(results) >= 1
    assert results[0].category == "MATH"
    assert "200" in results[0].title

def test_spotlight_engine_conversion_search():
    engine = SpotlightEngine()
    results = engine.search("10 km to miles")
    assert len(results) >= 1
    assert results[0].category == "MATH"
    assert "miles" in results[0].title

def test_spotlight_engine_system_tools_search():
    engine = SpotlightEngine()
    engine.build_index()
    # Calculator match
    results = engine.search("calc")
    assert any(item.category == "APP" and "Calculator" in item.title for item in results)

    # Sound settings match
    results_settings = engine.search("open sound settings")
    assert any(item.category == "SETTING" for item in results_settings)

def test_spotlight_engine_web_fallback_when_not_installed():
    engine = SpotlightEngine()
    # Something definitely not installed locally
    results = engine.search("open non_existent_quantum_app_12345")
    assert len(results) >= 1
    assert results[-1].category == "WEB"
    assert "google.com" in results[-1].target
