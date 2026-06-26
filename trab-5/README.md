# GraphQL vs REST: Um Experimento Controlado

Sistema desenvolvido para o Laboratório de Experimentação de Software - PUCMINAS 01/2026

## Visão Geral

Este projeto conduz um experimento controlado comparando a API REST e a API GraphQL do GitHub na mesma tarefa (obter metadados de um repositório), medindo tempo de resposta e tamanho do payload.

**Status atual**: Lab05S01, Lab05S02 e Lab05S03 concluídos. 100 repositórios, 1.000 medições, relatório completo em `relatorio.md` e dashboard consolidado em `imgs/dashboard.png`.

## Questões de Pesquisa

- **RQ1**: Respostas às consultas GraphQL são mais rápidas que respostas às consultas REST?
- **RQ2**: Respostas às consultas GraphQL têm tamanho menor que respostas às consultas REST?

## Estrutura do Repositório

```
trab-5/
├── README.md              ← este arquivo
├── relatorio.md            ← desenho do experimento, metodologia e resultados
├── scripts/
│   ├── github_utils.py     ← chamadas REST/GraphQL instrumentadas (tempo + tamanho)
│   ├── select_repos.py     ← Etapa 1: seleciona a amostra de repositórios
│   ├── run_experiment.py   ← Etapa 2: executa o experimento (REST vs GraphQL, K repetições)
│   ├── analyze_results.py  ← Etapas 3/4: testes estatísticos pareados + gráficos individuais
│   └── dashboard.py        ← Etapa 4 (Lab05S03): monta o dashboard único a partir dos gráficos e dados
├── data/                   ← CSVs gerados pelos scripts
└── imgs/                   ← gráficos individuais + dashboard.png (visão consolidada)
```

## Instalação e Requisitos

```bash
pip install requests pandas matplotlib seaborn scipy
```

### Token do GitHub

A GraphQL API do GitHub **exige autenticação** mesmo para dados públicos (a REST funciona sem token, mas com limite de taxa reduzido). Para rodar o experimento completo:

1. Acesse https://github.com/settings/tokens.
2. Gere um token (classic) com permissão `public_repo`.
3. Edite a constante `GITHUB_TOKEN` no topo de `scripts/github_utils.py` **ou** defina a variável de ambiente `GITHUB_TOKEN` (tem precedência sobre a constante).

## Como Usar

### Etapa 1: Selecionar a amostra de repositórios

Não exige token (Search API funciona, com limite de taxa, sem autenticação).

```bash
cd scripts
python select_repos.py --target 100 --output ../data/repos_amostra.csv
```

| Argumento | Padrão | Descrição |
|---|---|---|
| `--target` | `100` | Número de repositórios na amostra |
| `--output` | `../data/repos_amostra.csv` | CSV de saída |

### Etapa 2: Executar o experimento

Requer `GITHUB_TOKEN` válido.

```bash
python run_experiment.py --repos ../data/repos_amostra.csv --output ../data/resultados_brutos.csv --repetitions 5
```

| Argumento | Padrão | Descrição |
|---|---|---|
| `--repos` | `../data/repos_amostra.csv` | CSV de entrada (Etapa 1) |
| `--output` | `../data/resultados_brutos.csv` | CSV de saída com as medições |
| `--repetitions` | `5` | Repetições (K) por tratamento por repositório |
| `--delay-min` / `--delay-max` | `0.2` / `0.5` | Intervalo aleatório (s) entre requisições |

A ordem de toda a sequência de medições é embaralhada antes da execução (não apenas dentro de cada repositório), e os resultados são gravados incrementalmente, de modo que uma interrupção não perde o progresso já salvo.

**Saída** (`resultados_brutos.csv`): `repo`, `owner`, `name`, `treatment` (`REST`/`GraphQL`), `repetition`, `order_index`, `timestamp`, `status_code`, `ok`, `elapsed_ms`, `size_bytes`, `error`.

### Etapa 3: Analisar os resultados

```bash
python analyze_results.py --input ../data/resultados_brutos.csv --imgs ../imgs
```

Descarta medições com falha, agrega as repetições de cada repositório pela mediana (evitando pseudo-replicação), escolhe entre teste t pareado e Wilcoxon signed-rank conforme o teste de normalidade de Shapiro-Wilk sobre as diferenças pareadas, imprime os resultados de RQ1 e RQ2 no terminal, e salva gráficos em `imgs/` e um resumo em `data/resumo_estatistico.csv`.

### Etapa 4: Montar o dashboard

```bash
pip install pillow
python dashboard.py --data ../data --imgs ../imgs --output ../imgs/dashboard.png
```

| Argumento | Padrão | Descrição |
|---|---|---|
| `--data` | `../data` | Diretório com `resultados_brutos.csv` e `resumo_estatistico.csv` |
| `--imgs` | `../imgs` | Diretório com os gráficos individuais (gerados pela Etapa 3) e onde o dashboard é salvo |
| `--output` | `../imgs/dashboard.png` | Caminho do dashboard final |

Lê os CSVs já processados e os 10 gráficos já gerados pela Etapa 3, e monta uma única imagem (`dashboard.png`) com cartões de resumo (objetos experimentais, medições coletadas, resultado de RQ1 e RQ2) seguidos pelos gráficos de cada questão de pesquisa, lado a lado, para permitir uma leitura visual rápida do experimento completo.

## Desenho do Experimento

Ver `relatorio.md`, Seção 2, para o desenho completo: hipóteses, variáveis dependentes/independentes, tratamentos, objetos experimentais, tipo de projeto, quantidade de medições e ameaças à validade.

## Limitações Conhecidas

1. **GraphQL exige token sempre**: não é possível medir GraphQL anonimamente, diferente do REST.
2. **REST sem seleção de campos**: a comparação de tamanho de payload reflete tanto a tecnologia quanto a impossibilidade de REST do GitHub filtrar campos (discutido como ameaça à validade no relatório).
3. **Specific ao GitHub**: resultados não generalizam automaticamente para outras APIs REST/GraphQL.

## Licença

Projeto acadêmico - PUCMINAS 2026

## Autores

Augusto Fuscaldi Cerezo

Filipe Faria Melo

Desenvolvido para a disciplina de Experimentação de Software
