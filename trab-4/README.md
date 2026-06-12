# Trab-4 — Visualização de Dados com BI (Google Looker Studio)

**Disciplina:** Experimentação de Software  
**Ferramenta:** Google Looker Studio  
**Dataset:** Stack Overflow Developer Survey 2024  
**Entrega:** Dashboard (PDF) + Relatório

---

## Visão Geral

Este trabalho utiliza o **Stack Overflow Developer Survey 2024** — uma pesquisa pública anual com mais de 65.000 desenvolvedores de software ao redor do mundo — para construir um dashboard de Business Intelligence que responde questões de pesquisa sobre perfil e carreira de desenvolvedores.

---

## Questões de Pesquisa

| #       | Pergunta                                                                                          |
| ------- | ------------------------------------------------------------------------------------------------- |
| **RQ1** | Como a linguagem de programação principal se relaciona com o salário dos desenvolvedores?         |
| **RQ2** | Como o modelo de trabalho (remoto/presencial/híbrido) se relaciona com a satisfação profissional? |
| **RQ3** | Qual a relação entre nível educacional e salário dos desenvolvedores?                             |
| **RQ4** | Como os anos de experiência influenciam o salário?                                                |

---

## Estrutura do Repositório

```
trab-4/
├── README.md                   ← este arquivo
├── relatorio.md                ← relatório final em Markdown
├── data/
│   ├── survey_results_public.csv   ← dataset original (download manual — ver abaixo)
│   ├── processed_data.csv          ← dados processados (gerado pelo script)
│   └── summary_stats.csv           ← estatísticas resumo (gerado pelo script)
├── scripts/
│   └── process_data.py         ← script de limpeza e preparação dos dados
└── imgs/                       ← screenshots do dashboard final
```

---

## Como Reproduzir

### Passo 1 — Baixar o Dataset

1. Acesse: **https://survey.stackoverflow.co/2024/**
2. Clique em **"Download Full Data Set"**
3. Extraia o ZIP e copie o arquivo `survey_results_public.csv` para `trab-4/data/`

### Passo 2 — Instalar Dependências Python

```bash
pip install pandas numpy
```

### Passo 3 — Processar os Dados

```bash
cd trab-4
python scripts/process_data.py
```

Isso gera `data/processed_data.csv` e `data/summary_stats.csv`.

### Passo 4 — Importar no Google Sheets

1. Acesse **Google Sheets** (sheets.google.com)
2. Crie uma nova planilha
3. Vá em **Arquivo → Importar**
4. Selecione `data/processed_data.csv`
5. Escolha "Substituir planilha" e "Vírgula" como separador

### Passo 5 — Conectar ao Google Looker Studio

1. Acesse **https://lookerstudio.google.com/**
2. Crie um novo relatório
3. Clique em **"Adicionar dados"** → selecione **Google Sheets**
4. Conecte a planilha criada no Passo 4
5. Construa o dashboard seguindo a especificação abaixo

---

## Especificação do Dashboard

### Página 1 — Caracterização do Dataset

| Visualização                                  | Tipo                           | Campos              |
| --------------------------------------------- | ------------------------------ | ------------------- |
| Total de respondentes                         | Scorecard                      | count(id)           |
| Distribuição por país (Top 15)                | Gráfico de barras              | pais, count(id)     |
| Distribuição por linguagem principal (Top 10) | Gráfico de barras              | linguagem_principal |
| Distribuição por modelo de trabalho           | Gráfico de pizza               | modelo_trabalho     |
| Distribuição por nível educacional            | Gráfico de barras              | nivel_educacional   |
| Distribuição por grupo de experiência         | Gráfico de barras              | grupo_exp           |
| Distribuição salarial                         | Histograma / gráfico de barras | faixa_salarial      |

### Página 2 — RQ1 e RQ2

**RQ1: Linguagem × Salário**

- Gráfico de barras: mediana salarial por linguagem principal (Top 15 linguagens)
- Tabela: linguagem, nº respondentes, mediana salarial, média salarial

**RQ2: Modelo de Trabalho × Satisfação**

- Gráfico de barras agrupadas: satisfação por modelo de trabalho
- Scorecard: % muito satisfeitos por categoria de trabalho

### Página 3 — RQ3 e RQ4

**RQ3: Educação × Salário**

- Gráfico de barras: mediana salarial por nível educacional

**RQ4: Experiência × Salário**

- Gráfico de dispersão: anos_exp_pro × salario_anual_usd
- Gráfico de barras: mediana salarial por grupo de experiência

---

## Colunas do Dataset Processado

| Coluna                | Descrição                                   |
| --------------------- | ------------------------------------------- |
| `id`                  | ID do respondente                           |
| `pais`                | País do respondente                         |
| `nivel_educacional`   | Nível educacional (traduzido)               |
| `anos_exp_pro`        | Anos de experiência profissional (numérico) |
| `grupo_exp`           | Grupo de experiência (faixas)               |
| `tipo_dev`            | Tipo de desenvolvedor                       |
| `linguagens`          | Linguagens com que trabalha (lista)         |
| `linguagem_principal` | Primeira linguagem listada                  |
| `modelo_trabalho`     | Remoto / Híbrido / Presencial               |
| `satisfacao_label`    | Satisfação (traduzido)                      |
| `satisfacao_score`    | Satisfação numérica (1–5)                   |
| `salario_anual_usd`   | Salário anual em USD                        |
| `faixa_salarial`      | Faixa salarial                              |
| `tamanho_empresa`     | Tamanho da empresa                          |
| `faixa_etaria`        | Faixa etária                                |
| `tipo_emprego`        | Tipo de emprego                             |

---
