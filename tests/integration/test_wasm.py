from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.wasm import new_wasm

def test_wasm(validate):
    @guppy.wasm_module("../wasm_decoder.wasm", 42)
    class MyWasm:

        @guppy.wasm
        def add_one(self: "MyWasm", x: int) -> int: ...

        @guppy.wasm
        def add_two(self: "MyWasm", x: int) -> int: ...

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
        decoder2 = MyWasm().unwrap()
        two = decoder1.add_one(1)
        four = decoder2.add_two(2)
        decoder1.discard()
        decoder2.discard()
        return two + four

    mod = guppy.compile_module()
    validate(mod)
