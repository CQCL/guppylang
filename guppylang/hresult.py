r"""
Quantinuum system results and utilities.

Includes conversions to traditional distributions over bitstrings if a tagging
convention is used, including conversion to a pytket BackendResult.

Under this convention, tags are assumed to be a name of a bit register unless they fit
the regex pattern `^([a-z][\w_]*)\[(\d+)\]$` (like `my_Reg[12]`) in which case they
are assumed to refer to the nth element of a bit register.

For results of the form ``` result("<register>", value) ``` `value` can be `{0, 1, True,
False}`, wherein the register is assumed to be length 1, or lists over those values,
wherein the list is taken to be the value of the entire register.

For results of the form ``` result("<register>[n]", value) ``` `value` can only be `{0,
1, True, False}`. The register is assumed to be at least `n+1` in size and unset
elements are assumed to be `0`.

Subsequent writes to the same register/element in the same shot will overwrite.

To convert to a `BackendResult` all registers must be present in all shots, and register
sizes cannot change between shots.

"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pytket.backends.backendresult import BackendResult

#: Primitive data types that can be returned by a result
DataPrimitive = int | float | bool
#: Data value that can be returned by a result: a primitive or a list of primitives
DataValue = DataPrimitive | list[DataPrimitive]
TaggedResult = tuple[str, DataValue]
# Pattern to match register index in tag, e.g. "reg[0]"
REG_INDEX_PATTERN = re.compile(r"^([a-z][\w_]*)\[(\d+)\]$")


@dataclass
class HResult:
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

    def to_register_bits(self) -> dict[str, list[bool]]:
        """Convert results to a dictionary of register bit values."""
        reg_bits: dict[str, list[bool]] = {}

        res_dict = self.as_dict()
        for tag, data in res_dict.items():
            match = re.match(REG_INDEX_PATTERN, tag)
            if match is not None:
                reg_name, reg_index_str = match.groups()
                reg_index = int(reg_index_str)

                if reg_name not in reg_bits:
                    # Initialize register counts to False
                    reg_bits[reg_name] = [False] * (reg_index + 1)
                bitlst = reg_bits[reg_name]
                if reg_index >= len(bitlst):
                    # Extend register counts with False
                    bitlst += [False] * (reg_index - len(bitlst) + 1)

                bitlst[reg_index] = _cast_primitive_bool(data)
                continue
            match data:
                case list(vs):
                    reg_bits[tag] = [_cast_primitive_bool(v) for v in vs]
                case _:
                    reg_bits[tag] = [_cast_primitive_bool(data)]

        return reg_bits

    def to_register_bitstrings(self) -> dict[str, str]:
        """Convert results to a dictionary of register bitstrings."""
        reg_bits = self.to_register_bits()
        return {reg: bools_to_bitstring(bits) for reg, bits in reg_bits.items()}


def bools_to_bitstring(bools: list[bool]) -> str:
    return "".join("1" if b else "0" for b in bools)


def _cast_primitive_bool(data: DataValue) -> bool:
    match data:
        case bool(v):
            return v
        case int(1):
            return True
        case int(0):
            return False
        case _:
            raise ValueError(f"Expected bool data for register value found {data}")


@dataclass
class Shots:
    """Results accumulated over multiple shots."""

    results: list[HResult] = field(default_factory=list)

    def __init__(
        self, results: Iterable[HResult | Iterable[TaggedResult]] | None = None
    ):
        self.results = [
            res if isinstance(res, HResult) else HResult(res) for res in results or []
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
            bitstrs = shot.to_register_bitstrings()
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
        return shot_dct

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
        counts = self.register_bitstrings(strict_lengths=True, strict_names=True)
        reg_sizes: dict[str, int] = {
            reg: len(next(iter(counts[reg]), "")) for reg in counts
        }
        registers = list(counts.keys())
        bits = [Bit(reg, i) for reg in registers for i in range(reg_sizes[reg])]
        int_shots = [
            [ord(bitval) - 48 for reg in registers for bitval in counts[reg][i]]
            for i in range(len(self.results))
        ]
        return BackendResult(shots=OutcomeArray.from_readouts(int_shots), c_bits=bits)
