# Análise de Code Review em Repositórios Populares do GitHub

Sistema desenvolvido para o Laboratório de Experimentação de Software - PUCMINAS 01/2026

## Visão Geral

Este projeto coleta e analisa Pull Requests de repositórios populares do GitHub para investigar como características de um PR (tamanho, tempo, descrição e interações) se relacionam com o feedback final (MERGED vs CLOSED) e com o número de revisões realizadas.

## Questões de Pesquisa

O sistema coleta dados para responder as seguintes questões:

**Feedback Final (MERGED vs CLOSED):**

- **RQ01**: Qual a relação entre o **tamanho** dos PRs e o feedback final das revisões?
- **RQ02**: Qual a relação entre o **tempo de análise** dos PRs e o feedback final das revisões?
- **RQ03**: Qual a relação entre a **descrição** dos PRs e o feedback final das revisões?
- **RQ04**: Qual a relação entre as **interações** nos PRs e o feedback final das revisões?

**Número de Revisões:**

- **RQ05**: Qual a relação entre o **tamanho** dos PRs e o número de revisões realizadas?
- **RQ06**: Qual a relação entre o **tempo de análise** dos PRs e o número de revisões realizadas?
- **RQ07**: Qual a relação entre a **descrição** dos PRs e o número de revisões realizadas?
- **RQ08**: Qual a relação entre as **interações** nos PRs e o número de revisões realizadas?

## Arquitetura do Sistema

### Módulos

```
trab-3/
├── github_utils.py          # Módulo compartilhado com queries GraphQL e funções auxiliares
├── collect_repos.py         # Etapa 1: seleciona repositórios populares
├── collect_prs.py           # Etapa 2: coleta PRs dos repositórios selecionados
├── analyze_prs.py           # Etapa 3: interface gráfica de análise e visualização
├── repos_selecionados.csv   # Saída da etapa 1
├── prs_coletados.csv        # Saída da etapa 2
├── RELATORIO.md             # Relatório completo do experimento
└── README.md                # Este arquivo
```

### Fluxo de Execução

```
collect_repos.py  →  repos_selecionados.csv
        ↓
collect_prs.py    →  prs_coletados.csv
        ↓
analyze_prs.py    →  Gráficos e análise estatística
```

### Módulo Compartilhado (github_utils.py)

Centraliza toda a lógica de comunicação com a API:

- `fetch_repositories()` — Requisições GraphQL para selecionar repositórios populares
- `async_fetch_pull_requests()` — Coleta assíncrona de PRs por repositório
- `validate_token()` / `async_validate_token()` — Validação do token do GitHub
- `export_repos_csv()` — Exporta lista de repositórios selecionados
- `init_prs_csv()` / `append_prs_csv()` — Gerencia o CSV de PRs com escrita incremental

## Instalação e Requisitos

### Dependências

```bash
pip install aiohttp scipy matplotlib numpy
```

> `tkinter` já vem instalado com Python (biblioteca padrão).

### Token do GitHub

O token precisa ser inserido manualmente no topo dos arquivos de coleta:

1. Acesse https://github.com/settings/tokens
2. Clique em "Generate new token (classic)"
3. Selecione a permissão `public_repo`
4. Copie o token gerado e insira nos arquivos:

**`collect_repos.py`** (linha 5):

```python
GITHUB_TOKEN = "ghp_seu_token_aqui"
```

**`collect_prs.py`** (linha 13):

```python
GITHUB_TOKEN = "ghp_seu_token_aqui"
```

## Como Usar

O projeto é executado em três etapas sequenciais.

---

### Etapa 1 — Selecionar Repositórios (`collect_repos.py`)

Consulta a API do GitHub e seleciona repositórios populares com número mínimo de PRs.

```bash
python collect_repos.py
```

**Argumentos disponíveis:**

| Argumento    | Padrão                   | Descrição                                         |
| ------------ | ------------------------ | ------------------------------------------------- |
| `--target`   | `200`                    | Número de repositórios a selecionar               |
| `--min-prs`  | `100`                    | Mínimo de PRs (MERGED+CLOSED) para incluir o repo |
| `--per-page` | `20`                     | Itens por página da API (máx. 100)                |
| `--output`   | `repos_selecionados.csv` | Arquivo CSV de saída                              |

**Exemplos:**

```bash
# Coleta padrão: 200 repos com >= 100 PRs
python collect_repos.py

# Teste rápido: 20 repositórios com critério mais flexível
python collect_repos.py --target 20 --min-prs 50

# Coleta maior com saída customizada
python collect_repos.py --target 500 --output meus_repos.csv
```

**Saída:** arquivo `repos_selecionados.csv` com colunas `Owner`, `Nome`, `Estrelas`, `Linguagem`, `Merged PRs`, `Closed PRs`.

---

### Etapa 2 — Coletar Pull Requests (`collect_prs.py`)

Lê o CSV da etapa anterior e coleta todos os PRs de cada repositório de forma assíncrona.

```bash
python collect_prs.py
```

**Argumentos disponíveis:**

| Argumento        | Padrão                   | Descrição                                               |
| ---------------- | ------------------------ | ------------------------------------------------------- |
| `--repos`        | `repos_selecionados.csv` | CSV de entrada gerado pela etapa 1                      |
| `--output`       | `prs_coletados.csv`      | CSV de saída com os PRs coletados                       |
| `--max-prs`      | `0`                      | Máximo de PRs válidos por repositório (`0` = ilimitado) |
| `--per-page`     | `50`                     | PRs por página da API (máx. 100)                        |
| `--concurrency`  | `5`                      | Repositórios processados em paralelo                    |
| `--delay`        | `0.0`                    | Delay (segundos) entre páginas de um mesmo repositório  |
| `--page-retries` | `3`                      | Tentativas extras por página em caso de erro            |

**Exemplos:**

```bash
# Coleta padrão (todos os PRs, 5 repos em paralelo)
python collect_prs.py

# Coleta limitada a 200 PRs por repositório para teste rápido
python collect_prs.py --max-prs 200 --concurrency 3

# Usando CSVs customizados
python collect_prs.py --repos meus_repos.csv --output meus_prs.csv

# Coleta mais conservadora (evita rate limiting)
python collect_prs.py --concurrency 2 --delay 0.5
```

**Filtros aplicados automaticamente** (PRs descartados):

- Estado diferente de `MERGED` ou `CLOSED`
- Sem nenhuma revisão (`reviews_count < 1`)
- Tempo de análise ≤ 1 hora (evita merges automáticos/bots)

**Saída:** arquivo `prs_coletados.csv` com as seguintes colunas:

| Coluna                | Descrição                                   |
| --------------------- | ------------------------------------------- |
| `repo`                | Nome completo do repositório (`owner/nome`) |
| `pr_number`           | Número do PR                                |
| `title`               | Título do PR                                |
| `state`               | Estado: `MERGED` ou `CLOSED`                |
| `author`              | Login do autor                              |
| `created_at`          | Data/hora de criação                        |
| `closed_at`           | Data/hora de fechamento ou merge            |
| `time_to_close_hours` | Tempo entre criação e fechamento (horas)    |
| `changed_files`       | Número de arquivos modificados              |
| `additions`           | Linhas adicionadas                          |
| `deletions`           | Linhas removidas                            |
| `total_changes`       | Total de mudanças (additions + deletions)   |
| `body_length`         | Comprimento da descrição do PR (caracteres) |
| `reviews_count`       | Número de revisões                          |
| `participants_count`  | Número de participantes                     |
| `comments_count`      | Número de comentários                       |

---

### Etapa 3 — Analisar e Visualizar (`analyze_prs.py`)

Interface gráfica que carrega o CSV de PRs e exibe gráficos e estatísticas para cada RQ.

```bash
pip install matplotlib numpy scipy
python analyze_prs.py
```

> Se `scipy` não estiver instalado, o p-valor das correlações de Spearman não é calculado, mas os gráficos ainda funcionam.

#### Visão Geral da Interface

A janela principal exibe:

- **Barra superior** — campo para selecionar o arquivo CSV e botão de carregamento
- **Barra de status** — totais de PRs, contagem de MERGED/CLOSED, botões de gráficos e filtros
- **Tabela paginada** — exibe os PRs carregados com navegação por páginas

#### Carregando os Dados

O script tenta carregar `prs_coletados.csv` automaticamente ao iniciar. Para usar outro arquivo, clique em **"…"**, selecione o CSV e clique em **"📂 Carregar"**.

#### Filtros

Clique em **"🔍 Filtros"** para filtrar por:

| Filtro    | Descrição                                   |
| --------- | ------------------------------------------- |
| Estado    | `Todos`, `MERGED` ou `CLOSED`               |
| Repo      | Texto parcial no nome do repositório        |
| Reviews ≥ | Mínimo de revisões                          |
| Tempo (h) | Faixa de tempo de análise (mínimo e máximo) |

#### Janela de Gráficos

Clique em **"📊 Ver Gráficos"** para abrir a janela de análise. Os gráficos são organizados em abas:

| Aba                        | Conteúdo                                                             |
| -------------------------- | -------------------------------------------------------------------- |
| Visão Geral                | Distribuição MERGED/CLOSED (pizza) e top 10 repositórios por PRs     |
| RQ01 – Tamanho/Estado      | Medianas de tamanho por estado (MERGED vs CLOSED)                    |
| RQ01 – Médias/Estado       | Médias de tamanho por estado                                         |
| RQ02 – Tempo/Estado        | Mediana e distribuição do tempo de análise por estado                |
| RQ02 – ZoomIn              | Distribuição do tempo de análise (faixa 0–1.000h)                    |
| RQ03 – Descrição/Estado    | Mediana do body_length por estado e % MERGED por faixa de descrição  |
| RQ04 – Interações/Estado   | Medianas de comentários, participantes e reviews por estado          |
| RQ05 – Tamanho/Revisões    | Box plot por quintil de tamanho vs número de revisões                |
| RQ06 – Tempo/Revisões      | Heatmap 2D de tempo de análise vs número de revisões                 |
| RQ06 – ZoomOut             | Heatmap 2D com escala ampliada                                       |
| RQ07 – Descrição/Revisões  | Mediana de revisões por faixa de body_length                         |
| RQ08 – Interações/Revisões | Box plot por quintil de interações vs número de revisões             |
| Taxa de Merge              | % de PRs MERGED por faixa de tamanho, tempo, descrição e comentários |
| Resumo Estatístico         | Estatísticas descritivas e tabela de correlação de Spearman          |

#### Entendendo os Gráficos

![Visão Geral](imgs/visao_geral.png)

![RQ01 - Tamanho por Estado](imgs/rq01_mediana.png)

![RQ05 - Tamanho vs Revisões](imgs/rq05.png)

![Resumo Estatístico](imgs/resumo.png)

**Correlação de Spearman (ρ):** exibida nos títulos dos gráficos de correlação. Mede a associação monotônica entre duas variáveis sem assumir distribuição normal.

| \|ρ\|       | Interpretação |
| ----------- | ------------- |
| 0,00 – 0,19 | Desprezível   |
| 0,20 – 0,39 | Fraca         |
| 0,40 – 0,59 | Moderada      |
| 0,60 – 0,79 | Forte         |
| 0,80 – 1,00 | Muito forte   |

O **sinal** indica a direção: positivo significa que as duas variáveis crescem juntas; negativo significa que crescem em direções opostas.

## Detalhes Técnicos

### API do GitHub

- GraphQL API v4 (`https://api.github.com/graphql`)
- Autenticação por token pessoal com permissão `public_repo`
- Paginação automática com cursor
- Retry com backoff exponencial: até 3 tentativas por página (5s → 10s → 20s)

### Coleta Assíncrona

`collect_prs.py` usa `aiohttp` + `asyncio` para processar múltiplos repositórios em paralelo, controlado pelo parâmetro `--concurrency`. Cada repositório escreve seus PRs no CSV de forma atômica via `asyncio.Lock`, permitindo retomar a análise mesmo em execuções parciais.

### Tratamento de Erros

- **Rate limiting:** retry automático com backoff exponencial
- **Repositório sem dados:** ignorado, coleta dos demais continua
- **Página com erro GraphQL:** até `--page-retries` tentativas antes de abandonar o repositório
- **Token inválido:** verificado antes de iniciar a coleta em ambos os scripts

## Resolução de Problemas

### Token inválido

**Sintoma:** `Token inválido ou sem permissão. Verifique.`

**Soluções:**

- Confirmar que o token começa com `ghp_` ou `github_pat_`
- Confirmar permissão `public_repo` no token
- Gerar novo token se estiver expirado

### Arquivo `repos_selecionados.csv` não encontrado

**Sintoma:** `Arquivo 'repos_selecionados.csv' não encontrado. Execute collect_repos.py primeiro.`

**Solução:** Execute a etapa 1 antes da etapa 2:

```bash
python collect_repos.py
python collect_prs.py
```

### Coleta muito lenta ou interrompida

**Possíveis causas:** rate limiting da API, conexão instável, ou repositórios muito grandes.

**Soluções:**

- Reduzir `--concurrency` (ex.: `--concurrency 2`)
- Adicionar delay entre páginas: `--delay 1.0`
- Aumentar tentativas: `--page-retries 5`
- Os PRs já gravados no CSV são preservados; a coleta pode ser retomada parcialmente importando o CSV na GUI

### `scipy` não encontrado

**Sintoma:** p-valores aparecem como `N/D` nos gráficos.

**Solução:**

```bash
pip install scipy
```

### Interface gráfica não abre (tkinter)

**Sintoma:** `ModuleNotFoundError: No module named 'tkinter'`

**Solução (Linux/Mac):**

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Mac (via Homebrew)
brew install python-tk
```

No Windows, `tkinter` já está incluído na instalação padrão do Python.

## Link para PRs coletadas

Uma vez que o collect_prs demora muito para coletar todos os dados (para nós levou 13 horas), deixamos aqui o link para o arquivo no google drive para usar o sistema com mais velocidade.

https://drive.google.com/file/d/1a94Xj6TA6iDWE-6U6IRliS4hLRUttUNS/view?usp=sharing

## Limitações Conhecidas

1. **Rate limiting:** a API do GitHub limita requisições. O retry automático mitiga, mas conexões muito lentas podem acumular erros.
2. **Repositórios muito grandes:** repos com dezenas de milhares de PRs consomem muitas páginas e aumentam o tempo de coleta significativamente.
3. **Snapshot temporal:** os dados representam o estado dos PRs no momento da coleta.
4. **`body_length` inclui markdown:** o comprimento da descrição contém tags de formatação, o que pode distorcer a métrica de riqueza textual.

## Licença

Projeto acadêmico - PUCMINAS 2026

## Autores

Augusto Fuscaldi Cerezo

Filipe Faria Melo

Desenvolvido para a disciplina de Experimentação de Software
