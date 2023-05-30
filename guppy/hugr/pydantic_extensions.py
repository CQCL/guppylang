""" Custom Pydantic BaseModel with additional features needed to interact with Serde-serialised Enums in Rust """

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, Extra, root_validator
from typing import get_origin, get_args, Literal, Union, Any, Optional, Callable

"""
This is all very hacky, but we need the following two extra Pydantic features
to be compatible with the way Serde serialises Rust Enums:

1. EXTERNALLY TAGGED UNIONS

Allow unions to be discriminated during (de)serialisation using an outer
tag. Each BaseModel in the union must be tagged. For example:

    class Cat(BaseModel, tagged=True):
        cat_property: str

    class Dog(BaseModel, tagged=True):
        dog_property: str

    class Foo(BaseModel):
        pet: Union[Cat, Dog]

    Foo(pet=Cat(cat_property="cute")).dict()  # -> {"pet": {"Cat": {"cat_property": "cute" }}}
    Foo(pet=Dog(dog_property="loud")).dict()  # -> {"pet": {"Dog": {"dog_property": "loud" }}}

We need this because Rust enums are serialised via such an outer tag by Serde.
There has been some discussion around a similar feature for Pydantic 2.0, but
it is not available yet. See:
    https://github.com/pydantic/pydantic-core/issues/102
    https://github.com/pydantic/pydantic/issues/5244


2. MODEL SERIALISATION VIA LISTS

Support serialisation of models via lists instead of dicts. In that case,
the fields can be identified via the position in the list instead of the
name. If the model only has a single field, the entry is just serialised
on its own without wrapping it into a list:

    class Foo(BaseModel, list=True):
        x: int
        y: str

    class Bar(BaseModel, list=True):
        z: float

    class Baz(BaseModel, list=True):
        pass

    Foo(x=42, y="abc").dict()  # -> [42, "abc"]
    Bar(z=13.37).dict()  # -> 13.37
    Baz().dict()  # -> "Baz"

We need this feature since Rust's tuple enum variants are serialised as
lists by Serde. Note that deserialization is only implemented in the
case where the list model occurs inside of a tagged union, since this
is the only case we need for our use case at the moment.
"""


def is_tagged_union(ty: type) -> bool:
    """
    Checks if a given type is a tagged union, i.e. a union  where all
    members are tagged models.
    """
    return get_origin(ty) is Union and all(issubclass(m, BaseModel) and m._tagged for m in get_args(ty))


def contains_tagged_union(ty: type) -> bool:
    """
    Checks if a type is a tagged union or a list-, set-, or tuple-type
    containing tagged unions somewhere in its arguments.
    """
    if is_tagged_union(ty):
        return True
    elif get_origin(ty) in [list, set]:
        return contains_tagged_union(get_args(ty)[0])
    elif get_origin(ty) is tuple:
        return any(contains_tagged_union(t) for t in get_args(ty))
    return False


class BaseModel(PydanticBaseModel, extra=Extra.forbid):
    """ Custom Pydantic BaseModel with support for externally tagged unions and list serialisation. """
    # We give every model a tag field that is set to the class name (this
    # can be customised by passing `tag=...` when defining a subclass).
    # Note that this is *not* a private field, so pydantic can use it to
    # disambiguate isomorphic models in a union.
    tag_: Literal[""] = Field("", repr=False, exclude=True)

    # Whether this model is serialised as a list instead of a dict. This
    # can be set by passing `list=True` when defining a subclass.
    _is_list_model: bool = False

    # Whether to add the model tag externally when serialising the model.
    # This can be set by passing `tagged=True` when defining a subclass.
    _tagged: bool = False

    def __init_subclass__(cls, list: bool = False, tagged: bool = False, tag: Optional[str] = None,
                          **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._is_list_model = list
        cls._tagged = tagged

        # Initialise the tag field with the correct class name
        cls.__fields__["tag_"].type_ = Literal[tag or cls.__name__]
        cls.__fields__["tag_"].default = tag or cls.__name__

        for field in cls.__fields__.values():
            check_type_valid(field.outer_type_)

        # We patch the __init__ function here instead of overriding, so
        # we can trick the Pydantic IDE support to still give hints for
        # the original constructor
        old_init = cls.__init__
        cls.__init__ = lambda self, *args, **kwargs_: cls.__new_init__(self, old_init, *args, **kwargs_)  # type: ignore

    def __new_init__(self, old_init: Any, *args: Any, **kwargs: Any) -> None:
        # Accept positional arguments for list models
        fields = self.__fields__.copy()
        fields.pop("tag_")  # Ignore `tag_` field
        if self._is_list_model and len(kwargs) == 0 and len(args) == len(fields):
            field_order = list(fields)
            for (i, arg) in enumerate(args):
                kwargs[field_order[i]] = arg
            args = tuple()
        old_init(self, *args, **kwargs)

    @root_validator(pre=True)
    def parse_tagged_union(cls, values: dict[str, Any]) -> dict[str, Any]:
        # We need to handle dict-parsing of externally tagged unions ourselves using
        # this custom root validator
        for field_name, value in values.items():
            if field_name not in cls.__fields__:
                continue
            field = cls.__fields__[field_name]
            if contains_tagged_union(field.outer_type_):
                values[field_name] = parse_tagged_union(field.outer_type_, values[field_name])
        return values

    def dict(self, *args: Any, **kwargs: Any) -> Union[dict[str, Any], list[Any], str]:  # type: ignore
        # We override the dict() method to alter the serialisation behaviour
        d = super().dict(*args, **kwargs)
        if self._is_list_model:
            vs = [d[f] for f in self.__fields__ if f != "tag_"]
            d = vs[0] if len(vs) == 1 else vs
        if self._tagged:
            return self.tag_ if len(d) == 0 else {self.tag_: d}
        return d


def check_type_valid(ty: type) -> None:
    """
    Raises an exception if the type is invalid. At the moment this only
    checks if all members of a tagged union are tagged.
    """
    o = get_origin(ty)
    if o is Union:
        if all(issubclass(m, BaseModel) and m._tagged for m in get_args(ty)):
            return
        if any(issubclass(m, BaseModel) and m._tagged for m in get_args(ty)):
            raise ValueError("If one Union member is tagged, all have to be")
    elif o in [list, set]:
        check_type_valid(get_args(ty)[0])
    elif get_origin(ty) is tuple:
        for t in get_args(ty):
            check_type_valid(t)


def parse_tagged_union(ty: type, value: Any) -> Any:
    """
    Parses a dict-encoded tagged union value. If the encoding is invalid,
    `value` is returned unchanged.
    """
    if is_tagged_union(ty):
        members = {m.__fields__["tag_"].default: m for m in get_args(ty)}
        # Look for singleton dict with class name as key
        if isinstance(value, dict) and len(value) == 1:
            (name, v), = value.items()
            if name in members:
                member = members[name]
                # Call the member constructor using *args if it's a list model
                if issubclass(member, BaseModel) and member._is_list_model:
                    if not isinstance(v, list):
                        v = [v]
                    return member(*v)
                else:
                    return member(**v)
            else:
                raise ValueError(f"`{name}` is not a valid union member")
        # If it's just a string, this must be a model without fields
        elif isinstance(value, str):
            if value in members:
                return members[value]()
            else:
                raise ValueError(f"`{value}` is not a valid union member")
        # If value is anything else, we just fall through and let Pydantic
        # validation handle it
    elif contains_tagged_union(ty):
        if (isinstance(value, list) and get_origin(ty) is list) or (isinstance(value, set) and get_origin(ty) is set):
            return type(value)(parse_tagged_union(get_args(ty)[0], val) for val in value)
        elif isinstance(value, tuple) and get_origin(ty) is tuple:
            return tuple(parse_tagged_union(t, val) for t, val in zip(get_args(ty), value))
    return value
