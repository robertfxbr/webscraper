# coletor

Raspador de sites em Python: lê a descrição da coleta de um arquivo YAML, percorre
as páginas, extrai os campos declarados, converte cada um para o tipo certo e
grava tudo em planilha.

O que separa este projeto de um script de scraping comum são três coisas que
normalmente ficam de fora: ele lê o `robots.txt` do site antes da primeira
requisição, respeita um intervalo mínimo entre elas, e **avisa quando um seletor
para de casar** em vez de continuar gravando linhas vazias.

São 155 testes, 100% de cobertura, e a suíte inteira roda sem rede — contra
páginas guardadas em `tests/fixtures`.

[![CI](https://github.com/robertfxbr/webscraper/actions/workflows/ci.yml/badge.svg)](https://github.com/robertfxbr/webscraper/actions/workflows/ci.yml)

## Instalação

```bash
git clone git@github.com:robertfxbr/webscraper.git
cd webscraper
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[rede,xlsx]"
```

## Uso

```bash
coletor check configs/livros.yaml                    # valida a configuração
coletor run configs/terabyte-placas-de-video.yaml     # loja real, uma página
coletor run configs/livros.yaml --max-paginas 2      # coleta e grava livros.csv
coletor run configs/livros.yaml --saida dados.xlsx   # grava planilha do Excel
```

Saída de uma execução real:

```
[robots] https://books.toscrape.com/robots.txt devolveu 404; nenhuma restricao declarada
[ok] https://books.toscrape.com/catalogue/page-1.html: 20 item(ns)
[ok] https://books.toscrape.com/catalogue/page-2.html: 20 item(ns)
40 registro(s) em 2 pagina(s) -> livros.csv
parou porque: limite de 2 pagina(s) atingido
```

```csv
titulo,preco,disponibilidade,url
A Light in the Attic,51.77,In stock,https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html
Tipping the Velvet,53.74,In stock,https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html
```

Códigos de saída: `0` coletou algo, `1` não coletou nada ou foi barrado pelo
`robots.txt`, `2` configuração inválida. Distintos de propósito: num agendador,
"o site mudou o layout" e "eu escrevi a configuração errada" pedem reações
diferentes.

### Uma configuração

```yaml
nome: livros
url_inicial: https://books.toscrape.com/catalogue/page-1.html
user_agent: coletor/0.1 (+https://github.com/robertfxbr/webscraper)

intervalo: 1.0            # segundos entre requisições
max_paginas: 3
item: article.product_pod # cada item da lista
proxima_pagina: li.next a # como avançar
chave: [titulo]           # o que define duplicata

campos:
  - nome: titulo
    seletor: h3 a
    atributo: title       # lê o atributo, não o texto
    obrigatorio: true     # sem isto, o item é descartado

  - nome: preco
    seletor: p.price_color
    tipo: dinheiro        # "£1,234.56" e "R$ 1.234,56" viram 1234.56

  - nome: url
    seletor: h3 a
    atributo: href
    tipo: url             # resolve link relativo contra a página
```

Tipos: `texto`, `numero`, `dinheiro`, `inteiro`, `url`.

## As quatro decisões de projeto

**O `robots.txt` vem antes da primeira requisição.** Se o arquivo proíbe a página
inicial, o programa recusa a coleta inteira; se proíbe uma página no meio da
paginação, ele encerra e entrega o que já tinha, dizendo por quê. Um
`Crawl-delay` declarado pelo site vence o intervalo configurado, mesmo que seja
mais lento — quem define o ritmo é o dono do servidor.

**Coluna vazia é erro, não dado.** Um seletor que deixa de casar é a falha mais
silenciosa de um scraper: o programa continua rodando e a planilha continua sendo
escrita, só que vazia. Aqui, campo marcado como `obrigatorio` derruba o item, e o
relatório final diz quantos caíram e por quê. As colunas declaradas sempre
aparecem no CSV, mesmo quando ninguém as preencheu — coluna que some esconde o
defeito.

*Isso já pegou um erro real neste repositório.* A primeira versão do
`configs/livros.yaml` lia `estoque` como número, porque a página do livro mostra
"In stock (22 available)". Só que a página de catálogo escreve apenas "In stock":
o campo virava nulo em todas as linhas. O relatório mostrou a coluna inteira
vazia na primeira execução de verdade, e a configuração foi corrigida para
`disponibilidade`, como texto.

**Número é número.** "£1,234.56" e "R$ 1.234,56" chegam como texto e saem como
`1234.56`. O separador decimal é decidido pela posição, não por configuração
regional. Planilha com número guardado como texto perde soma, ordenação e filtro,
e é o defeito mais comum de scraper amador.

**Cache em disco, por etiqueta antes de desempenho.** Enquanto se ajusta um
seletor, a mesma página seria baixada dezenas de vezes. Com cache, ela é baixada
uma vez. O servidor do outro lado não tem por que pagar pelo meu ciclo de
desenvolvimento.

## Decisões rejeitadas

O que foi considerado e descartado, com o motivo:

**Raspar qualquer loja que "desse certo".** A escolha de alvo passou por um
critério, medido e não suposto: o `robots.txt` precisa permitir aquele caminho, e
o HTML da primeira resposta precisa já conter o produto. Das cinco lojas
testadas, **Pichau devolve 403** e **Amazon devolve 503** para qualquer cliente
que não seja navegador, e **Shopee e Shein são SPA** — o HTML chega vazio e os
produtos vêm de uma API interna não publicada. Só a **Terabyte** passou nos dois
critérios, e é a única loja real em `configs/`. As outras não ficaram de fora por
serem difíceis: ficaram porque chegar nelas exigiria forjar navegador, e um
repositório que depende disso quebra sozinho no mês seguinte.

Contornar esses bloqueios é possível e não está aqui. Rotação de proxy e
resolução de captcha resolveriam o 403 da Pichau, ao custo de violar o termo de
uso dela, de queimar o IP de quem rodasse, e de virar manutenção permanente
contra um adversário que muda quando quer.

**Adivinhar o endereço interno da paginação.** Na Terabyte, o botão "ver mais"
aponta para a própria página e guarda o destino num atributo `data-pg`: a
paginação é feita por JavaScript. Dava para abrir o DevTools, descobrir qual
endereço o site chama por baixo e apontar para ele. Seria um endpoint não
documentado, que a loja pode mudar sem aviso e não prometeu a ninguém — a mesma
categoria de coisa que o projeto recusa nas outras lojas. A configuração declara
`max_paginas: 1` e diz por quê.

**Selenium.** O alvo entrega o HTML já pronto na primeira resposta, então subir um
navegador seria dezenas de vezes mais lento e mais pesado para obter exatamente o
mesmo texto. Selenium se justifica quando o conteúdo só existe depois do
JavaScript rodar; não é o caso, e usá-lo aqui seria escolher a ferramenta pela
aparência. (Um projeto meu que *precisa* de navegador está em
[botautomatic](https://github.com/robertfxbr/botautomatic-repo).)

**`urllib.robotparser`, da biblioteca padrão.** Seria menos código. Foi descartado
por ignorar `Crawl-delay`, que é justamente a informação que define o ritmo
educado da coleta, e por não dizer qual regra casou — o que torna impossível
explicar ao usuário por que uma URL foi recusada.

**Threads para baixar em paralelo.** Pareceria mais sofisticado e não serviria
para nada: o gargalo aqui é o intervalo que eu mesmo imponho entre requisições.
Paralelizar só aumentaria a carga no servidor do outro lado, que é exatamente o
que o projeto tenta não fazer.

**pandas para escrever o CSV.** Traria dezenas de megabytes de dependência para
usar uma função que o módulo `csv` da biblioteca padrão já faz. pandas se paga
quando há análise; aqui só há escrita.

**Deduplicar pela linha inteira.** Parece inofensivo e apagaria itens
legitimamente idênticos em todas as colunas coletadas — caso real quando se
raspam poucas colunas. A deduplicação só acontece se a configuração declarar
`chave`.

## Estrutura

```
src/coletor/
  robots.py     leitura do robots.txt: grupos, curingas, Allow x Disallow, Crawl-delay
  throttle.py   intervalo mínimo entre requisições, com relógio injetável
  http.py       contrato de rede + retry só nos status que fazem sentido repetir
  cache.py      cache das páginas em disco
  config.py     modelo e validação do YAML
  tipos.py      conversão de texto para número, inteiro e URL
  extrair.py    extração dos itens e da próxima página
  exportar.py   deduplicação e escrita em CSV/XLSX
  coleta.py     orquestração: robots, intervalo, busca, paginação
  cli.py        argparse: check, run
tests/          155 testes, sem rede
configs/        livros.yaml (site de treino) e terabyte (loja real), validadas no CI
```

## Desenvolvimento

```bash
pytest --cov --cov-report=term-missing
ruff check . && ruff format --check .
```

O CI roda lint, formatação, a suíte com exigência de 90% de cobertura e o `check`
de todas as configurações de `configs/`, em Python 3.11, 3.12 e 3.13.

## Licença

MIT. Ver [LICENSE](LICENSE).
