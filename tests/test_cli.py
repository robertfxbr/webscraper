import csv
from pathlib import Path

import pytest

from coletor.cli import main
from coletor.http import FetcherFalso
from conftest import FIXTURES

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = str(FIXTURES / "config.yaml")


@pytest.fixture
def sem_rede(monkeypatch, paginas):
    """Troca o fetcher real pelo falso, para o CLI rodar offline."""
    monkeypatch.setattr("coletor.cli.RequestsFetcher", lambda **_: FetcherFalso(paginas))


def test_check_aprova_a_config_de_exemplo(capsys):
    assert main(["check", str(RAIZ / "configs" / "livros.yaml")]) == 0
    saida = capsys.readouterr().out
    assert "ok:" in saida
    assert "books.toscrape.com" in saida


def test_check_recusa_config_invalida(tmp_path, capsys):
    ruim = tmp_path / "c.yaml"
    ruim.write_text("nome: t\n", encoding="utf-8")
    assert main(["check", str(ruim)]) == 2
    assert "erro:" in capsys.readouterr().err


def test_run_grava_o_csv(sem_rede, tmp_path, capsys):
    saida = tmp_path / "livros.csv"
    assert main(["run", CONFIG, "--saida", str(saida), "--cache", ""]) == 0
    with saida.open(encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert len(linhas) == 4
    assert linhas[0]["titulo"] == "Luz nas Trevas"
    assert "4 registro(s)" in capsys.readouterr().out


def test_run_respeita_o_limite_de_paginas(sem_rede, tmp_path):
    saida = tmp_path / "s.csv"
    main(["run", CONFIG, "--saida", str(saida), "--cache", "", "--max-paginas", "1"])
    with saida.open(encoding="utf-8-sig", newline="") as arquivo:
        assert len(list(csv.DictReader(arquivo))) == 3


def test_run_reporta_itens_descartados(sem_rede, tmp_path, capsys):
    main(["run", CONFIG, "--saida", str(tmp_path / "s.csv"), "--cache", ""])
    assert "descartado" in capsys.readouterr().err


def test_formato_de_saida_nao_suportado(sem_rede, tmp_path, capsys):
    assert main(["run", CONFIG, "--saida", str(tmp_path / "s.json")]) == 2
    assert "formato" in capsys.readouterr().err


def test_config_inexistente(capsys):
    assert main(["run", "nao/existe.yaml"]) == 2
    assert "erro:" in capsys.readouterr().err


def test_robots_proibindo_devolve_um(monkeypatch, tmp_path, capsys, paginas):
    bloqueado = dict(paginas)
    bloqueado["https://exemplo.test/robots.txt"] = "User-agent: *\nDisallow: /catalogo/"
    monkeypatch.setattr("coletor.cli.RequestsFetcher", lambda **_: FetcherFalso(bloqueado))
    assert main(["run", CONFIG, "--saida", str(tmp_path / "s.csv"), "--cache", ""]) == 1
    assert "proibe" in capsys.readouterr().err


def test_ignorar_robots_avisa(sem_rede, tmp_path, capsys):
    main(["run", CONFIG, "--saida", str(tmp_path / "s.csv"), "--cache", "", "--ignorar-robots"])
    assert "robots.txt ignorado" in capsys.readouterr().err


def test_rede_indisponivel_devolve_dois(monkeypatch, capsys):
    def sem_requests(**_):
        raise RuntimeError("requests nao instalado")

    monkeypatch.setattr("coletor.cli.RequestsFetcher", sem_requests)
    assert main(["run", CONFIG]) == 2
    assert "requests nao instalado" in capsys.readouterr().err


def test_coleta_vazia_devolve_um(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("coletor.cli.RequestsFetcher", lambda **_: FetcherFalso({}))
    assert main(["run", CONFIG, "--saida", str(tmp_path / "s.csv"), "--cache", ""]) == 1


def test_sem_subcomando_o_argparse_recusa():
    with pytest.raises(SystemExit):
        main([])


def test_run_grava_xlsx(sem_rede, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    saida = tmp_path / "livros.xlsx"
    assert main(["run", CONFIG, "--saida", str(saida), "--cache", ""]) == 0
    aba = openpyxl.load_workbook(saida).active
    assert aba.max_row == 5  # cabecalho + 4 registros
