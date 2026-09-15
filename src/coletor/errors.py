"""Excecoes do coletor."""


class ColetorError(Exception):
    """Base de todos os erros do projeto."""


class ConfigError(ColetorError):
    """A configuracao da coleta e invalida. Detectada antes do primeiro request."""


class RobotsError(ColetorError):
    """A URL alvo e proibida pelo robots.txt do site."""


class FetchError(ColetorError):
    """A pagina nao pode ser obtida depois de todas as tentativas."""


class ExtracaoError(ColetorError):
    """A pagina foi obtida, mas nao produziu os campos esperados."""
