"""Conversao dos textos raspados para tipos utilizaveis.

Raspar devolve string sempre. Um preco que chega como "R$ 1.234,56" e texto
ate alguem converter, e planilha cheia de numero salvo como texto e o defeito
mais comum de scraper amador: some a soma, some a ordenacao, some o filtro.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urljoin

from .errors import ExtracaoError

_SO_NUMERO = re.compile(r"[^0-9,.\-]")


def texto(valor: str) -> str:
    """Colapsa espacos, inclusive quebras de linha e espaco duro."""
    return re.sub(r"\s+", " ", valor.replace("\xa0", " ")).strip()


def numero(valor: str) -> float:
    """Le um numero decimal escrito no formato brasileiro ou no americano.

    Decide o separador decimal pela posicao, nao por configuracao regional:
    o ultimo separador presente e o decimal, desde que sobrem no maximo dois
    digitos depois dele. Assim "1.234,56" e "1,234.56" chegam ao mesmo valor.
    """
    limpo = _SO_NUMERO.sub("", texto(valor))
    if not limpo or limpo in {"-", ".", ","}:
        raise ExtracaoError(f"nao e um numero: {valor!r}")

    corte = max(limpo.rfind(","), limpo.rfind("."))
    if corte == -1 or len(limpo) - corte - 1 > 2:
        inteiro, decimal = limpo, ""
    else:
        inteiro, decimal = limpo[:corte], limpo[corte + 1 :]

    negativo = inteiro.startswith("-")
    inteiro = inteiro.replace(".", "").replace(",", "").lstrip("-")
    if not inteiro and not decimal:
        raise ExtracaoError(f"nao e um numero: {valor!r}")

    resultado = float(f"{inteiro or 0}.{decimal or 0}")
    return -resultado if negativo else resultado


def inteiro(valor: str) -> int:
    """Primeiro inteiro do texto, util para "In stock (22 available)"."""
    achado = re.search(r"-?\d+", valor.replace(".", "").replace(",", ""))
    if not achado:
        raise ExtracaoError(f"nao contem inteiro: {valor!r}")
    return int(achado.group())


def url(valor: str, base: str = "") -> str:
    """Resolve link relativo contra a pagina de origem."""
    return urljoin(base, texto(valor))


CONVERSORES: dict[str, Callable[..., object]] = {
    "texto": texto,
    "numero": numero,
    "dinheiro": numero,
    "inteiro": inteiro,
    "url": url,
}


def converter(tipo: str, valor: str, base: str = "") -> object:
    """Aplica o conversor de `tipo` sobre `valor`."""
    if tipo not in CONVERSORES:
        raise ExtracaoError(f"tipo desconhecido: {tipo}")
    if tipo == "url":
        return url(valor, base)
    return CONVERSORES[tipo](valor)
