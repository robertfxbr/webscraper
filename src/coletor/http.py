"""Camada de rede, atras de um contrato pequeno.

O `requests` fica confinado a `RequestsFetcher`. Todo o resto do projeto fala
com `Fetcher`, o que permite rodar a suite inteira sem rede, contra paginas
guardadas em `tests/fixtures`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .errors import FetchError

RETENTAVEIS = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True)
class Resposta:
    status: int
    corpo: str
    cabecalhos: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


@runtime_checkable
class Fetcher(Protocol):
    def buscar(self, url: str) -> Resposta:
        """Faz uma requisicao GET e devolve a resposta."""


def espera_sugerida(resposta: Resposta, tentativa: int, base: float) -> float:
    """Quanto esperar antes de tentar de novo.

    Um `Retry-After` do servidor vence o calculo local: se o site diz quanto
    tempo quer de folga, insistir antes disso e escolher ser bloqueado.
    """
    cabecalho = resposta.cabecalhos.get("Retry-After") or resposta.cabecalhos.get("retry-after")
    if cabecalho:
        try:
            return max(0.0, float(cabecalho))
        except ValueError:
            pass
    return base * (2**tentativa)


def buscar_com_retry(
    fetcher: Fetcher,
    url: str,
    *,
    tentativas: int = 3,
    base: float = 1.0,
    dormir: Callable[[float], None] = lambda _: None,
    log: Callable[[str], None] = lambda _: None,
) -> Resposta:
    """Busca `url`, repetindo apenas em status que fazem sentido repetir.

    Um 404 nao vira retry: a pagina nao vai aparecer na terceira tentativa, e
    insistir so gasta o limite de taxa que poderia ir para outra pagina.
    """
    if tentativas < 1:
        raise ValueError("tentativas deve ser >= 1")

    ultima: Resposta | None = None
    for tentativa in range(tentativas):
        resposta = fetcher.buscar(url)
        if resposta.ok:
            return resposta
        ultima = resposta
        if resposta.status not in RETENTAVEIS:
            break
        if tentativa < tentativas - 1:
            espera = espera_sugerida(resposta, tentativa, base)
            log(f"[retry {tentativa + 1}] {url} devolveu {resposta.status}, esperando {espera:g}s")
            dormir(espera)

    assert ultima is not None
    raise FetchError(f"{url} devolveu {ultima.status}")


class RequestsFetcher:
    """Implementacao real, sobre `requests`.

    Sem teste automatizado, de proposito: testaria a biblioteca, nao este
    projeto. Toda a decisao de quando repetir e quanto esperar esta em
    `buscar_com_retry`, que e testado contra um fetcher falso.
    """

    def __init__(self, *, user_agent: str, timeout: float = 20.0) -> None:
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise RuntimeError("requests nao instalado. Use: pip install -e '.[rede]'") from exc
        self._sessao = requests.Session()
        self._sessao.headers["User-Agent"] = user_agent
        self._timeout = timeout

    def buscar(self, url: str) -> Resposta:  # pragma: no cover - exige rede
        r = self._sessao.get(url, timeout=self._timeout)
        return Resposta(status=r.status_code, corpo=r.text, cabecalhos=dict(r.headers))


class FetcherFalso:
    """Fetcher em memoria: devolve o que foi registrado para cada URL.

    Usado pela suite inteira e pelo modo offline. Registra a ordem das URLs
    pedidas, que e como se afirma sobre paginacao e sobre cache sem rede.
    """

    def __init__(
        self,
        paginas: dict[str, str] | None = None,
        *,
        status: dict[str, int] | None = None,
        cabecalhos: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self.paginas = paginas or {}
        self.status = status or {}
        self.cabecalhos = cabecalhos or {}
        self.pedidas: list[str] = []
        self.falhas_restantes: dict[str, int] = {}

    def buscar(self, url: str) -> Resposta:
        self.pedidas.append(url)
        restantes = self.falhas_restantes.get(url, 0)
        if restantes > 0:
            self.falhas_restantes[url] = restantes - 1
            return Resposta(503, "", self.cabecalhos.get(url, {}))
        if url not in self.paginas:
            return Resposta(self.status.get(url, 404), "", self.cabecalhos.get(url, {}))
        return Resposta(self.status.get(url, 200), self.paginas[url], self.cabecalhos.get(url, {}))
