import pytest

from coletor.errors import ExtracaoError
from coletor.tipos import converter, inteiro, numero, texto, url


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        ("  a   b  ", "a b"),
        ("a\n\tb", "a b"),
        ("a\xa0b", "a b"),
        ("", ""),
    ],
)
def test_texto_colapsa_espacos(bruto, esperado):
    assert texto(bruto) == esperado


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        ("51.77", 51.77),
        ("R$ 1.234,56", 1234.56),
        ("$1,234.56", 1234.56),
        ("1234", 1234.0),
        ("1.234", 1234.0),  # separador de milhar, tres digitos depois
        ("1,23", 1.23),  # decimal brasileiro
        ("-9,50", -9.5),
        ("  10,5  ", 10.5),
        ("12.345.678,90", 12345678.9),
    ],
)
def test_numero_le_os_dois_formatos(bruto, esperado):
    assert numero(bruto) == pytest.approx(esperado)


@pytest.mark.parametrize("bruto", ["", "indisponivel", "-", ",", "R$"])
def test_numero_recusa_o_que_nao_e_numero(bruto):
    with pytest.raises(ExtracaoError):
        numero(bruto)


def test_inteiro_pega_o_primeiro_numero_da_frase():
    assert inteiro("In stock (22 available)") == 22


def test_inteiro_recusa_texto_sem_digito():
    with pytest.raises(ExtracaoError):
        inteiro("Out of stock")


def test_url_resolve_link_relativo():
    assert url("../a/b.html", "https://x.test/c/d/") == "https://x.test/c/a/b.html"


def test_url_absoluta_passa_intacta():
    assert url("https://outro.test/a", "https://x.test/") == "https://outro.test/a"


def test_converter_encaminha_a_base_so_para_url():
    assert converter("url", "a.html", "https://x.test/") == "https://x.test/a.html"
    assert converter("texto", " a ", "https://x.test/") == "a"


def test_converter_recusa_tipo_desconhecido():
    with pytest.raises(ExtracaoError, match="tipo desconhecido"):
        converter("booleano", "sim")


def test_numero_recusa_separador_sem_digito():
    with pytest.raises(ExtracaoError):
        numero("-.")
