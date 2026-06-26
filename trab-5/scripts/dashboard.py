import argparse
import os

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

COLUMN_WIDTH = 750
COLUMN_HEIGHT = 640
ROW_LABEL_HEIGHT = 60
GUTTER = 30
MARGIN = 50

RQ1_IMAGES = [
    ("rq1_tempo_boxplot_bruto.png", "Boxplot bruto (500 medições)"),
    ("rq1_tempo_pareado.png", "Boxplot pareado (100 repos)"),
    ("rq1_tempo_barras.png", "Mediana e IQR"),
    ("rq1_tempo_slope.png", "Slopegraph pareado"),
    ("rq1_tempo_diferenca.png", "Diferença pareada"),
]

RQ2_IMAGES = [
    ("rq2_tamanho_boxplot_bruto.png", "Boxplot bruto (500 medições)"),
    ("rq2_tamanho_pareado.png", "Boxplot pareado (100 repos)"),
    ("rq2_tamanho_barras.png", "Mediana e IQR"),
    ("rq2_tamanho_slope.png", "Slopegraph pareado"),
    ("rq2_tamanho_diferenca.png", "Diferença pareada"),
]


def load_font(bold, size):
    names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    dirs = ["C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/msttcorefonts"]
    for d in dirs:
        for n in names:
            path = os.path.join(d, n)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fmt_pt(value, decimals=0):
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_p(value):
    if value < 0.0001:
        return "p < 0,0001"
    return f"p = {fmt_pt(value, 5)}"


def load_kpis(data_dir):
    raw = pd.read_csv(os.path.join(data_dir, "resultados_brutos.csv"))
    summary = pd.read_csv(os.path.join(data_dir, "resumo_estatistico.csv"))
    rq1 = summary[summary["metrica"].str.startswith("RQ1")].iloc[0]
    rq2 = summary[summary["metrica"].str.startswith("RQ2")].iloc[0]
    timestamps = pd.to_datetime(raw["timestamp"])
    return {
        "n_repos": raw["repo"].nunique(),
        "n_medicoes": len(raw),
        "n_rest": int((raw["treatment"] == "REST").sum()),
        "n_graphql": int((raw["treatment"] == "GraphQL").sum()),
        "data_inicio": timestamps.min(),
        "data_fim": timestamps.max(),
        "rq1": rq1,
        "rq2": rq2,
    }


def draw_card(draw, xy, size, title, lines, fill, font_title, font_body):
    x, y = xy
    w, h = size
    draw.rounded_rectangle([x, y, x + w, y + h], radius=16, fill=fill, outline=(205, 205, 205), width=2)
    draw.text((x + 22, y + 20), title, font=font_title, fill=(25, 25, 25))
    for i, line in enumerate(lines):
        draw.text((x + 22, y + 68 + i * 36), line, font=font_body, fill=(55, 55, 55))


def paste_row(canvas, draw, images_dir, images, y, font_label):
    x = MARGIN
    for filename, label in images:
        img = Image.open(os.path.join(images_dir, filename))
        available_h = COLUMN_HEIGHT - ROW_LABEL_HEIGHT
        scale = min(COLUMN_WIDTH / img.width, available_h / img.height)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
        offset_x = x + (COLUMN_WIDTH - new_size[0]) // 2
        offset_y = y + ROW_LABEL_HEIGHT + (available_h - new_size[1]) // 2
        canvas.paste(img, (offset_x, offset_y))
        bbox = draw.textbbox((0, 0), label, font=font_label)
        text_w = bbox[2] - bbox[0]
        draw.text((x + (COLUMN_WIDTH - text_w) // 2, y + 14), label, font=font_label, fill=(70, 70, 70))
        x += COLUMN_WIDTH + GUTTER


def rq_card_lines(row, metric_unit, faster_smaller_word, slower_bigger_word):
    diff = row["diferenca_pct"]
    direction = faster_smaller_word if diff > 0 else slower_bigger_word
    return [
        f"REST: {fmt_pt(row['mediana_rest'], 1)} {metric_unit}    GraphQL: {fmt_pt(row['mediana_graphql'], 1)} {metric_unit}",
        f"GraphQL {abs(diff):.1f}% {direction} (mediana)",
        f"{row['teste']}, {fmt_p(row['p_valor'])}",
    ]


def build_dashboard(data_dir, images_dir, output_path):
    kpis = load_kpis(data_dir)

    width = MARGIN * 2 + len(RQ1_IMAGES) * COLUMN_WIDTH + (len(RQ1_IMAGES) - 1) * GUTTER
    canvas = Image.new("RGB", (width, 2600), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    font_h1 = load_font(True, 46)
    font_h2 = load_font(False, 24)
    font_section = load_font(True, 30)
    font_card_title = load_font(True, 22)
    font_card_body = load_font(False, 20)
    font_label = load_font(False, 20)
    font_footer = load_font(False, 18)

    y = MARGIN
    draw.text((MARGIN, y), "Dashboard: GraphQL vs REST, Um Experimento Controlado", font=font_h1, fill=(20, 20, 20))
    y += 58
    subtitle = (
        f"GitHub REST API v3 vs GraphQL API v4 | {kpis['n_repos']} repositórios | "
        f"{fmt_pt(kpis['n_medicoes'], 0)} medições ({kpis['n_rest']} REST + {kpis['n_graphql']} GraphQL) | "
        f"Coleta: {kpis['data_inicio']:%d/%m/%Y %H:%M} a {kpis['data_fim']:%H:%M} UTC"
    )
    draw.text((MARGIN, y), subtitle, font=font_h2, fill=(90, 90, 90))
    y += 52

    card_w = (width - MARGIN * 2 - GUTTER * 3) // 4
    card_h = 180
    card_fill = (245, 247, 250)

    draw_card(
        draw, (MARGIN, y), (card_w, card_h), "Objetos experimentais",
        [f"{kpis['n_repos']} repositórios públicos", "selecionados por número de estrelas", "K = 5 repetições por tratamento"],
        card_fill, font_card_title, font_card_body,
    )
    draw_card(
        draw, (MARGIN + card_w + GUTTER, y), (card_w, card_h), "Medições coletadas",
        [f"{fmt_pt(kpis['n_medicoes'], 0)} medições totais", f"{kpis['n_rest']} REST + {kpis['n_graphql']} GraphQL", "0 falhas/timeouts"],
        card_fill, font_card_title, font_card_body,
    )
    draw_card(
        draw, (MARGIN + 2 * (card_w + GUTTER), y), (card_w, card_h), "RQ1: Tempo de resposta",
        rq_card_lines(kpis["rq1"], "ms", "mais rápido", "mais lento"),
        (250, 244, 237), font_card_title, font_card_body,
    )
    draw_card(
        draw, (MARGIN + 3 * (card_w + GUTTER), y), (card_w, card_h), "RQ2: Tamanho da resposta",
        rq_card_lines(kpis["rq2"], "bytes", "menor", "maior"),
        (237, 244, 250), font_card_title, font_card_body,
    )
    y += card_h + 40

    draw.text((MARGIN, y), "RQ1: Respostas GraphQL são mais rápidas que REST?", font=font_section, fill=(30, 30, 30))
    y += 50
    paste_row(canvas, draw, images_dir, RQ1_IMAGES, y, font_label)
    y += COLUMN_HEIGHT + 40

    draw.text((MARGIN, y), "RQ2: Respostas GraphQL têm tamanho menor que REST?", font=font_section, fill=(30, 30, 30))
    y += 50
    paste_row(canvas, draw, images_dir, RQ2_IMAGES, y, font_label)
    y += COLUMN_HEIGHT + 30

    draw.line([(MARGIN, y), (width - MARGIN, y)], fill=(220, 220, 220), width=2)
    y += 16
    draw.text(
        (MARGIN, y),
        "Trab-5, Experimentação de Software, PUCMINAS 01/2026. Dados em data/resultados_brutos.csv, gráficos individuais em imgs/.",
        font=font_footer, fill=(120, 120, 120),
    )
    y += 34

    final = canvas.crop((0, 0, width, y + MARGIN))
    final.save(output_path)
    print(f"Dashboard salvo em {output_path} ({final.width}x{final.height}px)")


def main():
    parser = argparse.ArgumentParser(description="Monta o dashboard final (Lab05S03) a partir dos gráficos e dados já gerados")
    parser.add_argument("--data", default="../data")
    parser.add_argument("--imgs", default="../imgs")
    parser.add_argument("--output", default="../imgs/dashboard.png")
    args = parser.parse_args()
    build_dashboard(args.data, args.imgs, args.output)


if __name__ == "__main__":
    main()
