"""Extracao dos registros de uma pagina HTML.

Um seletor que deixa de casar e a falha mais comum e mais silenciosa de um
scraper: o programa continua rodando, a planilha continua sendo escrita, e as
colunas vem vazias. Por isso campo marcado como obrigatorio derruba o item, e
o relatorio conta quantos itens cairam e por que.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .config import Campo, Config
from .errors import ExtracaoError
from .tipos import converter, texto


@dataclass
class Extracao:
    """Os registros de uma pagina, mais o que falhou nela."""

    registros: list[dict[str, object]] = field(default_factory=list)
    descartados: list[str] = field(default_factory=list)
    proxima_url: str | None = None

    @property
    def total(self) -> int:
        return len(self.registros)


def _valor_bruto(item, campo: Campo) -> str | None:
    alvo = item.select_one(campo.seletor)
    if alvo is None:
        return None
    if campo.atributo:
        valor = alvo.get(campo.atributo)
        if valor is None:
            return None
        return " ".join(valor) if isinstance(valor, list) else valor
    return alvo.get_text()


def extrair(html: str, config: Config, url_base: str = "") -> Extracao:
    """Extrai todos os itens de uma pagina, conforme a configuracao."""
    sopa = BeautifulSoup(html, "html.parser")
    resultado = Extracao()

    for indice, item in enumerate(sopa.select(config.item)):
        registro: dict[str, object] = {}
        problema: str | None = None

        for campo in config.campos:
            bruto = _valor_bruto(item, campo)
            if bruto is None or not texto(bruto):
                if campo.obrigatorio:
                    problema = f"item {indice}: campo obrigatorio {campo.nome!r} vazio"
                    break
                registro[campo.nome] = None
                continue
            try:
                registro[campo.nome] = converter(campo.tipo, bruto, url_base)
            except ExtracaoError as exc:
                if campo.obrigatorio:
                    problema = f"item {indice}: campo {campo.nome!r} invalido: {exc}"
                    break
                registro[campo.nome] = None

        if problema:
            resultado.descartados.append(problema)
        else:
            resultado.registros.append(registro)

    if config.proxima_pagina:
        link = sopa.select_one(config.proxima_pagina)
        destino = link.get("href") if link else None
        if isinstance(destino, str) and destino:
            resultado.proxima_url = converter("url", destino, url_base)  # type: ignore[assignment]

    return resultado
