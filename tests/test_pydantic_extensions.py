import pytest
from typing import Union
from pydantic import ValidationError

from guppy.hugr.pydantic_extensions import BaseModel


class A(BaseModel, tagged=True):
    x: int
    y: bool


class A2(BaseModel, tagged=True):
    x: int
    y: bool


class B(BaseModel, tagged=True, tag="BB"):
    z: str


class C(BaseModel):
    union: Union[A, B]


class D(BaseModel):
    union: Union[A, A2]


class E(BaseModel):
    l: list[Union[A, A2]]


class F(BaseModel):
    t: tuple[Union[A, A2], Union[A, A2], int, Union[A, B]]


def test_serialize_tagged_union():
    c1 = C(union=A(x=42, y=True))
    c2 = C(union=B(z="foo"))
    d1 = D(union=A(x=44, y=True))
    d2 = D(union=A2(x=1337, y=False))
    e = E(l=[A(x=44, y=True), A2(x=1337, y=False)])
    assert c1.dict() == {"union": {"A": {"x": 42, "y": True}}}
    assert c2.dict() == {"union": {"BB": {"z": "foo"}}}
    assert d1.dict() == {"union": {"A": {"x": 44, "y": True}}}
    assert d2.dict() == {"union": {"A2": {"x": 1337, "y": False}}}
    assert e.dict() == {"l": [{"A": {"x": 44, "y": True}}, {"A2": {"x": 1337, "y": False}}]}


def test_roundtrip_tagged_union():
    c1 = C(union=A(x=42, y=True))
    c2 = C(union=B(z="foo"))
    d1 = D(union=A(x=44, y=True))
    d2 = D(union=A2(x=1337, y=False))
    e = E(l=[A(x=44, y=True), A(x=44, y=True)])
    f = F(t=(A(x=42, y=True), A2(x=1337, y=False), 3472, B(z="foo")))
    assert C(**c1.dict()) == c1
    assert C(**c2.dict()) == c2
    assert D(**d1.dict()) == d1
    assert D(**d2.dict()) == d2
    assert E(**e.dict()) == e
    assert F(**f.dict()) == f


def test_not_in_union():
    with pytest.raises(ValidationError, match="`D` is not a valid union member") as exc_info:
        c = {"union": {"D": {"x": 42, "y": True}}}
        C(**c)


def test_not_in_union_empty():
    with pytest.raises(ValidationError, match="`D` is not a valid union member"):
        c = {"union": "D"}
        C(**c)


def test_invalid_member():
    with pytest.raises(Exception, match="If one Union member is tagged, all have to be"):
        class Foo(BaseModel):
            x: Union[A, str]


class G(BaseModel, list=True):
    x: int
    y: float


class H(BaseModel, list=True):
    x: str


class I(BaseModel, list=True, tagged=True):
    x: str


class J(BaseModel, list=True, tagged=True):
    pass


class K(BaseModel):
    z: Union[I, J]


def test_serialize_list():
    assert G(x=42, y=13.37).dict() == [42, 13.37]
    assert H(x="bar").dict() == "bar"
    assert K(z=I(x="foo")).dict() == {"z": {"I": "foo"}}
    assert K(z=J()).dict() == {"z": "J"}


def test_roundtrip_list():
    x1 = G(x=42, y=13.37)
    x2 = H(x="bar")
    x3 = K(z=I(x="foo"))
    x4 = K(z=J())

    assert G(*x1.dict()) == x1
    assert H(x2.dict()) == x2
    assert K(**x3.dict()) == x3
    assert K(**x4.dict()) == x4
