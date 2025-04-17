from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.wasm import new_wasm
# all declared wasm signatures are treated as belonging to single wasm module


@guppy.wasm
def add_one(x: int) -> int: ...


@guppy.wasm
def add_syndrome(syndrome: array[bool, 3]) -> None: ...


@guppy.wasm
def decode() -> int: ...


@guppy
def main() -> None:
    wasm1 = new_wasm()
    wasm2 = new_wasm()
    y = wasm1.add_one(42)  # all methods take WASMContext as inout
    wasm2.add_syndrome(array(True, False, False))
    decoded = wasm2.decode()
