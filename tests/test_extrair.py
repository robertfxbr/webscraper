from dataclasses import replace

from coletor.config import Campo
from coletor.extrair import extrair
from conftest import BASE, ler


def test_extrai_os_itens_validos(config):
    resultado = extrair(ler("pagina1.html"), config, BASE + "pagina1.html")
    assert resultado.total == 3
    assert [r["titulo"] for r in resultado.registros] == ["Luz nas Trevas", "O Porao", "Sem Preco"]


def test_descarta_item_sem_campo_obrigatorio(config):
    resultado = extrair(ler("pagina1.html"), config, BASE + "pagina1.html")
    assert len(resultado.descartados) == 1
    assert "titulo" in resultado.descartados[0]


def test_converte_preco_nos_dois_formatos(config):
    registros = extrair(ler("pagina1.html"), config, BASE).registros
    assert registros[0]["preco"] == 51.77
    assert registros[1]["preco"] == 1234.56


def test_campo_opcional_invalido_vira_nulo_sem_derrubar_o_item(config):
    """O livro sem preco continua na planilha, com a celula vazia."""
    registros = extrair(ler("pagina1.html"), config, BASE).registros
    assert registros[2]["titulo"] == "Sem Preco"
    assert registros[2]["preco"] is None
    assert registros[2]["estoque"] is None


def test_le_atributo_quando_pedido(config):
    registros = extrair(ler("pagina1.html"), config, BASE).registros
    assert registros[0]["estoque"] == 22


def test_resolve_url_relativa_contra_a_pagina(config):
    registros = extrair(ler("pagina1.html"), config, BASE + "pagina1.html").registros
    assert registros[0]["url"] == "https://exemplo.test/livro/luz-nas-trevas_1/index.html"


def test_encontra_a_proxima_pagina(config):
    resultado = extrair(ler("pagina1.html"), config, BASE + "pagina1.html")
    assert resultado.proxima_url == BASE + "pagina2.html"


def test_ultima_pagina_nao_tem_proxima(config):
    resultado = extrair(ler("pagina2.html"), config, BASE + "pagina2.html")
    assert resultado.proxima_url is None


def test_pagina_sem_itens_nao_quebra(config):
    resultado = extrair("<html><body><p>nada aqui</p></body></html>", config, BASE)
    assert resultado.total == 0
    assert resultado.descartados == []


def test_seletor_que_parou_de_casar_produz_descarte_nao_linha_vazia(config):
    """A falha silenciosa que o projeto existe para evitar."""
    html = ler("pagina1.html").replace('class="product_pod"', 'class="produto"')
    quebrado = html.replace("<h3>", "<h4>").replace("</h3>", "</h4>")
    resultado = extrair(quebrado, config, BASE)
    assert resultado.total == 0


def test_seletor_que_nao_casa_deixa_o_campo_nulo(config):
    com_fantasma = replace(
        config,
        campos=(*config.campos, Campo(nome="isbn", seletor="span.isbn", tipo="texto")),
    )
    registros = extrair(ler("pagina1.html"), com_fantasma, BASE).registros
    assert all(r["isbn"] is None for r in registros)


def test_campo_obrigatorio_com_valor_invalido_derruba_o_item(config):
    exigente = replace(
        config,
        campos=tuple(
            replace(c, obrigatorio=True) if c.nome == "estoque" else c for c in config.campos
        ),
    )
    resultado = extrair(ler("pagina1.html"), exigente, BASE)
    # "Out of stock" nao tem inteiro: o item cai em vez de virar linha pela metade
    assert resultado.total == 2
    assert any("estoque" in d for d in resultado.descartados)


def test_atributo_com_varios_valores_vira_texto(config):
    com_classe = replace(
        config,
        campos=(*config.campos, Campo(nome="classes", seletor="p.price_color", atributo="class")),
    )
    registros = extrair(ler("pagina1.html"), com_classe, BASE).registros
    assert registros[0]["classes"] == "price_color"
