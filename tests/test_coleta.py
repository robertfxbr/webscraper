from dataclasses import replace

import pytest

from coletor.cache import Cache
from coletor.coleta import carregar_robots, coletar
from coletor.errors import RobotsError
from coletor.http import FetcherFalso
from coletor.robots import parse_robots
from coletor.throttle import Throttle
from conftest import BASE

P1 = BASE + "pagina1.html"
P2 = BASE + "pagina2.html"


def test_segue_a_paginacao_e_junta_os_registros(config, paginas):
    resultado = coletar(config, FetcherFalso(paginas))
    assert resultado.paginas == [P1, P2]
    # 3 + 2 itens, menos "Luz nas Trevas" repetido na pagina 2
    assert resultado.total == 4


def test_deduplica_pela_chave_declarada(config, paginas):
    titulos = [r["titulo"] for r in coletar(config, FetcherFalso(paginas)).registros]
    assert titulos.count("Luz nas Trevas") == 1


def test_sem_chave_nao_deduplica(config, paginas):
    sem_chave = replace(config, chave=())
    assert coletar(sem_chave, FetcherFalso(paginas)).total == 5


def test_respeita_o_limite_de_paginas(config, paginas):
    resultado = coletar(config, FetcherFalso(paginas), max_paginas=1)
    assert resultado.paginas == [P1]
    assert "limite" in resultado.motivo_parada


def test_para_quando_nao_ha_proxima_pagina(config, paginas):
    assert "nao ha proxima pagina" in coletar(config, FetcherFalso(paginas)).motivo_parada


def test_robots_proibindo_a_primeira_pagina_interrompe(config, paginas):
    robots = parse_robots("User-agent: *\nDisallow: /catalogo/", "coletor-teste")
    with pytest.raises(RobotsError, match="proibe"):
        coletar(config, FetcherFalso(paginas), robots=robots)


def test_robots_proibindo_a_segunda_pagina_encerra_sem_perder_a_primeira(config, paginas):
    robots = parse_robots("User-agent: *\nDisallow: /catalogo/pagina2.html", "coletor-teste")
    resultado = coletar(config, FetcherFalso(paginas), robots=robots)
    assert resultado.paginas == [P1]
    assert "robots.txt proibe" in resultado.motivo_parada
    assert resultado.total == 3


def test_crawl_delay_do_site_vence_o_intervalo_configurado(config, paginas):
    robots = parse_robots("User-agent: *\nCrawl-delay: 5", "coletor-teste")
    dormidas = []
    coletar(config, FetcherFalso(paginas), robots=robots, dormir=dormidas.append)
    # a primeira pagina nao espera; a segunda sim
    assert dormidas == [pytest.approx(5.0, abs=0.1)]


def test_intervalo_configurado_vale_quando_o_site_nao_declara(config, paginas):
    rapido = replace(config, intervalo=0.25)
    dormidas = []
    coletar(rapido, FetcherFalso(paginas), dormir=dormidas.append)
    assert dormidas == [pytest.approx(0.25, abs=0.05)]


def test_pagina_em_cache_nao_vai_a_rede(config, paginas, tmp_path):
    cache = Cache(tmp_path)
    fetcher = FetcherFalso(paginas)
    coletar(config, fetcher, cache=cache)
    pedidas_antes = len(fetcher.pedidas)

    segundo = FetcherFalso(paginas)
    resultado = coletar(config, segundo, cache=cache)
    assert pedidas_antes == 2
    assert segundo.pedidas == []
    assert resultado.total == 4


def test_falha_de_rede_encerra_com_o_que_ja_foi_coletado(config, paginas):
    fetcher = FetcherFalso({P1: paginas[P1]})  # a pagina 2 devolve 404
    resultado = coletar(config, fetcher)
    assert resultado.paginas == [P1]
    assert resultado.total == 3
    assert "404" in resultado.motivo_parada


def test_paginacao_circular_nao_vira_laco_infinito(config, paginas):
    circular = dict(paginas)
    circular[P2] = paginas[P1]  # a pagina 2 aponta de volta para a 2
    resultado = coletar(replace(config, max_paginas=50), FetcherFalso(circular))
    assert "ja visitada" in resultado.motivo_parada


def test_itens_descartados_sao_reportados(config, paginas):
    assert len(coletar(config, FetcherFalso(paginas)).descartados) == 1


def test_throttle_injetado_e_respeitado(config, paginas):
    dormidas = []
    throttle = Throttle(3.0, agora=lambda: 0.0, dormir=dormidas.append)
    coletar(config, FetcherFalso(paginas), throttle=throttle)
    assert dormidas == [pytest.approx(3.0)]


def test_carregar_robots_le_o_arquivo_do_site():
    fetcher = FetcherFalso({"https://x.test/robots.txt": "User-agent: *\nCrawl-delay: 4"})
    assert carregar_robots(fetcher, "https://x.test/a/b", "coletor").crawl_delay == 4.0


def test_site_sem_robots_nao_restringe():
    """Ausencia de robots.txt libera: e a leitura correta da especificacao."""
    robots = carregar_robots(FetcherFalso({}), "https://x.test/a", "coletor")
    assert robots.permite("https://x.test/qualquer")


def test_falha_ao_buscar_robots_nao_derruba_a_coleta():
    class FetcherQuebrado:
        def buscar(self, url):
            raise OSError("rede caiu")

    linhas = []
    robots = carregar_robots(FetcherQuebrado(), "https://x.test/a", "coletor", log=linhas.append)
    assert robots.permite("https://x.test/qualquer")
    assert "nao foi possivel" in linhas[0]
