import argparse
import csv
import os
import random
import time
from datetime import datetime, timezone

from github_utils import graphql_fetch_repo, rest_fetch_repo, validate_token

FIELDNAMES = [
    "repo", "owner", "name", "treatment", "repetition", "order_index",
    "timestamp", "status_code", "ok", "elapsed_ms", "size_bytes", "error",
]


def load_repos(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_plan(repos, repetitions):
    plan = [
        (repo, treatment, rep)
        for repo in repos
        for rep in range(1, repetitions + 1)
        for treatment in ("REST", "GraphQL")
    ]
    random.shuffle(plan)
    return plan


def run(repos_path, output_path, repetitions, delay_min, delay_max):
    if not validate_token():
        raise SystemExit(
            "Token do GitHub inválido ou ausente. Defina a variável de ambiente "
            "GITHUB_TOKEN ou edite GITHUB_TOKEN em github_utils.py."
        )

    repos = load_repos(repos_path)
    if not repos:
        raise SystemExit(f"Nenhum repositório encontrado em {repos_path}. Rode select_repos.py primeiro.")

    plan = build_plan(repos, repetitions)
    total = len(plan)

    rest_fetch_repo(repos[0]["owner"], repos[0]["name"])
    graphql_fetch_repo(repos[0]["owner"], repos[0]["name"])

    write_header = not os.path.exists(output_path)
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()

        for idx, (repo, treatment, rep) in enumerate(plan, start=1):
            owner, name = repo["owner"], repo["name"]
            result = rest_fetch_repo(owner, name) if treatment == "REST" else graphql_fetch_repo(owner, name)

            writer.writerow({
                "repo": f"{owner}/{name}",
                "owner": owner,
                "name": name,
                "treatment": treatment,
                "repetition": rep,
                "order_index": idx,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status_code": result["status_code"],
                "ok": result["ok"],
                "elapsed_ms": result["elapsed_ms"],
                "size_bytes": result["size_bytes"],
                "error": result["error"],
            })
            f.flush()

            if idx % 50 == 0 or idx == total:
                print(f"{idx}/{total} medições concluídas")

            time.sleep(random.uniform(delay_min, delay_max))

    print(f"Experimento concluído: {total} medições salvas em {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Executa o experimento controlado REST vs GraphQL")
    parser.add_argument("--repos", default="../data/repos_amostra.csv")
    parser.add_argument("--output", default="../data/resultados_brutos.csv")
    parser.add_argument("--repetitions", type=int, default=5, help="Repetições por tratamento por repositório (K)")
    parser.add_argument("--delay-min", type=float, default=0.2, help="Delay mínimo (s) entre requisições")
    parser.add_argument("--delay-max", type=float, default=0.5, help="Delay máximo (s) entre requisições")
    args = parser.parse_args()
    run(args.repos, args.output, args.repetitions, args.delay_min, args.delay_max)


if __name__ == "__main__":
    main()
