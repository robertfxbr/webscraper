"""Interface de linha de comando."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .cache import Cache, CacheNulo
from .coleta import carregar_robots, coletar
from .config import load_config
from .errors import ColetorError
from .exportar import escrever_csv, escrever_xlsx
from .http import RequestsFetcher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coletor",
        description="Coleta dados de sites respeitando robots.txt e limite de taxa.",
    )
    parser.add_argument("--version", action="version", version=f"coletor {__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_check = sub.add_parser("check", help="apenas valida o arquivo de configuracao")
    p_check.add_argument("config")

    p_run = sub.add_parser("run", help="executa a coleta")
    p_run.add_argument("config")
    p_run.add_argument("--saida", default=None, help="arquivo de saida (.csv ou .xlsx)")
    p_run.add_argument("--max-paginas", type=int, default=None, help="limite desta execucao")
    p_run.add_argument("--cache", default=".cache", help="diretorio de cache (vazio desliga)")
    p_run.add_argument(
        "--ignorar-robots",
        action="store_true",
        help="nao consulta o robots.txt do site; use apenas em site proprio",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = load_config(args.config)
    except ColetorError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    if args.comando == "check":
        print(f"ok: coleta {config.nome!r} com {len(config.campos)} campo(s)")
        print(f"alvo: {config.url_inicial}")
        print(f"intervalo: {config.intervalo:g}s entre requisicoes")
        return 0

    saida = Path(args.saida) if args.saida else Path(f"{config.nome}.csv")
    if saida.suffix.lower() not in (".csv", ".xlsx"):
        print(f"erro: formato de saida nao suportado: {saida.suffix!r}", file=sys.stderr)
        return 2

    try:
        fetcher = RequestsFetcher(user_agent=config.user_agent)
    except RuntimeError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    if args.ignorar_robots:
        print("aviso: robots.txt ignorado por pedido explicito", file=sys.stderr)
        robots = None
    else:
        robots = carregar_robots(fetcher, config.url_inicial, config.user_agent, log=print)

    cache = Cache(args.cache) if args.cache else CacheNulo()

    try:
        resultado = coletar(
            config,
            fetcher,
            robots=robots,
            cache=cache,
            max_paginas=args.max_paginas,
            log=print,
            dormir=time.sleep,
        )
    except ColetorError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1

    if saida.suffix.lower() == ".xlsx":
        escrever_xlsx(resultado.registros, saida, config.nomes)
    else:
        escrever_csv(resultado.registros, saida, config.nomes)

    print(f"{resultado.total} registro(s) em {len(resultado.paginas)} pagina(s) -> {saida}")
    print(f"parou porque: {resultado.motivo_parada}")
    if resultado.descartados:
        print(f"{len(resultado.descartados)} item(ns) descartado(s):", file=sys.stderr)
        for motivo in resultado.descartados[:10]:
            print(f"  {motivo}", file=sys.stderr)

    return 0 if resultado.total else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
