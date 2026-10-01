import pytest

from prospectsignal import orgnr
from prospectsignal.demo import fake_orgnr, make_demo_units


@pytest.mark.parametrize("value", ["923609016", "974760673", "NO 923 609 016 MVA", "923.609.016", "923 609 016"])
def test_valid_orgnr_passes_mod11(value):
    assert orgnr.is_valid(value)
    assert orgnr.validate(value) in {"923609016", "974760673"}


@pytest.mark.parametrize("value", ["923609017", "12345678", "1234567890", "ABCDEFGHI", "", None])
def test_invalid_orgnr_fails(value):
    assert not orgnr.is_valid(value)


def test_orgnr_stays_a_string_with_leading_zero():
    assert orgnr.normalise("012345678") == "012345678"
    assert isinstance(orgnr.normalise(12345678), str)
    with pytest.raises(ValueError):
        orgnr.validate(12345678)  # an integer has already lost its leading zero


def test_demo_orgnr_fail_mod11_on_purpose_and_keep_leading_zero():
    frame = make_demo_units()
    assert frame["org_nr"].map(lambda value: isinstance(value, str)).all()
    assert frame["org_nr"].str.len().eq(9).all()
    assert frame["org_nr"].str.startswith("0").all()
    assert not frame["org_nr"].map(orgnr.is_valid).any()
    assert frame["org_nr"].is_unique
    assert not orgnr.is_valid(fake_orgnr(1234567))


def test_display_format():
    assert orgnr.format_display("923609016") == "923 609 016"
