import pytest

from pyggp._caching import size_str_to_int


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        ("1", 1),
        ("1.2", 1),
        ("1k", 1000),
        ("1ki", 1024),
        ("2M", 2_000_000),
        ("1 MiB", 1_048_576),
        ("1.5 G", 1_500_000_000),
        ("1.5 Gi", 1_610_612_736),
    ],
)
def test_size_str_to_int(string: str, expected: int) -> None:
    actual = size_str_to_int(string)
    assert actual == expected
