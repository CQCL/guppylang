from hugr.qsystem.result import QsysShot

from .result import EmulatorResult

class EmulatorError(Exception):
    completed_shots: EmulatorResult
    failing_shot: QsysShot
    underlying_exception: Exception | None
    def __init__(
        self,
        completed_shots: EmulatorResult,
        failing_shot: QsysShot,
        underlying_exception: Exception | None = None,
    ):
        super().__init__(str(underlying_exception))
        self.completed_shots = completed_shots
        self.failing_shot = failing_shot
        self.underlying_exception = underlying_exception
