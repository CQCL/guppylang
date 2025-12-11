from dataclasses import dataclass
from typing import Any, ClassVar

from hugr.hugr.node_port import ToNode as HugrNode

from guppylang_internals.diagnostic import Fatal
from guppylang_internals.error import GuppyError

METADATA_MAX_QUBITS = "core.max_qubits"


@dataclass(frozen=True, init=True, kw_only=True)
class Metadata:
    max_qubits: int | None


@dataclass(frozen=True)
class MetadataAlreadySetError(Fatal):
    title: ClassVar[str] = "Metadata key already set"
    message: ClassVar[str] = "Received two values for the metadata key `{key}`"
    key: str


def add_metadata(
    node: HugrNode,
    metadata: Metadata | None = None,
    *,
    additional_metadata: dict[str, Any] | None = None,
) -> None:
    """Adds metadata to the given node, using standard keys for defined fields of the
    `Metadata` instance and forwarding surplus keyword arguments as is.
    """
    if metadata is not None and metadata.max_qubits is not None:
        if METADATA_MAX_QUBITS in node.metadata:  # TODO proper key
            raise GuppyError(MetadataAlreadySetError(None, METADATA_MAX_QUBITS))
        node.metadata[METADATA_MAX_QUBITS] = metadata.max_qubits

    if additional_metadata is not None:
        for key, value in additional_metadata.items():
            if key in node.metadata:
                raise GuppyError(MetadataAlreadySetError(None, key))
            node.metadata[key] = value


@dataclass(frozen=True)
class MaxQubitHintError(Fatal):
    title: ClassVar[str] = "Metadata key already set"
    message: ClassVar[str] = "Received two values for the metadata key `{key}`"
    key: str
