# Relatório de Análise — Atividade de Code Review em Repositórios Populares do GitHub

**Disciplina**: Experimentação de Software  
**Instituição**: PUCMINAS  
**Período**: 01/2026  
**Autores**: Augusto Fuscaldi e Filipe Faria

---

## 1. Introdução

### 1.1 Contextualização

A prática de code review tornou-se uma constante nos processos de desenvolvimento ágil. Em repositórios open source hospedados no GitHub, as revisões ocorrem principalmente via Pull Requests (PRs): um autor submete mudanças, revisores inspecionam o código e, após discussão, o PR pode ser aceito (merged) ou fechado (closed).

Este trabalho investiga a atividade de code review em repositórios populares do GitHub, buscando identificar quais variáveis de um PR (tamanho, tempo de análise, descrição, interações) se relacionam com o feedback final (merge vs closed) e com o número de revisões realizadas.

### 1.2 Problema Foco do Experimento

Nos processos colaborativos de projetos open source surge a seguinte questão empírica: quais características de um Pull Request influenciam seu resultado final (merge vs closed) e a intensidade do processo de revisão (número de revisões)? Em outras palavras, PRs maiores, mais antigos, com descrições melhores ou com mais discussões tendem a ser aceitos com mais frequência ou a sofrerem mais revisões?

Este estudo busca responder essas perguntas analisando PRs submetidos a repositórios populares do GitHub, usando como base o pipeline implementado em `trab-3`.

### 1.3 Questões de Pesquisa

As questões de pesquisa seguem duas dimensões (Feedback Final e Número de Revisões):

A. Feedback Final das Revisões (Status do PR)

- **RQ01**: Qual a relação entre o **tamanho** dos PRs e o feedback final das revisões (merge vs closed)?
- **RQ02**: Qual a relação entre o **tempo de análise** dos PRs e o feedback final das revisões?
- **RQ03**: Qual a relação entre a **descrição** dos PRs e o feedback final das revisões?
- **RQ04**: Qual a relação entre as **interações** nos PRs (comentários, participantes) e o feedback final das revisões?

B. Número de Revisões

- **RQ05**: Qual a relação entre o **tamanho** dos PRs e o número de revisões realizadas?
- **RQ06**: Qual a relação entre o **tempo de análise** dos PRs e o número de revisões realizadas?
- **RQ07**: Qual a relação entre a **descrição** dos PRs e o número de revisões realizadas?
- **RQ08**: Qual a relação entre as **interações** nos PRs e o número de revisões realizadas?

### 1.4 Definição de Métricas

As métricas calculadas para cada PR e utilizadas nas análises são:

| Dimensão            | Métrica / Proxy                                                |
| ------------------- | -------------------------------------------------------------- |
| Tamanho             | Número de arquivos modificados (`changedFiles`), adições (`additions`), remoções (`deletions`), `total_changes` |
| Tempo de Análise    | Intervalo entre `createdAt` e `mergedAt`/`closedAt` (horas) — armazenado em `time_to_close_hours` |
| Descrição           | Número de caracteres do corpo do PR (`body_length`)            |
| Interações          | Número de revisões (`reviews.totalCount`), número de participantes (`participants.totalCount`), comentários (`comments.totalCount`) |
| Feedback Final      | Estado final do PR (`state`): `MERGED` ou `CLOSED`             |

Esses campos são extraídos diretamente da query GraphQL implementada em `github_utils.py` (campo `pullRequests.nodes`), e o pipeline de `collect_prs.py` aplica os filtros: PRs com `reviews.totalCount` < 1 são descartados; PRs com tempo de análise ≤ 1 hora são descartados (provável revisão automática). O arquivo de saída padrão do pipeline é `prs_coletados.csv`, com cabeçalho compatível com as chaves acima.

### 1.5 Hipóteses

Formulam-se hipóteses informais a serem testadas com o dataset agregado (medianas dos PRs):

- **H1 (RQ01)**: PRs maiores (mais arquivos/linhas alteradas) tendem a ter menor probabilidade de serem aceitos (merge), pois são mais complexos e difíceis de revisar, com mais chance de possuir bugs.
- **H2 (RQ02)**: PRs com maior tempo de análise tendem a ter menor probabilidade de merge (tempo longos podem indicar problemas, conflitos ou necessidade de mudanças substanciais).
- **H3 (RQ03)**: PRs com descrições mais detalhadas (maior `body_length`) tendem a ter maior probabilidade de merge, pois facilitam a avaliação pelos revisores.
- **H4 (RQ04)**: PRs com maior número de interações (comentários, participantes) tendem a ter menor taxa de merge inicial (discussões indicam controvérsia), mas podem evoluir para merge após iterações.

- **H5 (RQ05)**: PRs maiores exigem mais revisões (maior `reviews.totalCount`).
- **H6 (RQ06)**: PRs com maior tempo de análise tendem a acumular mais revisões.
- **H7 (RQ07)**: PRs com descrições mais ricas tendem a exigir menos revisões (descrição clara reduz idas e vindas).
- **H8 (RQ08)**: PRs com mais interações correlacionam-se positivamente com o número de revisões (discussões prolongadas aumentam o número de revisões registradas).

### 1.6 Objetivos

**Objetivo Principal**: Investigar empiricamente quais características de Pull Requests influenciam o feedback final (merge vs closed) e o número de revisões em repositórios populares do GitHub.

**Objetivos Específicos**:

- Selecionar repositórios populares usando `collect_repos.py` (padrão: 200 repositórios com ≥ 100 PRs Merged+Closed).
- Coletar PRs dos repositórios selecionados usando `collect_prs.py`, aplicando filtros: PRs com estado MERGED/CLOSED, ≥ 1 revisão, tempo de análise > 1 hora.
- Construir o dataset `prs_coletados.csv` contendo as métricas listadas em 1.4 (`changedFiles`, `additions`, `deletions`, `time_to_close_hours`, `body_length`, `reviews_count`, `participants_count`, `comments_count`, `state`).
- Calcular estatísticas descritivas (medianas) por métrica e executar testes de correlação apropriados entre variáveis explicativas e as respostas (feedback final e número de revisões).

**Decisão sobre teste estatístico**: para as análises de associação será utilizado o coeficiente de correlação de Spearman (ρ), por ser não-paramétrico e robusto a distribuições fortemente enviesadas e outliers — comportamento esperado nas métricas de PR (por exemplo, `additions` e `deletions` costumam ter distribuição assimétrica). Quando aplicável, complementar-se-á com testes de hipótese (p-valor) e análise descritiva baseada em medianas.

**Objetivos Específicos**:
Os scripts disponíveis implementam a pipeline de coleta: `collect_repos.py` seleciona repositórios populares via GraphQL (por padrão, `--target=200` e `--min-prs=100`), `collect_prs.py` percorre cada repositório buscando PRs (padrão `--per-page=50`, concorrência assíncrona `--concurrency=5`) e `github_utils.py` contém as queries GraphQL usadas para obter PRs e repositórios. Os critérios de filtragem adotados no pipeline são consistentes com o objetivo de analisar PRs que passaram por revisão humana: considerar apenas PRs com estado MERGED ou CLOSED, que possuam ao menos uma revisão (`reviews.totalCount >= 1`) e cujo tempo entre criação e fechamento/merge seja maior que 1 hora (evita revisões automáticas/bots).

---

