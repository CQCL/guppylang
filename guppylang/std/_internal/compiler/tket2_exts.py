from tket2_exts import (
    futures,
    qsystem,
    qsystem_random,
    qsystem_utils,
    quantum,
    result,
    rotation,
    opaque_bool,
)

BOOL_EXTENSION = opaque_bool()
FUTURES_EXTENSION = futures()
QSYSTEM_EXTENSION = qsystem()
QSYSTEM_RANDOM_EXTENSION = qsystem_random()
QSYSTEM_UTILS_EXTENSION = qsystem_utils()
QUANTUM_EXTENSION = quantum()
RESULT_EXTENSION = result()
ROTATION_EXTENSION = rotation()

TKET2_EXTENSIONS = [
    BOOL_EXTENSION,
    FUTURES_EXTENSION,
    QSYSTEM_EXTENSION,
    QSYSTEM_RANDOM_EXTENSION,
    QSYSTEM_UTILS_EXTENSION,
    QUANTUM_EXTENSION,
    RESULT_EXTENSION,
    ROTATION_EXTENSION,
]
