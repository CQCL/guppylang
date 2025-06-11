from dataclasses import dataclass

from hugr import tys as ht

from guppylang.tys.arg import ConstArg
from guppylang.tys.builtin import is_string_type, string_type
from guppylang.tys.const import ConstValue


class ConstStringArg(ConstArg):

    def to_hugr(self) -> ht.TypeArg:
        match self.const:
            case ConstValue(value=v, ty=ty) if is_string_type(ty):
                assert isinstance(v, str)
                return ht.StringArg(v)
            case _:
                return super().to_hugr()

def const_string_arg(s: str) -> ConstStringArg:
    return ConstStringArg(ConstValue(string_type(), s))
