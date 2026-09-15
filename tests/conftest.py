from pathlib import Path

import pytest

from coletor.config import load_config

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASE = "https://exemplo.test/catalogo/"


def ler(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


@pytest.fixture
def config():
    return load_config(FIXTURES / "config.yaml")


@pytest.fixture
def paginas() -> dict[str, str]:
    return {
        BASE + "pagina1.html": ler("pagina1.html"),
        BASE + "pagina2.html": ler("pagina2.html"),
    }
