# import pytest
#
# from guppylang.error import UndefinedPort, InternalGuppyError
# from guppylang.gtypes import BoolType
#
#
# def test_undefined_port():
#     ty = BoolType()
#     p = UndefinedPort(ty)
#     assert p.ty == ty
#     with pytest.raises(InternalGuppyError, match="Tried to access undefined Port"):
#         p.node
#     with pytest.raises(InternalGuppyError, match="Tried to access undefined Port"):
#         p.offset
