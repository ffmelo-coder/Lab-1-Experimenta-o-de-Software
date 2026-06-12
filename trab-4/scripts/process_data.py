import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE  = os.path.join(BASE_DIR, "data", "survey_results_public.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "processed_data.csv")
STATS_FILE  = os.path.join(BASE_DIR, "data", "summary_stats.csv")

COLUMNS = {
    "ResponseId":           "id",
    "Country":              "pais",
    "EdLevel":              "nivel_educacional",
    "YearsCodePro":         "anos_exp_pro",
    "DevType":              "tipo_dev",
    "LanguageHaveWorkedWith": "linguagens",
    "LanguageWantToWorkWith": "linguagens_desejadas",
    "DatabaseHaveWorkedWith": "bancos",
    "PlatformHaveWorkedWith": "plataformas",
    "RemoteWork":           "modelo_trabalho",
    "OrgSize":              "tamanho_empresa",
    "JobSat":               "satisfacao",
    "ConvertedCompYearly":  "salario_anual_usd",
    "Age":                  "faixa_etaria",
    "Employment":           "tipo_emprego",
    "MentalHealth":         "saude_mental",
    "ICorPM":               "cargo_ic_ou_gestao",
}

EDUCATION_MAP = {
    "Bachelor’s degree (B.A., B.S., B.Eng., etc.)": "Graduação",
    "Master’s degree (M.A., M.S., M.Eng., MBA, etc.)": "Mestrado",
    "Some college/university study without earning a degree": "Faculdade incompleta",
    "Secondary school (e.g. American high school, German Realschule or Gymnasium, etc.)": "Ensino Médio",
    "Associate degree (A.A., A.S., etc.)": "Técnico/Associado",
    "Professional degree (JD, MD, Ph.D, Ed.D, etc.)": "Pós-graduação/Doutorado",
    "Primary/elementary school": "Ensino Fundamental",
    "Something else": "Outro",
}

REMOTE_MAP = {
    "Remote":        "Remoto",
    "Hybrid (some remote, some in-person)": "Híbrido",
    "In-person":     "Presencial",
}

SATISFACTION_MAP = {
    "Very satisfied":       "Muito satisfeito",
    "Slightly satisfied":   "Satisfeito",
    "Neither satisfied nor dissatisfied": "Neutro",
    "Slightly dissatisfied": "Insatisfeito",
    "Very dissatisfied":    "Muito insatisfeito",
}

SATISFACTION_SCORE = {
    "Very satisfied":       5,
    "Slightly satisfied":   4,
    "Neither satisfied nor dissatisfied": 3,
    "Slightly dissatisfied": 2,
    "Very dissatisfied":    1,
}


def extract_primary_language(cell):
    """Retorna a primeira linguagem listada (considerada principal)."""
    if pd.isna(cell):
        return np.nan
    languages = [l.strip() for l in str(cell).split(";") if l.strip()]
    return languages[0] if languages else np.nan


def clean_years_exp(cell):
    """Converte anos de experiência para numérico."""
    if pd.isna(cell):
        return np.nan
    val = str(cell).strip()
    if val == "Less than 1 year":
        return 0.5
    if val == "More than 50 years":
        return 51.0
    try:
        return float(val)
    except ValueError:
        return np.nan


def classify_salary(salary):
    """Classifica salário em faixas."""
    if pd.isna(salary):
        return np.nan
    if salary < 30_000:
        return "< 30k"
    elif salary < 60_000:
        return "30k – 60k"
    elif salary < 100_000:
        return "60k – 100k"
    elif salary < 150_000:
        return "100k – 150k"
    else:
        return "> 150k"


def classify_experience(years):
    """Classifica experiência em grupos."""
    if pd.isna(years):
        return np.nan
    if years < 2:
        return "0–1 ano"
    elif years < 5:
        return "2–4 anos"
    elif years < 10:
        return "5–9 anos"
    elif years < 20:
        return "10–19 anos"
    else:
        return "20+ anos"


def main():
    print(f"[1/6] Carregando dataset de '{INPUT_FILE}'...")
    if not os.path.exists(INPUT_FILE):
        print(f"\n  ERRO: Arquivo não encontrado.")
        print(f"  Baixe o dataset em: https://survey.stackoverflow.co/2024/")
        print(f"  E salve em: {INPUT_FILE}")
        return

    df_raw = pd.read_csv(INPUT_FILE, low_memory=False)
    print(f"       {len(df_raw):,} respondentes carregados, {len(df_raw.columns)} colunas")

    print("[2/6] Selecionando e renomeando colunas...")
    cols_available = [c for c in COLUMNS if c in df_raw.columns]
    df = df_raw[cols_available].rename(columns=COLUMNS)

    print("[3/6] Limpando e transformando dados...")

   
    df["anos_exp_pro"] = df["anos_exp_pro"].apply(clean_years_exp)
    df["grupo_exp"] = df["anos_exp_pro"].apply(classify_experience)

    df["linguagem_principal"] = df["linguagens"].apply(extract_primary_language)

  
    df["nivel_educacional"] = df["nivel_educacional"].map(EDUCATION_MAP).fillna(df.get("nivel_educacional", ""))
    df["modelo_trabalho"]   = df["modelo_trabalho"].map(REMOTE_MAP).fillna(df.get("modelo_trabalho", ""))
    df["satisfacao_label"]  = df["satisfacao"].map(SATISFACTION_MAP).fillna(df.get("satisfacao", ""))
    df["satisfacao_score"]  = df["satisfacao"].map(SATISFACTION_SCORE)

    
    if "salario_anual_usd" in df.columns:
        df["salario_anual_usd"] = pd.to_numeric(df["salario_anual_usd"], errors="coerce")
        df.loc[df["salario_anual_usd"] > 500_000, "salario_anual_usd"] = np.nan
        df.loc[df["salario_anual_usd"] < 0,       "salario_anual_usd"] = np.nan
        df["faixa_salarial"] = df["salario_anual_usd"].apply(classify_salary)

    print("[4/6] Filtrando respondentes empregados com dados mínimos...")
    if "tipo_emprego" in df.columns:
        employed_mask = df["tipo_emprego"].str.contains(
            "Employed|Independent contractor|Freelancer", na=False, case=False
        )
        df = df[employed_mask]
    print(f"       {len(df):,} respondentes após filtro")

    print("[5/6] Salvando CSV processado...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"       Salvo em: {OUTPUT_FILE}")

    print("[6/6] Gerando estatísticas resumo...")
    stats = []

    if "salario_anual_usd" in df.columns:
        sal = df["salario_anual_usd"].dropna()
        stats.append({"metrica": "Mediana salarial (USD)", "valor": round(sal.median(), 2)})
        stats.append({"metrica": "Média salarial (USD)",   "valor": round(sal.mean(), 2)})
        stats.append({"metrica": "Respondentes com salário", "valor": len(sal)})

    if "anos_exp_pro" in df.columns:
        exp = df["anos_exp_pro"].dropna()
        stats.append({"metrica": "Mediana de experiência (anos)", "valor": round(exp.median(), 1)})

    if "satisfacao_score" in df.columns:
        sat = df["satisfacao_score"].dropna()
        stats.append({"metrica": "Média de satisfação (1–5)", "valor": round(sat.mean(), 2)})

    stats.append({"metrica": "Total de respondentes (filtrado)", "valor": len(df)})

    pd.DataFrame(stats).to_csv(STATS_FILE, index=False, encoding="utf-8-sig")

    print("\n=== Resumo ===")
    for s in stats:
        print(f"  {s['metrica']}: {s['valor']}")
    print(f"\nArquivos gerados:")
    print(f"  {OUTPUT_FILE}")
    print(f"  {STATS_FILE}")
    print("\nPróximo passo: importe 'processed_data.csv' no Google Sheets.")


if __name__ == "__main__":
    main()
