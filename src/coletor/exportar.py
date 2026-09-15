"""Escrita do resultado em planilha.

CSV e o formato padrao porque abre no Excel, no Google Sheets e em qualquer
coisa que leia texto, sem dependencia extra. XLSX fica como opcional, para
quando o destinatario precisa de tipos preservados na propria planilha.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from pathlib import Path

Registro = dict[str, object]


def chave_de(registro: Registro, campos: Sequence[str]) -> tuple:
    """Identidade de um registro, para deduplicacao."""
    return tuple(registro.get(campo) for campo in campos)


def deduplicar(registros: Iterable[Registro], campos: Sequence[str]) -> list[Registro]:
    """Remove repetidos preservando a ordem de chegada.

    Sem `campos`, nada e removido: deduplicar por linha inteira parece
    inofensivo, mas apagaria itens legitimamente iguais em todas as colunas
    coletadas, que e um caso real quando se raspa poucas colunas.
    """
    if not campos:
        return list(registros)

    vistos: set[tuple] = set()
    unicos: list[Registro] = []
    for registro in registros:
        chave = chave_de(registro, campos)
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(registro)
    return unicos


def escrever_csv(
    registros: Sequence[Registro],
    caminho: str | Path,
    colunas: Sequence[str],
) -> Path:
    """Escreve o CSV com todas as colunas declaradas, mesmo as sempre vazias.

    Coluna declarada que nao aparece no arquivo esconde erro de seletor: o
    destinatario acha que o site nao tinha o dado, quando na verdade o seletor
    parou de casar.
    """
    caminho = Path(caminho)
    if caminho.parent != Path(""):
        caminho.parent.mkdir(parents=True, exist_ok=True)

    with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(colunas), extrasaction="ignore")
        escritor.writeheader()
        for registro in registros:
            escritor.writerow({coluna: registro.get(coluna) for coluna in colunas})
    return caminho


def escrever_xlsx(
    registros: Sequence[Registro],
    caminho: str | Path,
    colunas: Sequence[str],
) -> Path:
    """Escreve XLSX preservando numero como numero."""
    try:
        from openpyxl import Workbook
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise RuntimeError("openpyxl nao instalado. Use: pip install -e '.[xlsx]'") from exc

    caminho = Path(caminho)
    if caminho.parent != Path(""):
        caminho.parent.mkdir(parents=True, exist_ok=True)

    livro = Workbook()
    aba = livro.active
    aba.append(list(colunas))
    for registro in registros:
        aba.append([registro.get(coluna) for coluna in colunas])
    livro.save(caminho)
    return caminho
