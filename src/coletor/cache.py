"""Cache das paginas baixadas, em disco.

Existe por uma razao de etiqueta, antes de ser de desempenho: enquanto se
ajusta um seletor, a mesma pagina seria baixada dezenas de vezes. Com cache,
ela e baixada uma vez. O servidor do outro lado nao tem por que pagar pelo meu
ciclo de desenvolvimento.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class Cache:
    """Guarda o corpo de cada URL em um arquivo nomeado pelo hash da URL."""

    def __init__(self, diretorio: str | Path) -> None:
        self.diretorio = Path(diretorio)

    def _caminho(self, url: str) -> Path:
        nome = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        return self.diretorio / f"{nome}.html"

    def get(self, url: str) -> str | None:
        caminho = self._caminho(url)
        if not caminho.exists():
            return None
        return caminho.read_text(encoding="utf-8", errors="replace")

    def set(self, url: str, conteudo: str) -> None:
        self.diretorio.mkdir(parents=True, exist_ok=True)
        self._caminho(url).write_text(conteudo, encoding="utf-8")


class CacheNulo:
    """Cache que nunca guarda nada, para quando a coleta precisa ser fresca."""

    def get(self, url: str) -> str | None:
        return None

    def set(self, url: str, conteudo: str) -> None:
        return None
