import csv

import pytest

from coletor.exportar import chave_de, deduplicar, escrever_csv

REGISTROS = [
    {"titulo": "A", "preco": 10.0},
    {"titulo": "B", "preco": 20.0},
    {"titulo": "A", "preco": 99.0},
]


def test_chave_de_usa_os_campos_pedidos():
    assert chave_de(REGISTROS[0], ["titulo"]) == ("A",)
    assert chave_de(REGISTROS[0], ["titulo", "preco"]) == ("A", 10.0)


def test_chave_ausente_vira_nulo():
    assert chave_de({"titulo": "A"}, ["isbn"]) == (None,)


def test_deduplica_preservando_o_primeiro():
    unicos = deduplicar(REGISTROS, ["titulo"])
    assert [r["preco"] for r in unicos] == [10.0, 20.0]


def test_sem_campos_de_chave_nada_e_removido():
    """Deduplicar pela linha inteira apagaria itens legitimamente iguais."""
    assert len(deduplicar(REGISTROS, [])) == 3


def test_deduplica_por_chave_composta():
    assert len(deduplicar(REGISTROS, ["titulo", "preco"])) == 3


def test_csv_tem_cabecalho_e_linhas(tmp_path):
    destino = escrever_csv(REGISTROS, tmp_path / "saida.csv", ["titulo", "preco"])
    with destino.open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert [linha["titulo"] for linha in linhas] == ["A", "B", "A"]


def test_coluna_declarada_aparece_mesmo_sempre_vazia(tmp_path):
    """Coluna sumida esconde seletor quebrado: o leitor acha que o dado nao existe."""
    destino = escrever_csv(REGISTROS, tmp_path / "s.csv", ["titulo", "preco", "isbn"])
    cabecalho = destino.read_text(encoding="utf-8-sig").splitlines()[0]
    assert cabecalho == "titulo,preco,isbn"


def test_campo_fora_das_colunas_e_ignorado(tmp_path):
    registros = [{"titulo": "A", "extra": "x"}]
    destino = escrever_csv(registros, tmp_path / "s.csv", ["titulo"])
    assert "extra" not in destino.read_text(encoding="utf-8-sig")


def test_cria_o_diretorio_de_destino(tmp_path):
    destino = escrever_csv(REGISTROS, tmp_path / "a" / "b" / "s.csv", ["titulo"])
    assert destino.exists()


def test_valor_com_virgula_e_escapado(tmp_path):
    destino = escrever_csv([{"titulo": "A, com virgula"}], tmp_path / "s.csv", ["titulo"])
    with destino.open(encoding="utf-8-sig", newline="") as arquivo:
        assert list(csv.DictReader(arquivo))[0]["titulo"] == "A, com virgula"


def test_acento_sobrevive_a_ida_e_volta(tmp_path):
    destino = escrever_csv([{"titulo": "Coracao e acao"}], tmp_path / "s.csv", ["titulo"])
    with destino.open(encoding="utf-8-sig", newline="") as arquivo:
        assert list(csv.DictReader(arquivo))[0]["titulo"] == "Coracao e acao"


def test_xlsx_preserva_numero_como_numero(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from coletor.exportar import escrever_xlsx

    destino = escrever_xlsx(REGISTROS, tmp_path / "s.xlsx", ["titulo", "preco"])
    aba = openpyxl.load_workbook(destino).active
    assert [c.value for c in aba[1]] == ["titulo", "preco"]
    # o Excel guarda 10.0 como 10; o que importa e nao chegar como texto
    assert aba["B2"].value == 10
    assert isinstance(aba["B2"].value, int | float)
    assert aba["B3"].value == 20


def test_xlsx_cria_o_diretorio(tmp_path):
    pytest.importorskip("openpyxl")
    from coletor.exportar import escrever_xlsx

    destino = escrever_xlsx(REGISTROS, tmp_path / "a" / "b" / "s.xlsx", ["titulo"])
    assert destino.exists()
