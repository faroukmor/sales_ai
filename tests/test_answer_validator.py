# tests/test_answer_validator.py
from services.answer_validator import AnswerValidator, numbers_in

v = AnswerValidator()


def test_answer_without_numbers_is_ok():
    assert v.validate("OLED pixels emit their own light.", ["any text"]).ok


def test_number_present_in_evidence_is_ok():
    assert v.validate("It has 16 GB of RAM.", ["The laptop has 16 GB RAM."]).ok


def test_number_missing_from_evidence_is_rejected():
    result = v.validate("It costs 900,000 DZD.", ["The price is 90,000 DZD."])
    assert not result.ok
    assert result.unsupported_numbers == ("900000",)


def test_thousands_separators_are_normalized():
    assert v.validate("Price 90.000 DZD", ["price: 90,000 dzd"]).ok
    assert v.validate("Price 90000", ["price: 90,000"]).ok


def test_decimal_equivalence():
    assert v.validate("2.0 kg", ["weight 2 kg"]).ok


def test_arabic_indic_digits_are_normalized():
    assert v.validate("السعر ١٦ جيجا", ["16 GB"]).ok


def test_list_markers_are_ignored():
    answer = "1. First point\n2) Second point"
    assert v.validate(answer, ["no numbers here"]).ok


def test_empty_evidence_rejects_any_number():
    assert not v.validate("There are 3 types.", []).ok


def test_numbers_in_returns_normalized_set():
    assert numbers_in("16 GB, 1,000 DZD and 1.5 kg") == {"16", "1000", "1.5"}
