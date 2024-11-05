import re
from collections import Counter

import pytest

from guppylang.hresult import REG_INDEX_PATTERN, HResult, HShots


@pytest.mark.parametrize(
    ("identifier", "match"),
    [
        ("sadfj", None),
        ("asdf_sdf", None),
        ("asdf3h32", None),
        ("dsf[3]asdf", None),
        ("_s34fd_fd[12]", None),
        ("afsd3[34]sdf", None),
        ("asdf[2]", ("asdf", 2)),
        ("as3df[21234]", ("as3df", 21234)),
        ("as3ABdfAB[2]", ("as3ABdfAB", 2)),
    ],
)
def test_reg_index_pattern_match(identifier, match: tuple[str, int] | None):
    """Test regex pattern matches tags indexing in to registers."""
    mtch = re.match(REG_INDEX_PATTERN, identifier)
    if mtch is None:
        assert match is None
        return
    parsed = (mtch.group(1), int(mtch.group(2)))
    assert parsed == match


def test_as_dict():
    results = HResult()
    results.append("tag1", 1)
    results.append("tag2", 2)
    results.append("tag2", 3)
    assert results.as_dict() == {"tag1": 1, "tag2": 3}


def test_to_register_bits():
    results = HResult()
    results.append("c[0]", 1)
    results.append("c[1]", 0)
    results.append("c[3]", 1)
    results.append("d", [1, 0, 1, 0])
    results.append("x[5]", 1)
    results.append("x", 0)

    assert results.to_register_bits() == {"c": "1001", "d": "1010", "x": "0"}

    shots = HShots([results, results])
    assert shots.register_counts() == {
        "c": Counter({"1001": 2}),
        "d": Counter({"1010": 2}),
        "x": Counter({"0": 2}),
    }


@pytest.mark.parametrize(
    "results",
    [
        HResult([("t", 1.0)]),
        HResult([("t[1]", 1.0)]),
        HResult([("t", [1.0])]),
        HResult([("t[0]", [0])]),
        HResult([("t[0]", 3)]),
    ],
)
def test_to_register_bits_bad(results: HResult):
    with pytest.raises(ValueError, match="Expected bit"):
        _ = results.to_register_bits()


def test_counter():
    shot1 = HResult()
    shot1.append("c", [1, 0, 1, 0])
    shot1.append("d", [1, 0, 1])

    shot2 = HResult()
    shot2.append("c", [1, 0, 1])

    shots = HShots([shot1, shot2])
    assert shots.register_counts() == {
        "c": Counter({"1010": 1, "101": 1}),
        "d": Counter({"101": 1}),
    }
    with pytest.raises(ValueError, match="same length"):
        _ = shots.register_counts(strict_lengths=True)

    with pytest.raises(ValueError, match="All shots must have the same registers"):
        _ = shots.register_counts(strict_names=True)


def test_pytket():
    """Test that results observing strict tagging conventions can be converted to pytket
    shot results."""
    pytest.importorskip("pytket", reason="pytket not installed")

    hsim_shots = HShots(([("c", [1, 0]), ("d", [1, 0])], [("c", [0, 0]), ("d", [1, 0])]))

    pytket_result = hsim_shots.to_pytket()

    from pytket._tket.unit_id import Bit
    from pytket.backends.backendresult import BackendResult
    from pytket.utils.outcomearray import OutcomeArray

    bits = [Bit("c", 0), Bit("c", 1), Bit("d", 0), Bit("d", 1)]
    expected = BackendResult(
        c_bits=bits, shots=OutcomeArray.from_readouts([[1, 0, 1, 0], [0, 0, 1, 0]])
    )

    assert pytket_result == expected
