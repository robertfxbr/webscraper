"""Leitura de robots.txt.

Python ja traz `urllib.robotparser`, e ele foi descartado por dois motivos
praticos: ignora `Crawl-delay`, que e justamente a informacao que define o
ritmo educado da coleta, e nao expoe qual regra casou, o que torna impossivel
explicar ao usuario por que uma URL foi recusada. Ver "Decisoes rejeitadas"
no README.

O formato nao tem norma oficial. O que esta implementado aqui e o
comportamento aceito na pratica: grupos por User-agent, `Allow` ganha de
`Disallow` quando o padrao casado e mais longo, e `*` casa qualquer trecho.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class Regra:
    permite: bool
    padrao: str

    @property
    def tamanho(self) -> int:
        return len(self.padrao)


@dataclass
class Robots:
    """As regras que valem para um agente especifico."""

    regras: list[Regra] = field(default_factory=list)
    crawl_delay: float | None = None

    def permite(self, url: str) -> bool:
        """Diz se `url` pode ser buscada.

        Sem regra que case, a resposta e sim: e o padrao da especificacao.
        Empate entre `Allow` e `Disallow` de mesmo tamanho resolve a favor do
        `Allow`, tambem por convencao.
        """
        caminho = _caminho(url)
        casadas = [r for r in self.regras if _casa(r.padrao, caminho)]
        if not casadas:
            return True
        melhor = max(casadas, key=lambda r: (r.tamanho, r.permite))
        return melhor.permite


def _caminho(url: str) -> str:
    partes = urlparse(url)
    caminho = unquote(partes.path) or "/"
    return caminho + (f"?{partes.query}" if partes.query else "")


def _casa(padrao: str, caminho: str) -> bool:
    """Casa um padrao de robots.txt, com `*` e `$`, contra um caminho."""
    if padrao == "":
        return False
    fim = padrao.endswith("$")
    corpo = padrao[:-1] if fim else padrao
    pedacos = re.split(r"(\*)", corpo)
    regex = "".join(".*" if pedaco == "*" else re.escape(pedaco) for pedaco in pedacos)
    return re.match(regex + ("$" if fim else ""), caminho) is not None


def parse_robots(texto: str, agente: str) -> Robots:
    """Extrai as regras que valem para `agente`.

    Um grupo nomeando o agente vence o grupo `*`, mesmo que apareca depois.
    """
    grupos: dict[str, Robots] = {}
    atuais: list[str] = []
    esperando_agente = True

    for linha_bruta in texto.splitlines():
        linha = linha_bruta.split("#", 1)[0].strip()
        if not linha or ":" not in linha:
            continue
        campo, _, valor = linha.partition(":")
        campo = campo.strip().lower()
        valor = valor.strip()

        if campo == "user-agent":
            if not esperando_agente:
                atuais = []
                esperando_agente = True
            atuais.append(valor.lower())
            grupos.setdefault(valor.lower(), Robots())
            continue

        if not atuais:
            continue
        esperando_agente = False

        for nome in atuais:
            grupo = grupos[nome]
            if campo in ("allow", "disallow") and valor:
                grupo.regras.append(Regra(permite=campo == "allow", padrao=valor))
            elif campo == "disallow" and not valor:
                # "Disallow:" vazio libera tudo; nao gera regra.
                continue
            elif campo == "crawl-delay":
                try:
                    grupo.crawl_delay = float(valor)
                except ValueError:
                    continue

    agente = agente.lower()
    for nome, grupo in grupos.items():
        if nome != "*" and nome in agente:
            return grupo
    return grupos.get("*", Robots())
