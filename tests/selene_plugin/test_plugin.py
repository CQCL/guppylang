from guppylang.selene_plugin import register_guppylang_with_selene
from pathlib import Path
from selene_sim import build, Coinflip

register_guppylang_with_selene()


def test_plugin():
    subject = Path(__file__).parent / "prog.gpy.py"
    build(subject).run(n_qubits=3, simulator=Coinflip())
