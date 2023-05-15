""" Custom Pydantic BaseModel with additional features needed to interact with Serde-serialised Enums in Rust """

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, Extra, root_validator
from pydantic.fields import ModelField
from typing import get_origin, get_args, Literal, Optional, Union, Any

"""
This is all very hacky, but we need the following two extra Pydantic features
to be compatible with the way Serde serialises Rust Enums:

1. EXTERNALLY TAGGED UNIONS

Allow unions to be discriminated during (de)serialisation using an outer
tag. Note that we only support discriminated unions where each union member 
is itself a BaseModel. For example:

    class Cat(BaseModel):
        cat_property: str
    
    class Dog(BaseModel):
        dog_property: str
    
    class Foo(BaseModel):
        pet: Union[Cat, Dog] = Field(tagged_union=True)
    
    Foo(pet=Cat(cat_property="cute")).dict()  # -> {"pet": {"Cat": {"cat_property": "cute" }}}
    Foo(pet=Dog(dog_property="loud")).dict()  # -> {"pet": {"Dog": {"dog_property": "loud" }}}

We need this because Rust enums are serialised via such an outer tag by Serde.
There has been some discussion around this feature for Pydantic 2.0, but it
is not available yet. See: 
    https://github.com/pydantic/pydantic-core/issues/102
    https://github.com/pydantic/pydantic/issues/5244


2. MODEL SERIALISATION VIA LISTS

Support serialisation of models via lists instead of dicts. In that case, 
the fields can be identified via the position in the list instead of the 
name. This requires the user to annotate the model field with position 
indices. If the model only has a single field, no list is required and 
the entry is just serialised on its own:

    class Foo(BaseModel, list=True):
        x: int = Field(position=0)
        y: str = Field(position=1)
        
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


def is_tagged_union(field: ModelField) -> bool:
    # When defining a Pydantic field using `foo: ty = Field(..., tagged_union=True)`,
    # the unknown argument `tagged_union` is placed into the `field_info.extra`
    # of the field.
    return "tagged_union" in field.field_info.extra and field.field_info.extra["tagged_union"] is True


def union_members(ty: type) -> tuple[Any, ...]:
    if get_origin(ty) != Union:
        raise ValueError("Not a union type")
    return get_args(ty)


class BaseModel(PydanticBaseModel, extra=Extra.forbid):
    """ Custom Pydantic BaseModel with support for externally tagged unions and list serialisation. """

    # We emulate externally tagged unions using Pydantic's discriminated
    # union feature. To make things easy, we just give every model a dummy
    # discriminator field that is only used if the model occurs inside
    # a discriminated union.
    discriminator_: Literal[""] = Field("", repr=False, exclude=True)

    # Store ordering of fields in case this is a list model
    _field_order: Optional[list[str]] = None

    # Serialisation name of this class. Per default, this will be the class
    # name, but can be changed by passing `serialize_as=...` when defining a
    # subclass
    _name: str

    @root_validator(pre=True)
    def preprocess_tagged_union(cls, values):
        # We need to handle dict-parsing of externally tagged unions ourselves using
        # this custom root validator
        for field_name, value in values.items():
            field = cls.__fields__[field_name]
            if is_tagged_union(field):
                members = {m._name: m for m in union_members(field.type_)}
                # Look for singleton dict with class name as key
                if isinstance(value, dict) and len(value) == 1:
                    (name, v), = value.items()
                    if name in members:
                        member = members[name]
                        # Call the member constructor using *args if it's a list model
                        if issubclass(member, BaseModel) and member._field_order is not None:
                            if not isinstance(v, list):
                                v = [v]
                            values[field_name] = member(*v)
                        else:
                            values[field_name] = member(**v)
                    else:
                        raise ValueError(f"`{name}` is not a valid union member")
                # If it's just a string, this could be a model without fields
                elif isinstance(value, str) and value in members:
                    values[field_name] = members[value]()
        return values

    def __init_subclass__(cls, list=False, serialize_as=None, **kwargs):
        super().__init_subclass__(**kwargs)

        # Initialise the discriminator field with the correct class name
        cls._name = serialize_as or cls.__name__
        cls.__fields__["discriminator_"].type_ = Literal[cls._name]
        cls.__fields__["discriminator_"].default = cls._name

        # If any field is marked as a tagged union, turn it into a Pydantic
        # discriminated union
        fields = cls.__fields__.copy()
        fields.pop("discriminator_", None)  # Ignore `discriminator_` field
        for field in fields.values():
            if is_tagged_union(field):
                if get_origin(field.type_) is not Union:
                    raise ValueError("`tagged_union` can only be set for fields of `Union[...]` type")
                field.discriminator_key = "discriminator_"

        # Read out field ordering if it is a list model
        if list:
            if len(fields) == 1:
                f, = fields.keys()
                cls._field_order = [f]
                return

            cls._field_order = [None for _ in range(len(fields))]
            for field_name, field in fields.items():
                if "position" not in field.field_info.extra:
                    raise ValueError(f"Add field positions for ListModel using `... = Field(position=xxx)`")
                pos = field.field_info.extra["position"]
                if not 0 <= pos <= len(fields) - 1:
                    raise ValueError(f"Invalid position: {pos}")
                if cls._field_order[pos] is not None:
                    raise ValueError(f"Position not unique: {pos}")
                cls._field_order[pos] = field_name

            # Patch __init__ function to accept positional arguments. By doing this
            # here we can trick the Pydantic IDE support to still give hints for the
            # original constructor
            old_init = cls.__init__

            def patched_init(self, *args, **kwargs_):
                if len(args) == len(fields):
                    for (i, arg) in enumerate(args):
                        kwargs_[self._field_order[i]] = arg
                old_init(self, **kwargs_)

            cls.__init__ = patched_init

    def dict(self, *args, **kwargs):
        # We override the dict() method to alter the serialisation behaviour
        d = super().dict(*args, **kwargs)
        # Add outer tag to tagged union fields
        for field_name, field in self.__fields__.items():
            if is_tagged_union(field):
                name = self.__getattribute__(field_name).__class__._name
                x = d[field_name]
                d[field_name] = name if len(x) == 0 else {name: x}
        # Turn into list if we're a list model
        if self._field_order is not None:
            ordered = [d[f] for f in self._field_order]
            return ordered[0] if len(ordered) == 1 else ordered
        return d
