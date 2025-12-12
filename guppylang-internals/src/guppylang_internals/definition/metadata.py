from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Generic, TypeVar

from hugr.hugr.node_port import ToNode as HugrNode

from guppylang_internals.diagnostic import Fatal
from guppylang_internals.error import GuppyError

T = TypeVar("T")


@dataclass(init=True, kw_only=True)
class GuppyMetadataValue(Generic[T]):
    key: ClassVar[str]
    value: T | None = None


class MetadataMaxQubits(GuppyMetadataValue[int]):
    key = "core.max_qubits"


@dataclass(frozen=True, init=True, kw_only=True)
class GuppyMetadata:
    max_qubits: MetadataMaxQubits = field(default_factory=MetadataMaxQubits, init=False)


@dataclass(frozen=True)
class MetadataAlreadySetError(Fatal):
    title: ClassVar[str] = "Metadata key already set"
    message: ClassVar[str] = "Received two values for the metadata key `{key}`"
    key: str


@dataclass(frozen=True)
class ReservedMetadataKeysError(Fatal):
    title: ClassVar[str] = "Metadata key is reserved"
    message: ClassVar[str] = (
        "The following metadata keys are reserved by Guppy but provided in additional "
        "metadata: `{keys}`"
    )
    keys: set[str]


def add_metadata(
    node: HugrNode,
    metadata: GuppyMetadata | None = None,
    *,
    additional_metadata: dict[str, Any] | None = None,
) -> None:
    """Adds metadata to the given node, using standard keys for defined fields of the
    `Metadata` instance and forwarding surplus keyword arguments as is.
    """
    if metadata is not None:
        for f in fields(GuppyMetadata):
            field_value: GuppyMetadataValue[Any] = getattr(metadata, f.name)
            if field_value.key in node.metadata:
                raise GuppyError(MetadataAlreadySetError(None, field_value.key))
            node.metadata[field_value.key] = field_value.value

    if additional_metadata is not None:
        reserved_keys: set[str] = {f.type.key for f in fields(GuppyMetadata)}
        used_reserved_keys = reserved_keys.intersection(additional_metadata.keys())
        if len(used_reserved_keys) > 0:
            raise GuppyError(ReservedMetadataKeysError(None, keys=used_reserved_keys))

        for key, value in additional_metadata.items():
            node.metadata[key] = value
