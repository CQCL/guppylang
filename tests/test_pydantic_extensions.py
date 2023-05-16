import pytest
from typing import Union
from pydantic import Field, ValidationError

from guppy.hugr.pydantic_extensions import BaseModel


class A(BaseModel):
    x: int
    y: bool


class B(BaseModel, serialize_as="BB"):
    z: str


class C(BaseModel):
    union: Union[A, B] = Field(tagged_union=True)


def test_serialize_tagged_union():
    c1 = C(union=A(x=42, y=True))
    c2 = C(union=B(z="foo"))
    assert c1.dict() == {"union": {"A": {"x": 42, "y": True}}}
    assert c2.dict() == {"union": {"BB": {"z": "foo"}}}


def test_deserialize_tagged_union():
    c1 = {"union": {"A": {"x": 42, "y": True}}}
    c2 = {"union": {"BB": {"z": "foo"}}}
    assert C(**c1) == C(union=A(x=42, y=True))
    assert C(**c2) == C(union=B(z="foo"))


def test_not_in_union():
    with pytest.raises(ValidationError) as exc_info:
        c = {"union": {"D": {"x": 42, "y": True}}}
        C(**c)
    assert exc_info.value.args[0][0].exc.args[0] == "`D` is not a valid union member"


def test_not_in_union_empty():
    with pytest.raises(ValidationError, match="`D` is not a valid union member"):
        c = {"union": "D"}
        C(**c)


def test_not_a_union():
    with pytest.raises(Exception) as exc_info:
        class Foo(BaseModel):
            x: int = Field(tagged_union=True)
    assert exc_info.value.args[0] == "`tagged_union` can only be set for fields of `Union[...]` type"


def test_invalid_member():
    with pytest.raises(Exception, match="`tagged_union` members must all be subclasses of `BaseModel`"):
        class Foo(BaseModel):
            x: Union[A, str] = Field(tagged_union=True)


class D(BaseModel, list=True):
    x: int
    y: float


class E(BaseModel, list=True):
    x: str


class F(BaseModel, list=True):
    pass


class G(BaseModel):
    z: Union[E, F] = Field(tagged_union=True)


def test_serialize_list():
    assert D(x=42, y=13.37).dict() == [42, 13.37]
    assert E(x="bar").dict() == "bar"
    assert G(z=E(x="foo")).dict() == {"z": {"E": "foo"}}
    assert G(z=F()).dict() == {"z": "F"}


def test_deserialize_list():
    assert D(*[42, 13.37]) == D(x=42, y=13.37)
    assert E(*["bar"]) == E(x="bar")
    assert G(**{"z": {"E": "foo"}}) == G(z=E(x="foo"))
    assert G(**{"z": "F"}) == G(z=F())


def test_position_skipped():
    with pytest.raises(Exception) as exc_info:
        class Foo(BaseModel, list=True):
            x: int = Field(position=2)
            y: float = Field(position=0)
    assert exc_info.value.args[0] == "Invalid position: 2"
