from guppylang.cfg import BBStatement
from guppylang.checker.core import PlaceId

class ProgramDependencies:
    dependencies: dict[BBStatement, set[PlaceId]]