import argparse
import csv
import os

from github_utils import select_top_repos


def main():
    parser = argparse.ArgumentParser(description="Seleciona amostra de repositórios populares do GitHub")
    parser.add_argument("--target", type=int, default=100, help="Quantidade de repositórios na amostra")
    parser.add_argument("--output", default="../data/repos_amostra.csv")
    args = parser.parse_args()

    repos = select_top_repos(target=args.target)

    output_path = os.path.normpath(args.output)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["owner", "name", "stars"])
        writer.writeheader()
        writer.writerows(repos)

    print(f"{len(repos)} repositórios salvos em {output_path}")


if __name__ == "__main__":
    main()
