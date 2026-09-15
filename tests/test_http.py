import pytest

from coletor.errors import FetchError
from coletor.http import FetcherFalso, Resposta, buscar_com_retry, espera_sugerida


def test_resposta_ok():
    assert Resposta(200, "x").ok
    assert not Resposta(404, "").ok


def test_devolve_no_primeiro_sucesso():
    fetcher = FetcherFalso({"u": "corpo"})
    assert buscar_com_retry(fetcher, "u").corpo == "corpo"
    assert fetcher.pedidas == ["u"]


def test_repete_em_503_ate_dar_certo():
    fetcher = FetcherFalso({"u": "corpo"})
    fetcher.falhas_restantes["u"] = 2
    dormidas = []
    resposta = buscar_com_retry(fetcher, "u", tentativas=3, base=1.0, dormir=dormidas.append)
    assert resposta.corpo == "corpo"
    assert dormidas == [1.0, 2.0]


def test_desiste_depois_do_limite():
    fetcher = FetcherFalso({"u": "corpo"})
    fetcher.falhas_restantes["u"] = 99
    with pytest.raises(FetchError, match="503"):
        buscar_com_retry(fetcher, "u", tentativas=2, dormir=lambda _: None)
    assert len(fetcher.pedidas) == 2


def test_nao_repete_em_404():
    """Insistir num 404 gasta o limite de taxa que outra pagina poderia usar."""
    fetcher = FetcherFalso({})
    with pytest.raises(FetchError, match="404"):
        buscar_com_retry(fetcher, "sumida", tentativas=5, dormir=lambda _: None)
    assert fetcher.pedidas == ["sumida"]


def test_retry_after_do_servidor_vence_o_backoff():
    fetcher = FetcherFalso({"u": "corpo"}, cabecalhos={"u": {"Retry-After": "7"}})
    fetcher.falhas_restantes["u"] = 1
    dormidas = []
    buscar_com_retry(fetcher, "u", tentativas=2, base=1.0, dormir=dormidas.append)
    assert dormidas == [7.0]


def test_retry_after_invalido_cai_no_backoff():
    resposta = Resposta(429, "", {"Retry-After": "amanha"})
    assert espera_sugerida(resposta, 1, base=2.0) == 4.0


def test_retry_after_em_minusculo_tambem_vale():
    resposta = Resposta(429, "", {"retry-after": "3"})
    assert espera_sugerida(resposta, 0, base=1.0) == 3.0


def test_tentativas_invalidas():
    with pytest.raises(ValueError):
        buscar_com_retry(FetcherFalso(), "u", tentativas=0)


def test_log_registra_a_espera():
    fetcher = FetcherFalso({"u": "corpo"})
    fetcher.falhas_restantes["u"] = 1
    linhas = []
    buscar_com_retry(fetcher, "u", tentativas=2, dormir=lambda _: None, log=linhas.append)
    assert "503" in linhas[0]


def test_requests_fetcher_declara_o_user_agent():
    """O unico teste do driver real: conferir que ele se identifica."""
    pytest.importorskip("requests")
    from coletor.http import RequestsFetcher

    fetcher = RequestsFetcher(user_agent="coletor-teste/9.9")
    assert fetcher._sessao.headers["User-Agent"] == "coletor-teste/9.9"
