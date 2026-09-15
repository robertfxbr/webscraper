import pytest

from coletor.cache import Cache, CacheNulo
from coletor.throttle import Throttle


class Relogio:
    """Relogio controlado pelo teste, para nao depender do tempo real."""

    def __init__(self) -> None:
        self.agora = 0.0
        self.dormidas: list[float] = []

    def ler(self) -> float:
        return self.agora

    def dormir(self, segundos: float) -> None:
        self.dormidas.append(segundos)
        self.agora += segundos


def test_primeira_chamada_nao_espera():
    relogio = Relogio()
    throttle = Throttle(2.0, agora=relogio.ler, dormir=relogio.dormir)
    assert throttle.esperar() == 0.0
    assert relogio.dormidas == []


def test_segunda_chamada_imediata_espera_o_intervalo_inteiro():
    relogio = Relogio()
    throttle = Throttle(2.0, agora=relogio.ler, dormir=relogio.dormir)
    throttle.esperar()
    assert throttle.esperar() == 2.0


def test_espera_so_o_que_falta():
    relogio = Relogio()
    throttle = Throttle(2.0, agora=relogio.ler, dormir=relogio.dormir)
    throttle.esperar()
    relogio.agora += 1.5
    assert throttle.esperar() == pytest.approx(0.5)


def test_nao_espera_se_ja_passou_do_intervalo():
    relogio = Relogio()
    throttle = Throttle(2.0, agora=relogio.ler, dormir=relogio.dormir)
    throttle.esperar()
    relogio.agora += 10
    assert throttle.esperar() == 0.0


def test_intervalo_zero_nunca_espera():
    relogio = Relogio()
    throttle = Throttle(0, agora=relogio.ler, dormir=relogio.dormir)
    throttle.esperar()
    assert throttle.esperar() == 0.0


def test_intervalo_negativo_e_recusado():
    with pytest.raises(ValueError):
        Throttle(-1)


def test_cache_guarda_e_devolve(tmp_path):
    cache = Cache(tmp_path)
    assert cache.get("https://x.test/a") is None
    cache.set("https://x.test/a", "<html>oi</html>")
    assert cache.get("https://x.test/a") == "<html>oi</html>"


def test_cache_separa_urls_diferentes(tmp_path):
    cache = Cache(tmp_path)
    cache.set("https://x.test/a", "A")
    cache.set("https://x.test/b", "B")
    assert cache.get("https://x.test/a") == "A"
    assert cache.get("https://x.test/b") == "B"


def test_cache_cria_o_diretorio(tmp_path):
    cache = Cache(tmp_path / "novo" / "fundo")
    cache.set("https://x.test/a", "A")
    assert cache.get("https://x.test/a") == "A"


def test_cache_aceita_acento(tmp_path):
    cache = Cache(tmp_path)
    cache.set("https://x.test/coracao", "<p>coracao</p>")
    assert cache.get("https://x.test/coracao") == "<p>coracao</p>"


def test_cache_nulo_nunca_guarda():
    cache = CacheNulo()
    cache.set("https://x.test/a", "A")
    assert cache.get("https://x.test/a") is None
