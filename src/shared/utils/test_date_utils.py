import sys
import pytest
from datetime import date
from shared.utils.date_utils import get_base_date

@pytest.fixture(autouse=True)
def fix_today(monkeypatch):
    # Freeze today's date to 2025-08-10 for deterministic testing
    class DummyDate(date):
        @classmethod
        def today(cls):
            return cls(2025, 8, 10)

    monkeypatch.setattr('shared.utils.date_utils.date', DummyDate)

@pytest.mark.parametrize(
    'argv, expected',
    [
        (['prog'], date(2025, 8, 9)),  # default to yesterday
        (['prog', '--base_date', '2025-08-08'], date(2025, 8, 8)),
    ]
)
def test_get_base_date_valid(monkeypatch, argv, expected):
    monkeypatch.setattr(sys, 'argv', argv)
    assert get_base_date() == expected


def test_get_base_date_invalid_format(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['prog', '--base_date', '08-10-2025'])
    with pytest.raises(ValueError):
        get_base_date()


def test_get_base_date_invalid_date(monkeypatch):
    # Invalid calendar date should raise ValueError
    monkeypatch.setattr(sys, 'argv', ['prog', '--base_date', '2025-02-30'])
    with pytest.raises(ValueError):
        get_base_date()
