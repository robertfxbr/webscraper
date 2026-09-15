import pytest

from coletor.config import load_config, parse_config
from coletor.errors import ConfigError

MINIMA = {
    "nome": "t",
    "url_inicial": "https://x.test/",
    "item": "article",
    "campos": [{"nome": "titulo", "seletor": "h3"}],
}


def test_config_minima():
    config = parse_config(MINIMA)
    assert config.max_paginas == 1
    assert config.intervalo == 1.0
    assert config.campos[0].tipo == "texto"
    assert config.nomes == ["titulo"]


def test_topo_precisa_ser_mapeamento():
    with pytest.raises(ConfigError, match="mapeamento"):
        parse_config([1, 2])


@pytest.mark.parametrize("faltando", ["nome", "url_inicial", "item"])
def test_campos_obrigatorios_do_topo(faltando):
    bruto = {k: v for k, v in MINIMA.items() if k != faltando}
    with pytest.raises(ConfigError, match=faltando):
        parse_config(bruto)


def test_chave_desconhecida_no_topo():
    with pytest.raises(ConfigError, match="desconhecidas"):
        parse_config({**MINIMA, "intervlo": 2})


def test_campos_vazio():
    with pytest.raises(ConfigError, match="pelo menos um campo"):
        parse_config({**MINIMA, "campos": []})


def test_campo_precisa_de_seletor():
    with pytest.raises(ConfigError, match=r"campos\[0\].*seletor"):
        parse_config({**MINIMA, "campos": [{"nome": "t"}]})


def test_campo_precisa_de_nome():
    with pytest.raises(ConfigError, match=r"campos\[0\].*nome"):
        parse_config({**MINIMA, "campos": [{"seletor": "h3"}]})


def test_campo_que_nao_e_mapeamento():
    with pytest.raises(ConfigError, match="mapeamento"):
        parse_config({**MINIMA, "campos": ["h3"]})


def test_chave_desconhecida_no_campo():
    campos = [{"nome": "t", "seletor": "h3", "atributos": "href"}]
    with pytest.raises(ConfigError, match="desconhecidas"):
        parse_config({**MINIMA, "campos": campos})


def test_tipo_desconhecido():
    campos = [{"nome": "t", "seletor": "h3", "tipo": "booleano"}]
    with pytest.raises(ConfigError, match="desconhecido"):
        parse_config({**MINIMA, "campos": campos})


def test_obrigatorio_precisa_ser_booleano():
    campos = [{"nome": "t", "seletor": "h3", "obrigatorio": "sim"}]
    with pytest.raises(ConfigError, match="true ou false"):
        parse_config({**MINIMA, "campos": campos})


def test_atributo_precisa_ser_texto():
    campos = [{"nome": "t", "seletor": "h3", "atributo": 7}]
    with pytest.raises(ConfigError, match="atributo"):
        parse_config({**MINIMA, "campos": campos})


def test_nomes_de_campo_repetidos():
    campos = [{"nome": "t", "seletor": "h3"}, {"nome": "t", "seletor": "p"}]
    with pytest.raises(ConfigError, match="repetidos"):
        parse_config({**MINIMA, "campos": campos})


@pytest.mark.parametrize("intervalo", [-1, "1", True])
def test_intervalo_invalido(intervalo):
    with pytest.raises(ConfigError, match="intervalo"):
        parse_config({**MINIMA, "intervalo": intervalo})


@pytest.mark.parametrize("paginas", [0, 1.5, "3"])
def test_max_paginas_invalido(paginas):
    with pytest.raises(ConfigError, match="max_paginas"):
        parse_config({**MINIMA, "max_paginas": paginas})


def test_varias_paginas_exigem_seletor_de_paginacao():
    with pytest.raises(ConfigError, match="proxima_pagina"):
        parse_config({**MINIMA, "max_paginas": 3})


def test_proxima_pagina_precisa_ser_texto():
    with pytest.raises(ConfigError, match="proxima_pagina"):
        parse_config({**MINIMA, "proxima_pagina": 7})


def test_chave_como_texto_vira_lista():
    config = parse_config({**MINIMA, "chave": "titulo"})
    assert config.chave == ("titulo",)


def test_chave_precisa_citar_campo_existente():
    with pytest.raises(ConfigError, match="inexistentes"):
        parse_config({**MINIMA, "chave": ["preco"]})


def test_chave_invalida():
    with pytest.raises(ConfigError, match="chave"):
        parse_config({**MINIMA, "chave": {"titulo": True}})


def test_user_agent_precisa_ser_texto():
    with pytest.raises(ConfigError, match="user_agent"):
        parse_config({**MINIMA, "user_agent": ""})


def test_load_config_le_o_exemplo_do_repositorio():
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1]
    config = load_config(raiz / "configs" / "livros.yaml")
    assert config.nome == "livros"
    assert "titulo" in config.nomes


def test_load_config_arquivo_inexistente():
    with pytest.raises(ConfigError, match="nao foi possivel ler"):
        load_config("nao/existe.yaml")


def test_load_config_yaml_quebrado(tmp_path):
    ruim = tmp_path / "ruim.yaml"
    ruim.write_text("nome: t\ncampos: [\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="YAML invalido"):
        load_config(ruim)
