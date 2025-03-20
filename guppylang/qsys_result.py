r"""
Quantinuum system results and utilities.

Includes conversions to traditional distributions over bitstrings if a tagging
convention is used, including conversion to a pytket BackendResult.

Under this convention, tags are assumed to be a name of a bit register unless they fit
the regex pattern `^([a-z][\w_]*)\[(\d+)\]$` (like `my_Reg[12]`) in which case they
are assumed to refer to the nth element of a bit register.

For results of the form ``` result("<register>", value) ``` `value` can be `{0, 1}`,
wherein the register is assumed to be length 1, or lists over those values,
wherein the list is taken to be the value of the entire register.

For results of the form ``` result("<register>[n]", value) ``` `value` can only be
`{0,1}`.
The register is assumed to be at least `n+1` in size and unset
elements are assumed to be `0`.

Subsequent writes to the same register/element in the same shot will overwrite.

To convert to a `BackendResult` all registers must be present in all shots, and register
sizes cannot change between shots.

"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pytket.backends.backendresult import BackendResult

try:
    from warnings import deprecated  # type: ignore[attr-defined]
except ImportError:
    # Python < 3.13
    def deprecated(_msg):  # type: ignore[no-redef]
        def _deprecated(func):
            return func

        return _deprecated


#: Primitive data types that can be returned by a result
DataPrimitive = int | float | bool
#: Data value that can be returned by a result: a primitive or a list of primitives
DataValue = DataPrimitive | list[DataPrimitive]
TaggedResult = tuple[str, DataValue]
# Pattern to match register index in tag, e.g. "reg[0]"
REG_INDEX_PATTERN = re.compile(r"^([a-z][\w_]*)\[(\d+)\]$")

BitChar = Literal["0", "1"]


@dataclass
class QsysShot:
    """Results from a single shot execution."""

    entries: list[TaggedResult] = field(default_factory=list)

    def __init__(self, entries: Iterable[TaggedResult] | None = None):
        self.entries = list(entries or [])

    def append(self, tag: str, data: DataValue) -> None:
        self.entries.append((tag, data))

    def as_dict(self) -> dict[str, DataValue]:
        """Convert results to a dictionary.

        For duplicate tags, the last value is used.

        Returns:
            dict: A dictionary where the keys are the tags and the
            values are the data.

        Example:
            >>> results = Results()
            >>> results.append("tag1", 1)
            >>> results.append("tag2", 2)
            >>> results.append("tag2", 3)
            >>> results.as_dict()
            {"tag1": 1, "tag2": 3}
        """
        return dict(self.entries)

    def to_register_bits(self) -> dict[str, str]:
        """Convert results to a dictionary of register bit values."""
        reg_bits: dict[str, list[BitChar]] = {}

        res_dict = self.as_dict()
        # relies on the fact that dict preserves insertion order
        for tag, data in res_dict.items():
            match = re.match(REG_INDEX_PATTERN, tag)
            if match is not None:
                reg_name, reg_index_str = match.groups()
                reg_index = int(reg_index_str)

                if reg_name not in reg_bits:
                    # Initialize register counts to False
                    reg_bits[reg_name] = ["0"] * (reg_index + 1)
                bitlst = reg_bits[reg_name]
                if reg_index >= len(bitlst):
                    # Extend register counts with "0"
                    bitlst += ["0"] * (reg_index - len(bitlst) + 1)

                bitlst[reg_index] = _cast_primitive_bit(data)
                continue
            match data:
                case list(vs):
                    reg_bits[tag] = [_cast_primitive_bit(v) for v in vs]
                case _:
                    reg_bits[tag] = [_cast_primitive_bit(data)]

        return {reg: "".join(bits) for reg, bits in reg_bits.items()}

    def collate_tags(self) -> dict[str, list[DataValue]]:
        """Collate all the entries with the same tag in to a dictionary with a list
        containing all the data for that tag."""

        tags: dict[str, list[DataValue]] = defaultdict(list)
        for tag, data in self.entries:
            tags[tag].append(data)
        return dict(tags)


@deprecated("Use QsysShot instead.")
class HResult(QsysShot):
    """Deprecated alias for QsysShot."""


def _cast_primitive_bit(data: DataValue) -> BitChar:
    if isinstance(data, int) and data in {0, 1}:
        return str(data)  # type: ignore[return-value]
    raise ValueError(f"Expected bit data for register value found {data}")


@dataclass
class QsysResult:
    """Results accumulated over multiple shots."""

    results: list[QsysShot]

    def __init__(
        self, results: Iterable[QsysShot | Iterable[TaggedResult]] | None = None
    ):
        self.results = [
            res if isinstance(res, QsysShot) else QsysShot(res) for res in results or []
        ]

    def register_counts(
        self, strict_names: bool = False, strict_lengths: bool = False
    ) -> dict[str, Counter[str]]:
        """Convert results to a dictionary of register counts.

        Returns:
            dict: A dictionary where the keys are the register names
            and the values are the counts of the register bitstrings.
        """
        return {
            reg: Counter(bitstrs)
            for reg, bitstrs in self.register_bitstrings(
                strict_lengths=strict_lengths, strict_names=strict_names
            ).items()
        }

    def register_bitstrings(
        self, strict_names: bool = False, strict_lengths: bool = False
    ) -> dict[str, list[str]]:
        """Convert results to a dictionary from register name to list of bitstrings over
        the shots.

        Args:
            strict_names: Whether to enforce that all shots have the same
                registers.
            strict_lengths: Whether to enforce that all register bitstrings have
                the same length.

        """

        shot_dct: dict[str, list[str]] = defaultdict(list)
        for shot in self.results:
            bitstrs = shot.to_register_bits()
            for reg, bitstr in bitstrs.items():
                if (
                    strict_lengths
                    and reg in shot_dct
                    and len(shot_dct[reg][0]) != len(bitstr)
                ):
                    raise ValueError(
                        "All register bitstrings must have the same length."
                    )
                shot_dct[reg].append(bitstr)
            if strict_names and not bitstrs.keys() == shot_dct.keys():
                raise ValueError("All shots must have the same registers.")
        return dict(shot_dct)

    def to_pytket(self) -> BackendResult:
        """Convert results to a pytket BackendResult.

        Returns:
            BackendResult: A BackendResult object with the shots.

        Raises:
            ImportError: If pytket is not installed.
            ValueError: If a register's bitstrings have different lengths or not all
            registers are present in all shots.
        """
        try:
            from pytket._tket.unit_id import Bit
            from pytket.backends.backendresult import BackendResult
            from pytket.utils.outcomearray import OutcomeArray
        except ImportError as e:
            raise ImportError(
                "Pytket is an optional dependency, install with the `pytket` extra"
            ) from e
        reg_shots = self.register_bitstrings(strict_lengths=True, strict_names=True)
        reg_sizes: dict[str, int] = {
            reg: len(next(iter(reg_shots[reg]), "")) for reg in reg_shots
        }
        registers = list(reg_shots.keys())
        bits = [Bit(reg, i) for reg in registers for i in range(reg_sizes[reg])]

        int_shots = [
            int("".join(reg_shots[reg][i] for reg in registers), 2)
            for i in range(len(self.results))
        ]
        return BackendResult(
            shots=OutcomeArray.from_ints(int_shots, width=len(bits)), c_bits=bits
        )

    def _collated_shots_iter(self) -> Iterable[dict[str, list[DataValue]]]:
        for shot in self.results:
            yield shot.collate_tags()

    def collated_shots(self) -> list[dict[str, list[DataValue]]]:
        """For each shot generate a dictionary of tags to collated data."""
        return list(self._collated_shots_iter())

    def collated_counts(self) -> Counter[tuple[tuple[str, str], ...]]:
        """Calculate counts of bit strings for each tag by collating across shots using
        `HShots.tag_collated_shots`. Each `result` entry per shot is seen to be
        appending to the bitstring for that tag.

        If the result value is a list, it is flattened and appended to the bitstring.

        Example:
            >>> res = HShots([HResult([("a", 1), ("a", 0)]), HResult([("a", [0, 1])])])
            >>> res.collated_counts()
            Counter({(("a", "10"),): 1, (("a", "01"),): 1})

        Raises:
            ValueError: If any value is a float.
        """
        return Counter(
            tuple((tag, _flat_bitstring(data)) for tag, data in d.items())
            for d in self._collated_shots_iter()
        )

@deprecated("Use QsysResult instead.")
class HShots(QsysResult):
    """Deprecated alias for QsysResult."""

def _flat_bitstring(data: Iterable[DataValue]) -> str:
    return "".join(_cast_primitive_bit(prim) for prim in _flatten(data))


def _flatten(itr: Iterable[DataValue]) -> Iterable[DataPrimitive]:
    for i in itr:
        if isinstance(i, list):
            yield from _flatten(i)
        else:
            yield i
