"""Modelo e leitura da configuracao da coleta.

A configuracao e validada inteira antes do primeiro request. Descobrir que o
nome de um campo esta duplicado depois de trezentas paginas baixadas gasta
tempo do servidor do outro lado, nao so o meu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError
from .tipos import CONVERSORES

CHAVES_DO_CAMPO = {"nome", "seletor", "atributo", "tipo", "obrigatorio"}
CHAVES_DA_CONFIG = {
    "nome",
    "url_inicial",
    "user_agent",
    "intervalo",
    "max_paginas",
    "item",
    "proxima_pagina",
    "chave",
    "campos",
}


@dataclass(frozen=True)
class Campo:
    """Um campo a extrair de cada item da pagina."""

    nome: str
    seletor: str
    atributo: str | None = None
    tipo: str = "texto"
    obrigatorio: bool = False


@dataclass(frozen=True)
class Config:
    """A coleta inteira, ja validada."""

    nome: str
    url_inicial: str
    item: str
    campos: tuple[Campo, ...]
    user_agent: str = "coletor/0.1"
    intervalo: float = 1.0
    max_paginas: int = 1
    proxima_pagina: str | None = None
    chave: tuple[str, ...] = field(default_factory=tuple)

    @property
    def nomes(self) -> list[str]:
        return [c.nome for c in self.campos]


def _campo(bruto: Any, indice: int) -> Campo:
    onde = f"campos[{indice}]"
    if not isinstance(bruto, dict):
        raise ConfigError(f"{onde}: cada campo deve ser um mapeamento")

    sobrando = set(bruto) - CHAVES_DO_CAMPO
    if sobrando:
        raise ConfigError(f"{onde}: chaves desconhecidas: " + ", ".join(sorted(sobrando)))

    nome = bruto.get("nome")
    if not isinstance(nome, str) or not nome:
        raise ConfigError(f"{onde}: campo nome obrigatorio")

    seletor = bruto.get("seletor")
    if not isinstance(seletor, str) or not seletor:
        raise ConfigError(f"{onde}: campo seletor obrigatorio")

    tipo = bruto.get("tipo", "texto")
    if tipo not in CONVERSORES:
        raise ConfigError(f"{onde}: tipo {tipo!r} desconhecido; use um de {sorted(CONVERSORES)}")

    obrigatorio = bruto.get("obrigatorio", False)
    if not isinstance(obrigatorio, bool):
        raise ConfigError(f"{onde}: obrigatorio deve ser true ou false")

    atributo = bruto.get("atributo")
    if atributo is not None and not isinstance(atributo, str):
        raise ConfigError(f"{onde}: atributo deve ser texto")

    return Campo(nome, seletor, atributo, tipo, obrigatorio)


def parse_config(bruto: Any) -> Config:
    """Valida um dicionario ja carregado e devolve uma Config."""
    if not isinstance(bruto, dict):
        raise ConfigError("a configuracao deve ser um mapeamento no topo")

    sobrando = set(bruto) - CHAVES_DA_CONFIG
    if sobrando:
        raise ConfigError("chaves desconhecidas: " + ", ".join(sorted(sobrando)))

    for obrigatorio in ("nome", "url_inicial", "item"):
        if not isinstance(bruto.get(obrigatorio), str) or not bruto[obrigatorio]:
            raise ConfigError(f"campo {obrigatorio} obrigatorio")

    brutos = bruto.get("campos")
    if not isinstance(brutos, list) or not brutos:
        raise ConfigError("campos deve ser uma lista com pelo menos um campo")
    campos = tuple(_campo(c, i) for i, c in enumerate(brutos))

    nomes = [c.nome for c in campos]
    repetidos = sorted({n for n in nomes if nomes.count(n) > 1})
    if repetidos:
        raise ConfigError("nomes de campo repetidos: " + ", ".join(repetidos))

    intervalo = bruto.get("intervalo", 1.0)
    if not isinstance(intervalo, int | float) or isinstance(intervalo, bool) or intervalo < 0:
        raise ConfigError("intervalo deve ser um numero >= 0")

    max_paginas = bruto.get("max_paginas", 1)
    if not isinstance(max_paginas, int) or isinstance(max_paginas, bool) or max_paginas < 1:
        raise ConfigError("max_paginas deve ser um inteiro >= 1")

    chave = bruto.get("chave", [])
    if isinstance(chave, str):
        chave = [chave]
    if not isinstance(chave, list) or any(not isinstance(c, str) for c in chave):
        raise ConfigError("chave deve ser um campo ou uma lista de campos")
    inexistentes = [c for c in chave if c not in nomes]
    if inexistentes:
        raise ConfigError("chave cita campos inexistentes: " + ", ".join(inexistentes))

    proxima = bruto.get("proxima_pagina")
    if proxima is not None and not isinstance(proxima, str):
        raise ConfigError("proxima_pagina deve ser um seletor de texto")
    if max_paginas > 1 and not proxima:
        raise ConfigError("max_paginas maior que 1 exige proxima_pagina")

    user_agent = bruto.get("user_agent", "coletor/0.1")
    if not isinstance(user_agent, str) or not user_agent:
        raise ConfigError("user_agent deve ser texto")

    return Config(
        nome=bruto["nome"],
        url_inicial=bruto["url_inicial"],
        item=bruto["item"],
        campos=campos,
        user_agent=user_agent,
        intervalo=float(intervalo),
        max_paginas=int(max_paginas),
        proxima_pagina=proxima,
        chave=tuple(chave),
    )


def load_config(caminho: str | Path) -> Config:
    """Le e valida um arquivo YAML de configuracao."""
    caminho = Path(caminho)
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"nao foi possivel ler {caminho}: {exc}") from exc
    try:
        bruto = yaml.safe_load(conteudo)
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML invalido em {caminho}: {exc}") from exc
    return parse_config(bruto)
