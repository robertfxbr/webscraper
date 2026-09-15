import pytest

from coletor.robots import parse_robots

SIMPLES = """
User-agent: *
Disallow: /privado/
Crawl-delay: 2
"""

COM_GRUPOS = """
User-agent: *
Disallow: /

User-agent: coletor
Disallow: /admin/
Allow: /admin/publico/
"""


def test_sem_regra_libera():
    robots = parse_robots("", "coletor")
    assert robots.permite("https://x.test/qualquer")


def test_disallow_bloqueia_o_prefixo():
    robots = parse_robots(SIMPLES, "coletor")
    assert not robots.permite("https://x.test/privado/a")
    assert robots.permite("https://x.test/publico/a")


def test_crawl_delay_e_lido():
    assert parse_robots(SIMPLES, "coletor").crawl_delay == 2.0


def test_crawl_delay_invalido_e_ignorado():
    assert parse_robots("User-agent: *\nCrawl-delay: depois", "coletor").crawl_delay is None


def test_grupo_do_agente_vence_o_curinga():
    robots = parse_robots(COM_GRUPOS, "coletor/0.1")
    assert robots.permite("https://x.test/qualquer")
    assert not robots.permite("https://x.test/admin/painel")


def test_allow_mais_especifico_vence_o_disallow():
    robots = parse_robots(COM_GRUPOS, "coletor/0.1")
    assert robots.permite("https://x.test/admin/publico/x")


def test_outro_agente_cai_no_curinga():
    robots = parse_robots(COM_GRUPOS, "outroBot")
    assert not robots.permite("https://x.test/qualquer")


def test_disallow_vazio_libera_tudo():
    robots = parse_robots("User-agent: *\nDisallow:", "coletor")
    assert robots.permite("https://x.test/qualquer")


def test_comentario_e_ignorado():
    robots = parse_robots("User-agent: *  # todos\nDisallow: /x/  # nao entre", "coletor")
    assert not robots.permite("https://x.test/x/a")


@pytest.mark.parametrize(
    "padrao, caminho, bloqueia",
    [
        ("/*.pdf$", "/docs/manual.pdf", True),
        ("/*.pdf$", "/docs/manual.pdf?v=2", False),
        ("/a/*/b", "/a/qualquer/b", True),
        ("/a/*/b", "/a/b", False),
        ("/exato$", "/exato", True),
        ("/exato$", "/exato/mais", False),
    ],
)
def test_curingas_e_ancora(padrao, caminho, bloqueia):
    robots = parse_robots(f"User-agent: *\nDisallow: {padrao}", "coletor")
    assert robots.permite("https://x.test" + caminho) is not bloqueia


def test_query_string_entra_no_casamento():
    robots = parse_robots("User-agent: *\nDisallow: /busca?", "coletor")
    assert not robots.permite("https://x.test/busca?q=1")


def test_dois_agentes_no_mesmo_grupo():
    texto = "User-agent: a\nUser-agent: b\nDisallow: /x/"
    assert not parse_robots(texto, "a").permite("https://t.test/x/1")
    assert not parse_robots(texto, "b").permite("https://t.test/x/1")


def test_grupo_novo_comeca_depois_das_regras():
    texto = "User-agent: a\nDisallow: /x/\nUser-agent: b\nDisallow: /y/"
    a = parse_robots(texto, "a")
    b = parse_robots(texto, "b")
    assert not a.permite("https://t.test/x/1")
    assert a.permite("https://t.test/y/1")
    assert not b.permite("https://t.test/y/1")


def test_linha_sem_dois_pontos_e_ignorada():
    robots = parse_robots("lixo\nUser-agent: *\nDisallow: /x/", "coletor")
    assert not robots.permite("https://t.test/x/1")


def test_caminho_percent_encoded():
    robots = parse_robots("User-agent: *\nDisallow: /privado/", "coletor")
    assert not robots.permite("https://t.test/privado/a%20b")


def test_regra_antes_de_qualquer_user_agent_e_ignorada():
    robots = parse_robots("Disallow: /x/\nUser-agent: *\nAllow: /", "coletor")
    assert robots.permite("https://t.test/x/1")


def test_padrao_vazio_nunca_casa():
    from coletor.robots import Regra, Robots

    robots = Robots(regras=[Regra(permite=False, padrao="")])
    assert robots.permite("https://t.test/qualquer")
