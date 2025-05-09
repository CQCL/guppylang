from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.wasm import new_wasm

def test_wasm(validate):
    @guppy.wasm_module("../wasm_decoder.wasm", 42)
    class MyWasm:

        @guppy.wasm
        def add_one(self, x: int) -> int: ...

        @guppy.wasm
        def add_two(self, x: int) -> int: ...

        #@guppy.wasm
        #def add_syndrome(self, syndrome: array[bool, 3]) -> None: ...
        #
        #@guppy.wasm
        #def decode(self) -> int: ...
        #
        #@guppy
        #def other_method(self) -> int:
        #    # Could even allow to define regular Guppy methods??
        #    self.add_one(1)
        #    self.add_one(10)
        #    return self.decode()

    @guppy
    def main() -> int:
        decoder1 = MyWasm().unwrap()
        #decoder2 = MyWasm()
        #two = decoder1.add_one(1)
        #four = decoder2.add_two(2)
        #return two + four
        decoder1.discard()
        return 42

    mod = guppy.compile_module()
    validate(mod)
