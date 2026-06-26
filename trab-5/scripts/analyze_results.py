import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats


def load_data(path):
    df = pd.read_csv(path)
    before = len(df)
    df = df[df["ok"] == True].copy()
    removed = before - len(df)
    if removed:
        print(f"Aviso: {removed} medições com falha (timeout/erro/rate limit) descartadas de {before}.")
    return df


def aggregate_by_repo(df, metric):
    agg = df.groupby(["repo", "treatment"])[metric].median().reset_index()
    wide = agg.pivot(index="repo", columns="treatment", values=metric).dropna()
    return wide


def run_paired_test(wide, label, unit):
    rest_vals, graphql_vals = wide["REST"], wide["GraphQL"]
    diff = rest_vals - graphql_vals
    n = len(diff)

    shapiro_p = stats.shapiro(diff).pvalue if 3 <= n <= 5000 else None
    if shapiro_p is not None and shapiro_p > 0.05:
        stat, p_value = stats.ttest_rel(rest_vals, graphql_vals)
        test_name = "Teste t pareado"
    else:
        stat, p_value = stats.wilcoxon(rest_vals, graphql_vals)
        test_name = "Wilcoxon signed-rank"

    pct_diff = 100 * (rest_vals.median() - graphql_vals.median()) / rest_vals.median()

    print(f"\n=== {label} (n={n} repositórios) ===")
    print(f"Mediana REST:    {rest_vals.median():.2f} {unit}")
    print(f"Mediana GraphQL: {graphql_vals.median():.2f} {unit}")
    print(f"Diferença relativa (REST -> GraphQL): {pct_diff:+.1f}%")
    if shapiro_p is not None:
        print(f"Shapiro-Wilk na diferença: p={shapiro_p:.4g} ({'normal' if shapiro_p > 0.05 else 'não normal'})")
    print(f"{test_name}: estatística={stat:.4f}, p-valor={p_value:.6g}")
    print("H0 rejeitada (alpha=0.05): " + ("SIM" if p_value < 0.05 else "NÃO"))

    return {
        "metrica": label,
        "n_repos": n,
        "mediana_rest": rest_vals.median(),
        "mediana_graphql": graphql_vals.median(),
        "diferenca_pct": pct_diff,
        "teste": test_name,
        "estatistica": stat,
        "p_valor": p_value,
        "shapiro_p": shapiro_p,
    }


def plot_boxplot(df, metric, ylabel, title, out_path, log_scale=False):
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.boxplot(data=df, x="treatment", y=metric, hue="treatment", legend=False, ax=ax)
    if log_scale:
        ax.set_yscale("log")
        ylabel = f"{ylabel} (escala log)"
    ax.set_title(title)
    ax.set_xlabel("Tratamento")
    ax.set_ylabel(ylabel)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico salvo em {out_path}")


def plot_paired_repo_medians(wide, ylabel, title, out_path, log_scale=False):
    fig, ax = plt.subplots(figsize=(6, 5))
    melted = wide.reset_index().melt(id_vars="repo", value_vars=["REST", "GraphQL"], var_name="treatment", value_name="valor")
    sns.boxplot(data=melted, x="treatment", y="valor", hue="treatment", legend=False, ax=ax)
    sns.stripplot(data=melted, x="treatment", y="valor", color="black", alpha=0.4, size=3, ax=ax)
    if log_scale:
        ax.set_yscale("log")
        ylabel = f"{ylabel} (escala log)"
    ax.set_title(title)
    ax.set_xlabel("Tratamento")
    ax.set_ylabel(ylabel)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico salvo em {out_path}")


def plot_median_bar(wide, ylabel, title, out_path, log_scale=False):
    treatments = ["REST", "GraphQL"]
    medians = wide.median()
    q1, q3 = wide.quantile(0.25), wide.quantile(0.75)
    err_low = [medians[t] - q1[t] for t in treatments]
    err_high = [q3[t] - medians[t] for t in treatments]

    fig, ax = plt.subplots(figsize=(6, 5))
    colors = sns.color_palette()[:2]
    bars = ax.bar(treatments, [medians[t] for t in treatments], color=colors,
                   yerr=[err_low, err_high], capsize=8, width=0.5)
    for bar, t in zip(bars, treatments):
        ax.annotate(f"{medians[t]:,.0f}", (bar.get_x() + bar.get_width() / 2, medians[t]),
                    ha="center", va="bottom", xytext=(0, 6), textcoords="offset points")
    if log_scale:
        ax.set_yscale("log")
        ylabel = f"{ylabel} (escala log)"
    ax.set_title(title)
    ax.set_xlabel("Tratamento")
    ax.set_ylabel(ylabel)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico salvo em {out_path}")


def plot_slopegraph(wide, ylabel, title, out_path, log_scale=False):
    fig, ax = plt.subplots(figsize=(5.5, 6))
    for _, row in wide.iterrows():
        color = "tab:red" if row["GraphQL"] < row["REST"] else "tab:blue"
        ax.plot([0, 1], [row["REST"], row["GraphQL"]], color=color, alpha=0.25, linewidth=1, zorder=1)
    ax.scatter([0] * len(wide), wide["REST"], color="tab:blue", s=18, zorder=2, label="REST")
    ax.scatter([1] * len(wide), wide["GraphQL"], color="tab:orange", s=18, zorder=2, label="GraphQL")

    pct_menor = 100 * (wide["GraphQL"] < wide["REST"]).mean()

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["REST", "GraphQL"])
    ax.set_xlim(-0.3, 1.3)
    if log_scale:
        ax.set_yscale("log")
        ylabel = f"{ylabel} (escala log)"
    ax.set_title(f"{title}\nGraphQL menor em {pct_menor:.0f}% dos repositórios", fontsize=11)
    ax.set_ylabel(ylabel)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico salvo em {out_path}")


def plot_diff_histogram(wide, unit, title, out_path):
    diff = wide["REST"] - wide["GraphQL"]
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.histplot(diff, kde=True, ax=ax, color="tab:purple")
    ax.axvline(0, color="black", linestyle="--", linewidth=1, label="H0: diferença = 0")
    ax.axvline(diff.median(), color="tab:red", linestyle="-", linewidth=1, label=f"Mediana = {diff.median():,.0f}")
    ax.legend(fontsize=8)
    ax.set_title(title)
    ax.set_xlabel(f"Diferença REST - GraphQL ({unit})")
    ax.set_ylabel("Nº de repositórios")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfico salvo em {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Analisa os resultados do experimento REST vs GraphQL")
    parser.add_argument("--input", default="../data/resultados_brutos.csv")
    parser.add_argument("--imgs", default="../imgs")
    parser.add_argument("--summary-output", default="../data/resumo_estatistico.csv")
    args = parser.parse_args()

    sns.set_theme(style="whitegrid")
    os.makedirs(args.imgs, exist_ok=True)

    df = load_data(args.input)

    print(f"Total de medições válidas: {len(df)}")
    print(df.groupby("treatment")[["elapsed_ms", "size_bytes"]].describe().T)

    wide_time = aggregate_by_repo(df, "elapsed_ms")
    wide_size = aggregate_by_repo(df, "size_bytes")

    results = [
        run_paired_test(wide_time, "RQ1 - Tempo de resposta (ms)", "ms"),
        run_paired_test(wide_size, "RQ2 - Tamanho da resposta (bytes)", "bytes"),
    ]

    plot_boxplot(df, "elapsed_ms", "Tempo (ms)", "RQ1 - Tempo de resposta por tratamento (todas as repetições)",
                 os.path.join(args.imgs, "rq1_tempo_boxplot_bruto.png"))
    plot_boxplot(df, "size_bytes", "Tamanho (bytes)", "RQ2 - Tamanho da resposta por tratamento (todas as repetições)",
                 os.path.join(args.imgs, "rq2_tamanho_boxplot_bruto.png"), log_scale=True)
    plot_paired_repo_medians(wide_time, "Tempo (ms)", "RQ1 - Mediana de tempo por repositório (pareado)",
                              os.path.join(args.imgs, "rq1_tempo_pareado.png"))
    plot_paired_repo_medians(wide_size, "Tamanho (bytes)", "RQ2 - Mediana de tamanho por repositório (pareado)",
                              os.path.join(args.imgs, "rq2_tamanho_pareado.png"), log_scale=True)

    plot_median_bar(wide_time, "Tempo (ms)", "RQ1 - Mediana e IQR de tempo por tratamento",
                     os.path.join(args.imgs, "rq1_tempo_barras.png"))
    plot_median_bar(wide_size, "Tamanho (bytes)", "RQ2 - Mediana e IQR de tamanho por tratamento",
                     os.path.join(args.imgs, "rq2_tamanho_barras.png"), log_scale=True)

    plot_slopegraph(wide_time, "Tempo (ms)", "RQ1 - Tempo por repositório: REST -> GraphQL",
                     os.path.join(args.imgs, "rq1_tempo_slope.png"))
    plot_slopegraph(wide_size, "Tamanho (bytes)", "RQ2 - Tamanho por repositório: REST -> GraphQL",
                     os.path.join(args.imgs, "rq2_tamanho_slope.png"), log_scale=True)

    plot_diff_histogram(wide_time, "ms", "RQ1 - Distribuição da diferença pareada (REST - GraphQL)",
                         os.path.join(args.imgs, "rq1_tempo_diferenca.png"))
    plot_diff_histogram(wide_size, "bytes", "RQ2 - Distribuição da diferença pareada (REST - GraphQL)",
                         os.path.join(args.imgs, "rq2_tamanho_diferenca.png"))

    pd.DataFrame(results).to_csv(args.summary_output, index=False)
    print(f"\nResumo estatístico salvo em {args.summary_output}")


if __name__ == "__main__":
    main()
