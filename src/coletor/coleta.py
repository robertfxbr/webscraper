"""Orquestracao da coleta.

A ordem aqui e deliberada: robots.txt primeiro, limite de taxa depois, e so
entao a requisicao. Inverter isso significaria bater na porta antes de ler o
aviso na porta.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin

from .cache import CacheNulo
from .config import Config
from .errors import FetchError, RobotsError
from .exportar import deduplicar
from .extrair import extrair
from .http import Fetcher, buscar_com_retry
from .robots import Robots, parse_robots
from .throttle import Throttle


@dataclass
class Coleta:
    """O resultado da coleta inteira."""

    registros: list[dict[str, object]] = field(default_factory=list)
    paginas: list[str] = field(default_factory=list)
    descartados: list[str] = field(default_factory=list)
    motivo_parada: str = ""

    @property
    def total(self) -> int:
        return len(self.registros)


def carregar_robots(
    fetcher: Fetcher,
    url_inicial: str,
    agente: str,
    *,
    log: Callable[[str], None] = lambda _: None,
) -> Robots:
    """Busca e interpreta o robots.txt do site.

    Site sem robots.txt e site que nao restringiu nada: a ausencia libera, e
    essa e a leitura correta da especificacao. Ja uma falha de rede ao buscar
    o arquivo nao libera nada por si so, mas tambem nao ha o que obedecer, e
    o limite de taxa continua valendo.
    """
    alvo = urljoin(url_inicial, "/robots.txt")
    try:
        resposta = fetcher.buscar(alvo)
    except Exception as exc:  # noqa: BLE001 - rede falha de muitas formas
        log(f"[robots] nao foi possivel ler {alvo}: {exc}")
        return Robots()

    if not resposta.ok:
        log(f"[robots] {alvo} devolveu {resposta.status}; nenhuma restricao declarada")
        return Robots()
    return parse_robots(resposta.corpo, agente)


def coletar(
    config: Config,
    fetcher: Fetcher,
    *,
    robots: Robots | None = None,
    cache=None,
    throttle: Throttle | None = None,
    max_paginas: int | None = None,
    log: Callable[[str], None] = lambda _: None,
    dormir: Callable[[float], None] = lambda _: None,
) -> Coleta:
    """Percorre as paginas a partir de `config.url_inicial` e junta os registros."""
    cache = CacheNulo() if cache is None else cache
    robots = Robots() if robots is None else robots
    limite = config.max_paginas if max_paginas is None else max_paginas

    if robots.crawl_delay and robots.crawl_delay > config.intervalo:
        log(f"[robots] Crawl-delay de {robots.crawl_delay:g}s vence o intervalo configurado")
        intervalo = robots.crawl_delay
    else:
        intervalo = config.intervalo
    throttle = Throttle(intervalo, dormir=dormir) if throttle is None else throttle

    resultado = Coleta()
    visitadas: set[str] = set()
    url: str | None = config.url_inicial

    while url and len(resultado.paginas) < limite:
        if url in visitadas:
            resultado.motivo_parada = "a paginacao voltou para uma pagina ja visitada"
            break
        if not robots.permite(url):
            if not resultado.paginas:
                raise RobotsError(f"o robots.txt do site proibe {url}")
            resultado.motivo_parada = f"robots.txt proibe {url}"
            break

        visitadas.add(url)
        html = cache.get(url)
        if html is None:
            throttle.esperar()
            try:
                resposta = buscar_com_retry(fetcher, url, dormir=dormir, log=log)
            except FetchError as exc:
                resultado.motivo_parada = str(exc)
                break
            html = resposta.corpo
            cache.set(url, html)
        else:
            log(f"[cache] {url}")

        pagina = extrair(html, config, url)
        resultado.registros.extend(pagina.registros)
        resultado.descartados.extend(pagina.descartados)
        resultado.paginas.append(url)
        log(f"[ok] {url}: {pagina.total} item(ns)")

        url = pagina.proxima_url

    if not resultado.motivo_parada:
        if url and len(resultado.paginas) >= limite:
            resultado.motivo_parada = f"limite de {limite} pagina(s) atingido"
        else:
            resultado.motivo_parada = "nao ha proxima pagina"

    antes = len(resultado.registros)
    resultado.registros = deduplicar(resultado.registros, config.chave)
    if config.chave and len(resultado.registros) < antes:
        log(f"[dedup] {antes - len(resultado.registros)} repetido(s) removido(s)")

    return resultado
