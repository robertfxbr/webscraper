"""Limite de taxa entre requisicoes.

O relogio e o sono sao injetados para que o teste afirme sobre o intervalo sem
dormir de verdade. Sem isso, testar ritmo de coleta significaria uma suite que
leva minutos - e uma suite lenta deixa de ser rodada.
"""

from __future__ import annotations

import time
from collections.abc import Callable


class Throttle:
    """Garante um intervalo minimo entre chamadas sucessivas."""

    def __init__(
        self,
        intervalo: float,
        *,
        agora: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        if intervalo < 0:
            raise ValueError("intervalo deve ser >= 0")
        self.intervalo = intervalo
        self._agora = agora
        self._dormir = dormir
        self._ultima: float | None = None

    def esperar(self) -> float:
        """Dorme o que falta para completar o intervalo. Devolve o tempo dormido."""
        instante = self._agora()
        if self._ultima is None or self.intervalo == 0:
            self._ultima = instante
            return 0.0

        falta = self.intervalo - (instante - self._ultima)
        if falta > 0:
            self._dormir(falta)
            self._ultima = instante + falta
            return falta

        self._ultima = instante
        return 0.0
