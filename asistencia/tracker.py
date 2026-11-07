"""Confirmación temporal de reconocimientos.

Un único fotograma puede producir un falso positivo. Para registrar la
asistencia se exige que el mismo estudiante sea reconocido en N fotogramas
dentro de una ventana de tiempo. Esto hace al sistema estable frente a
reconocimientos esporádicos.
"""

import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class _Streak:
    hits: int
    last_seen: float


class ConfirmationTracker:
    def __init__(self, required_hits: int = 3, window_seconds: float = 4.0, clock=time.monotonic):
        if required_hits < 1:
            raise ValueError("required_hits debe ser >= 1")
        self._required = required_hits
        self._window = window_seconds
        self._clock = clock
        self._streaks: dict = {}
        self._lock = threading.Lock()

    def observe(self, session_id: int, label: int) -> bool:
        """Registra una observación. Devuelve True mientras la racha alcance el
        mínimo requerido; quien llama evita duplicados (restricción única en la BD).
        Así, si un registro falla, el siguiente fotograma lo reintenta."""
        key = (session_id, label)
        now = self._clock()
        with self._lock:
            previous = self._streaks.get(key)
            expired = previous is None or (now - previous.last_seen) > self._window
            hits = 1 if expired else previous.hits + 1
            self._streaks[key] = _Streak(hits=hits, last_seen=now)
            return hits >= self._required

    def progress(self, session_id: int, label: int) -> float:
        """Avance 0-1 de la confirmación (para mostrar en la interfaz)."""
        with self._lock:
            streak = self._streaks.get((session_id, label))
        if streak is None or (self._clock() - streak.last_seen) > self._window:
            return 0.0
        return min(streak.hits / self._required, 1.0)

    def forget_session(self, session_id: int) -> None:
        with self._lock:
            self._streaks = {k: v for k, v in self._streaks.items() if k[0] != session_id}
