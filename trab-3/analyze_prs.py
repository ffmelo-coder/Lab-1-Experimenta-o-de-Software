import os
import csv
import math
import statistics as _st
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import Counter

try:
    import matplotlib

    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import numpy as np

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from scipy.stats import spearmanr

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PRS_CSV = os.path.join(_DIR, "prs_coletados.csv")

C_MERGED = "#2E7D32"
C_CLOSED = "#C62828"
PALETTE = [
    "#1565C0",
    "#E65100",
    "#6A1B9A",
    "#00695C",
    "#F57F17",
    "#AD1457",
    "#283593",
    "#00838F",
]

_NUMERIC_FIELDS = {
    "pr_number",
    "time_to_close_hours",
    "changed_files",
    "additions",
    "deletions",
    "total_changes",
    "body_length",
    "reviews_count",
    "participants_count",
    "comments_count",
}


def load_prs_csv(path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for raw in csv.DictReader(f):
            row = {}
            for k, v in raw.items():
                k = k.strip()
                v = (v or "").strip()
                if k in _NUMERIC_FIELDS:
                    try:
                        row[k] = float(v) if v else None
                    except Exception:
                        row[k] = None
                else:
                    row[k] = v
            rows.append(row)
    return rows


def safe_median(vals):
    v = [x for x in vals if x is not None]
    return _st.median(v) if v else 0.0


def spearman_corr(xs, ys):
    if SCIPY_AVAILABLE:
        try:
            r, p = spearmanr(xs, ys)
            return float(r), float(p)
        except Exception:
            return float("nan"), float("nan")
    n = len(xs)
    if n < 3:
        return float("nan"), float("nan")

    def ranks(lst):
        sp = sorted(enumerate(lst), key=lambda x: x[1])
        r = [0.0] * n
        for rv, (oi, _) in enumerate(sp, 1):
            r[oi] = float(rv)
        return r

    d2 = sum((a - b) ** 2 for a, b in zip(ranks(xs), ranks(ys)))
    return 1 - (6 * d2) / (n * (n**2 - 1)), float("nan")


def pct99(vals):
    """Retorna (lista_capeada, valor_do_cap) no percentil 99."""
    if not vals or not MATPLOTLIB_AVAILABLE:
        return list(vals), max(vals) if vals else 1.0
    cap = float(np.percentile(vals, 99))
    return [min(v, cap) for v in vals], cap


class PRAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Análise de Code Review — Pull Requests GitHub")
        self.root.geometry("1280x760")
        self.root.resizable(True, True)

        self.all_rows = []
        self.filtered_rows = None
        self.current_page = 0
        self.items_per_page = 20
        self.page_input = tk.StringVar(value="1")
        self.filter_visible = False
        self.prs_path = tk.StringVar(value=DEFAULT_PRS_CSV)

        self._setup_ui()
        self._try_autoload()

    def _try_autoload(self):
        if os.path.exists(DEFAULT_PRS_CSV):
            self._load_csv(DEFAULT_PRS_CSV)

    def _setup_ui(self):
        top = ttk.Frame(self.root, padding="8")
        top.pack(fill=tk.X)

        ttk.Label(top, text="Arquivo PRs:", font=("Arial", 10, "bold")).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Entry(top, textvariable=self.prs_path, width=54).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(top, text="…", width=2, command=self._browse).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(top, text="📂 Carregar", command=self._load_from_entry).pack(
            side=tk.LEFT, padx=4
        )

        self._prog_frame = ttk.Frame(self.root, padding="6 4")
        self._prog_frame.pack(fill=tk.X)

        for text, attr, fg in [
            ("Total PRs:", "_lbl_total", "blue"),
            ("MERGED:", "_lbl_merged", C_MERGED),
            ("CLOSED:", "_lbl_closed", C_CLOSED),
        ]:
            ttk.Label(self._prog_frame, text=text, font=("Arial", 9)).pack(
                side=tk.LEFT, padx=(0, 2)
            )
            lbl = ttk.Label(
                self._prog_frame, text="0", font=("Arial", 9, "bold"), foreground=fg
            )
            lbl.pack(side=tk.LEFT, padx=(0, 14))
            setattr(self, attr, lbl)

        self.btn_graphs = ttk.Button(
            self._prog_frame,
            text="📊 Ver Gráficos",
            command=self._open_graphs,
            state=tk.DISABLED,
        )
        self.btn_graphs.pack(side=tk.LEFT, padx=8)

        self.btn_filter = ttk.Button(
            self._prog_frame,
            text="🔍 Filtros",
            command=self._toggle_filters,
            state=tk.DISABLED,
        )
        self.btn_filter.pack(side=tk.LEFT, padx=4)

        self.status_label = ttk.Label(
            self._prog_frame,
            text="Nenhum dado carregado",
            font=("Arial", 9),
            foreground="gray",
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

        self.filter_frame = ttk.LabelFrame(self.root, text="Filtros", padding="8")
        fr = ttk.Frame(self.filter_frame)
        fr.pack(fill=tk.X, pady=2)

        ttk.Label(fr, text="Estado:").pack(side=tk.LEFT)
        self.f_state = tk.StringVar(value="Todos")
        ttk.Combobox(
            fr,
            textvariable=self.f_state,
            values=["Todos", "MERGED", "CLOSED"],
            width=9,
            state="readonly",
        ).pack(side=tk.LEFT, padx=(2, 10))

        ttk.Label(fr, text="Repo:").pack(side=tk.LEFT)
        self.f_repo = tk.StringVar()
        ttk.Entry(fr, textvariable=self.f_repo, width=22).pack(
            side=tk.LEFT, padx=(2, 10)
        )

        ttk.Label(fr, text="Reviews ≥:").pack(side=tk.LEFT)
        self.f_rev_min = tk.StringVar()
        ttk.Entry(fr, textvariable=self.f_rev_min, width=5).pack(
            side=tk.LEFT, padx=(2, 10)
        )

        ttk.Label(fr, text="Tempo (h):").pack(side=tk.LEFT)
        self.f_t_min = tk.StringVar()
        self.f_t_max = tk.StringVar()
        ttk.Entry(fr, textvariable=self.f_t_min, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(fr, text="–").pack(side=tk.LEFT)
        ttk.Entry(fr, textvariable=self.f_t_max, width=7).pack(
            side=tk.LEFT, padx=(2, 10)
        )

        ttk.Button(fr, text="✔ Aplicar", command=self._apply_filters).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(fr, text="✖ Limpar", command=self._clear_filters).pack(side=tk.LEFT)

        self.filter_status = ttk.Label(
            self.filter_frame,
            text="",
            font=("Arial", 9, "italic"),
            foreground="gray",
        )
        self.filter_status.pack(anchor=tk.W)

        tbl = ttk.Frame(self.root, padding="8 4")
        tbl.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(tbl)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = ttk.Scrollbar(tbl, orient=tk.HORIZONTAL)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        cols = (
            "#",
            "Repositório",
            "PR",
            "Estado",
            "Tempo (h)",
            "Arquivos",
            "Adições",
            "Remoções",
            "Corpo (chars)",
            "Reviews",
            "Partic.",
            "Coments.",
        )
        self.tree = ttk.Treeview(
            tbl,
            columns=cols,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=18,
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        widths = [40, 260, 50, 80, 90, 70, 70, 70, 90, 70, 60, 70]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(
                col,
                width=w,
                anchor=tk.W if col == "Repositório" else tk.CENTER,
            )
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.tag_configure("merged", foreground="#1B5E20")
        self.tree.tag_configure("closed", foreground="#B71C1C")

        nav = ttk.Frame(self.root, padding="8 4")
        nav.pack(fill=tk.X)

        self.btn_prev = ttk.Button(
            nav,
            text="◀ Anterior",
            command=self._prev_page,
            state=tk.DISABLED,
        )
        self.btn_prev.pack(side=tk.LEFT, padx=4)

        ttk.Label(nav, text="Página").pack(side=tk.LEFT, padx=(14, 4))
        pe = ttk.Entry(nav, textvariable=self.page_input, width=5, justify=tk.CENTER)
        pe.pack(side=tk.LEFT)
        pe.bind("<Return>", self._goto_page)
        self.page_total_label = ttk.Label(nav, text="de 0", font=("Arial", 9, "bold"))
        self.page_total_label.pack(side=tk.LEFT, padx=(4, 14))

        self.btn_next = ttk.Button(
            nav,
            text="Próxima ▶",
            command=self._next_page,
            state=tk.DISABLED,
        )
        self.btn_next.pack(side=tk.LEFT)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Selecionar CSV de PRs",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
            initialdir=_DIR,
        )
        if path:
            self.prs_path.set(path)
            self._load_csv(path)

    def _load_from_entry(self):
        self._load_csv(self.prs_path.get().strip())

    def _load_csv(self, path):
        if not os.path.exists(path):
            messagebox.showerror("Erro", f"Arquivo não encontrado:\n{path}")
            return
        try:
            self.all_rows = load_prs_csv(path)
            self.filtered_rows = None
            self.current_page = 0
            self._update_counts(self.all_rows)
            self._refresh_table()
            state = tk.NORMAL if self.all_rows else tk.DISABLED
            self.btn_graphs.config(
                state=state if MATPLOTLIB_AVAILABLE else tk.DISABLED,
            )
            self.btn_filter.config(state=state)
            self.btn_prev.config(state=tk.DISABLED)
            self.status_label.config(
                text=f"✓ {len(self.all_rows)} PRs carregados de {os.path.basename(path)}",
                foreground="green",
            )
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao carregar CSV:\n{exc}")
            self.status_label.config(text=f"Erro: {exc}", foreground="red")

    def _update_counts(self, rows):
        total = len(rows)
        merged = sum(1 for r in rows if r.get("state") == "MERGED")
        self._lbl_total.config(text=str(total))
        self._lbl_merged.config(text=str(merged))
        self._lbl_closed.config(text=str(total - merged))

    def _active_rows(self):
        return self.filtered_rows if self.filtered_rows is not None else self.all_rows

    @staticmethod
    def _sf(s, default):
        try:
            return float(s.strip())
        except Exception:
            return default

    def _apply_filters(self):
        if not self.all_rows:
            return
        state_f = self.f_state.get()
        repo_f = self.f_repo.get().strip().lower()
        rev_min = self._sf(self.f_rev_min.get(), 0)
        t_min = self._sf(self.f_t_min.get(), 0)
        t_max = self._sf(self.f_t_max.get(), float("inf"))

        result = [
            r
            for r in self.all_rows
            if (state_f == "Todos" or r.get("state") == state_f)
            and (not repo_f or repo_f in (r.get("repo") or "").lower())
            and (r.get("reviews_count") or 0) >= rev_min
            and t_min <= (r.get("time_to_close_hours") or 0) <= t_max
        ]
        self.filtered_rows = result
        self.current_page = 0
        self._refresh_table()
        self.filter_status.config(
            text=f"Filtros ativos: {len(result)} de {len(self.all_rows)} PRs",
            foreground="green" if len(result) == len(self.all_rows) else "orange",
        )

    def _clear_filters(self):
        for v in (self.f_repo, self.f_rev_min, self.f_t_min, self.f_t_max):
            v.set("")
        self.f_state.set("Todos")
        self.filtered_rows = None
        self.current_page = 0
        self.filter_status.config(text="")
        self._refresh_table()

    def _toggle_filters(self):
        if self.filter_visible:
            self.filter_frame.pack_forget()
            self.filter_visible = False
            self.btn_filter.config(text="🔍 Filtros")
        else:
            self.filter_frame.pack(
                fill=tk.X,
                padx=8,
                pady=(0, 4),
                after=self._prog_frame,
            )
            self.filter_visible = True
            self.btn_filter.config(text="🔍 Fechar Filtros")

    def _refresh_table(self):
        rows = self._active_rows()
        total_pages = max(
            1, (len(rows) + self.items_per_page - 1) // self.items_per_page
        )
        self.current_page = min(self.current_page, total_pages - 1)
        start = self.current_page * self.items_per_page

        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows[start : start + self.items_per_page], start + 1):
            state = r.get("state", "")
            t = r.get("time_to_close_hours")
            self.tree.insert(
                "",
                tk.END,
                tags=(state.lower(),),
                values=(
                    i,
                    r.get("repo", ""),
                    int(r.get("pr_number") or 0),
                    state,
                    f"{t:.1f}" if t is not None else "—",
                    int(r.get("changed_files") or 0),
                    int(r.get("additions") or 0),
                    int(r.get("deletions") or 0),
                    int(r.get("body_length") or 0),
                    int(r.get("reviews_count") or 0),
                    int(r.get("participants_count") or 0),
                    int(r.get("comments_count") or 0),
                ),
            )

        self.page_input.set(str(self.current_page + 1))
        self.page_total_label.config(text=f"de {total_pages}")
        self.btn_prev.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.btn_next.config(
            state=tk.NORMAL if self.current_page < total_pages - 1 else tk.DISABLED,
        )

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_table()

    def _next_page(self):
        rows = self._active_rows()
        total_pages = max(
            1, (len(rows) + self.items_per_page - 1) // self.items_per_page
        )
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._refresh_table()

    def _goto_page(self, _=None):
        try:
            p = int(self.page_input.get())
            rows = self._active_rows()
            total_pages = max(
                1, (len(rows) + self.items_per_page - 1) // self.items_per_page
            )
            self.current_page = max(0, min(p - 1, total_pages - 1))
            self._refresh_table()
        except ValueError:
            pass

    def _open_graphs(self):
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showwarning(
                "Dependência ausente",
                "matplotlib não instalado.\n\npip install matplotlib",
            )
            return
        rows = self._active_rows()
        if not rows:
            messagebox.showinfo("Aviso", "Nenhum dado para gráficos.")
            return
        GraphsWindow(self.root, rows)


class GraphsWindow(tk.Toplevel):
    def __init__(self, parent, rows):
        super().__init__(parent)
        self.title(f"Análise de Code Review — {len(rows):,} PRs")
        self.geometry("1200x760")
        self.resizable(True, True)
        self.rows = rows
        self._merged = [r for r in rows if r.get("state") == "MERGED"]
        self._closed = [r for r in rows if r.get("state") == "CLOSED"]
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        plt.close("all")
        self.destroy()

    def _vals(self, key, state=None):
        src = (
            self._merged
            if state == "MERGED"
            else self._closed if state == "CLOSED" else self.rows
        )
        return [float(r[key]) for r in src if r.get(key) is not None]

    def _paired(self, xkey, ykey, state=None):
        src = (
            self._merged
            if state == "MERGED"
            else self._closed if state == "CLOSED" else self.rows
        )
        pairs = [
            (float(r[xkey]), float(r[ykey]))
            for r in src
            if r.get(xkey) is not None and r.get(ykey) is not None
        ]
        if not pairs:
            return [], []
        xs, ys = zip(*pairs)
        return list(xs), list(ys)

    def _embed(self, fig, parent):
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        plt.close(fig)

    @staticmethod
    def _bar_labels(ax, bars, fmt="{:,.1f}"):
        ylim = ax.get_ylim()[1]
        for bar in bars:
            h = bar.get_height()
            offset = max(h * 0.02, ylim * 0.01)
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                h + offset,
                fmt.format(h),
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    @staticmethod
    def _clean(ax):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        for label, builder in [
            ("Visão Geral", self._tab_overview),
            ("RQ01 – Tamanho/Estado", self._tab_rq01),
            ("RQ01 – Médias/Estado", self._tab_rq01_mean),
            ("RQ02 – Tempo/Estado", self._tab_rq02),
            ("RQ02 – ZoomIn", self._tab_rq02_zoom),
            ("RQ03 – Descrição/Estado", self._tab_rq03),
            ("RQ04 – Interações/Estado", self._tab_rq04),
            ("RQ05 – Tamanho/Revisões", self._tab_rq05),
            ("RQ06 – Tempo/Revisões", self._tab_rq06),
            ("RQ06 – ZoomOut", self._tab_rq06_zoom),
            ("RQ07 – Descrição/Revisões", self._tab_rq07),
            ("RQ08 – Interações/Revisões", self._tab_rq08),
            ("Taxa de Merge", self._tab_merge_rate),
            ("Resumo Estatístico", self._tab_summary),
        ]:
            frame = ttk.Frame(nb)
            nb.add(frame, text=label)
            try:
                builder(frame)
            except Exception as exc:
                ttk.Label(
                    frame,
                    text=f"Erro ao gerar gráfico:\n{exc}",
                    font=("Arial", 10),
                    foreground="red",
                ).pack(expand=True)

    def _tab_overview(self, parent):
        n_m = len(self._merged)
        n_c = len(self._closed)
        total = n_m + n_c
        if total == 0:
            ttk.Label(parent, text="Sem dados.", font=("Arial", 11)).pack(expand=True)
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle(
            "Visão Geral — Distribuição dos PRs", fontsize=13, fontweight="bold"
        )

        wedges, texts, autotexts = ax1.pie(
            [n_m, n_c],
            labels=["MERGED", "CLOSED"],
            colors=[C_MERGED, C_CLOSED],
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.75,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )
        for at in autotexts:
            at.set_fontsize(11)
            at.set_fontweight("bold")
            at.set_color("white")
        ax1.set_title(f"MERGED vs CLOSED  (total = {total:,})", fontsize=11, pad=14)
        ax1.legend(
            wedges,
            [
                f"MERGED — {n_m:,} ({n_m/total*100:.1f}%)",
                f"CLOSED — {n_c:,} ({n_c/total*100:.1f}%)",
            ],
            loc="lower center",
            bbox_to_anchor=(0.5, -0.12),
            fontsize=9,
        )

        repo_counts = Counter(r.get("repo", "") for r in self.rows)
        top10 = repo_counts.most_common(10)
        labels_r = [t[0].split("/")[-1] for t in top10]
        values_r = [t[1] for t in top10]
        colors_r = PALETTE[: len(top10)]

        bars = ax2.barh(
            labels_r[::-1],
            values_r[::-1],
            color=colors_r[::-1],
            edgecolor="white",
        )
        max_v = max(values_r) if values_r else 1
        for bar, val in zip(bars, values_r[::-1]):
            ax2.text(
                bar.get_width() + max_v * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(val),
                va="center",
                fontsize=8,
                fontweight="bold",
            )
        ax2.set_title("Top 10 Repositórios por Nº de PRs", fontsize=11)
        ax2.set_xlabel("Número de PRs", fontsize=9)
        ax2.set_xlim(right=max_v * 1.15)
        self._clean(ax2)

        fig.tight_layout(rect=[0, 0, 1, 0.95])
        self._embed(fig, parent)

    def _tab_rq01(self, parent):
        metrics = [
            ("changed_files", "Arquivos Modificados"),
            ("additions", "Adições (linhas)"),
            ("deletions", "Remoções (linhas)"),
            ("total_changes", "Total de Mudanças"),
        ]
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(
            "RQ01 – Tamanho dos PRs vs Feedback Final\n"
            "Mediana por estado (MERGED vs CLOSED)",
            fontsize=12,
            fontweight="bold",
        )
        for ax, (key, label) in zip(axes.flat, metrics):
            m_med = safe_median(self._vals(key, "MERGED"))
            c_med = safe_median(self._vals(key, "CLOSED"))
            top = max(m_med, c_med) * 1.3 or 1.0
            bars = ax.bar(
                ["MERGED", "CLOSED"],
                [m_med, c_med],
                color=[C_MERGED, C_CLOSED],
                width=0.5,
                edgecolor="white",
                linewidth=1.2,
            )
            ax.set_title(f"Mediana — {label}", fontsize=10, pad=8)
            ax.set_ylabel(label, fontsize=9)
            ax.set_ylim(bottom=0, top=top)
            self._bar_labels(ax, bars, "{:,.1f}")
            self._clean(ax)

        fig.tight_layout(rect=[0, 0, 1, 0.93])
        self._embed(fig, parent)

    def _tab_rq01_mean(self, parent):
        metrics = [
            ("changed_files", "Arquivos Modificados"),
            ("additions", "Adições (linhas)"),
            ("deletions", "Remoções (linhas)"),
            ("total_changes", "Total de Mudanças"),
        ]
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(
            "RQ01 – Tamanho dos PRs vs Feedback Final\n"
            "Média por estado (MERGED vs CLOSED)",
            fontsize=12,
            fontweight="bold",
        )
        for ax, (key, label) in zip(axes.flat, metrics):
            m_vals = self._vals(key, "MERGED")
            c_vals = self._vals(key, "CLOSED")
            m_mean = _st.mean(m_vals) if m_vals else 0.0
            c_mean = _st.mean(c_vals) if c_vals else 0.0
            top = max(m_mean, c_mean) * 1.3 or 1.0
            bars = ax.bar(
                ["MERGED", "CLOSED"],
                [m_mean, c_mean],
                color=[C_MERGED, C_CLOSED],
                width=0.5,
                edgecolor="white",
                linewidth=1.2,
            )
            ax.set_title(f"Média — {label}", fontsize=10, pad=8)
            ax.set_ylabel(label, fontsize=9)
            ax.set_ylim(bottom=0, top=top)
            self._bar_labels(ax, bars, "{:,.1f}")
            self._clean(ax)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        self._embed(fig, parent)

    def _tab_rq02(self, parent):
        m_times = self._vals("time_to_close_hours", "MERGED")
        c_times = self._vals("time_to_close_hours", "CLOSED")
        all_times = m_times + c_times

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        fig.suptitle(
            "RQ02 – Tempo de Análise vs Feedback Final",
            fontsize=12,
            fontweight="bold",
        )

        m_med = safe_median(m_times)
        c_med = safe_median(c_times)
        top = max(m_med, c_med) * 1.35 or 1.0
        bars = ax1.bar(
            ["MERGED", "CLOSED"],
            [m_med, c_med],
            color=[C_MERGED, C_CLOSED],
            width=0.5,
            edgecolor="white",
            linewidth=1.2,
        )
        ax1.set_title("Mediana do Tempo de Análise (horas)", fontsize=11)
        ax1.set_ylabel("Horas", fontsize=10)
        ax1.set_ylim(bottom=0, top=top)
        self._bar_labels(ax1, bars, "{:,.0f}h")
        self._clean(ax1)
        ax1.text(
            0.5,
            0.97,
            f"MERGED: med={m_med:.0f}h  n={len(m_times)}\n"
            f"CLOSED: med={c_med:.0f}h  n={len(c_times)}",
            ha="center",
            va="top",
            transform=ax1.transAxes,
            fontsize=8,
            color="gray",
        )

        if all_times:
            cap = float(np.percentile(all_times, 99))
            bins = np.linspace(0, cap, 60)
            for times, color, label in [
                (m_times, C_MERGED, "MERGED"),
                (c_times, C_CLOSED, "CLOSED"),
            ]:
                capped = [min(v, cap) for v in times]
                if capped:
                    hist, edges = np.histogram(capped, bins=bins, density=True)
                    centers = (edges[:-1] + edges[1:]) / 2
                    ax2.fill_between(
                        centers,
                        hist,
                        alpha=0.50,
                        color=color,
                        label=f"{label} (n={len(capped)})",
                    )
                    ax2.plot(centers, hist, color=color, linewidth=1.1)
            ax2.set_title(
                f"Distribuição do Tempo de Análise\n(cap 99°pct ≈ {cap:.0f}h)",
                fontsize=10,
            )
            ax2.set_xlabel("Horas", fontsize=9)
            ax2.set_ylabel("Densidade", fontsize=9)
            ax2.legend(fontsize=9)
            from matplotlib.ticker import MultipleLocator

            ax2.xaxis.set_major_locator(MultipleLocator(1000))
            ax2.tick_params(axis="x", labelrotation=45, labelsize=7)
            self._clean(ax2)

        fig.tight_layout(rect=[0, 0, 1, 0.93])
        self._embed(fig, parent)

    def _tab_rq02_zoom(self, parent):
        m_times = self._vals("time_to_close_hours", "MERGED")
        c_times = self._vals("time_to_close_hours", "CLOSED")
        ZOOM_CAP = 1000

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.suptitle(
            "RQ02 – Tempo de Análise vs Feedback Final  (ZoomIn 0–1000h)",
            fontsize=12,
            fontweight="bold",
        )
        bins = np.linspace(0, ZOOM_CAP, 80)
        for times, color, label in [
            (m_times, C_MERGED, "MERGED"),
            (c_times, C_CLOSED, "CLOSED"),
        ]:
            within = [v for v in times if v <= ZOOM_CAP]
            if within:
                hist, edges = np.histogram(within, bins=bins, density=True)
                centers = (edges[:-1] + edges[1:]) / 2
                ax.fill_between(
                    centers,
                    hist,
                    alpha=0.50,
                    color=color,
                    label=f"{label} (n={len(within):,} / {len(times):,})",
                )
                ax.plot(centers, hist, color=color, linewidth=1.1)

        from matplotlib.ticker import MultipleLocator

        ax.xaxis.set_major_locator(MultipleLocator(100))
        ax.tick_params(axis="x", labelrotation=45, labelsize=8)
        ax.set_xlim(0, ZOOM_CAP)
        ax.set_xlabel("Horas", fontsize=9)
        ax.set_ylabel("Densidade", fontsize=9)
        ax.legend(fontsize=9)
        self._clean(ax)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        self._embed(fig, parent)

    def _tab_rq03(self, parent):
        m_body = self._vals("body_length", "MERGED")
        c_body = self._vals("body_length", "CLOSED")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        fig.suptitle(
            "RQ03 – Descrição dos PRs vs Feedback Final",
            fontsize=12,
            fontweight="bold",
        )

        m_med = safe_median(m_body)
        c_med = safe_median(c_body)
        top = max(m_med, c_med) * 1.35 or 1.0
        bars = ax1.bar(
            ["MERGED", "CLOSED"],
            [m_med, c_med],
            color=[C_MERGED, C_CLOSED],
            width=0.5,
            edgecolor="white",
            linewidth=1.2,
        )
        ax1.set_title("Mediana do Comprimento do Corpo", fontsize=10)
        ax1.set_ylabel("Caracteres", fontsize=9)
        ax1.set_ylim(bottom=0, top=top)
        self._bar_labels(ax1, bars, "{:,.0f}")
        self._clean(ax1)

        buckets = [
            ("Sem\n(0)", 0, 1),
            ("Curta\n(1–100)", 1, 101),
            ("Média\n(101–500)", 101, 501),
            ("Longa\n(>500)", 501, float("inf")),
        ]
        labels_b, pcts_b, ns_b = [], [], []
        for lbl, lo, hi in buckets:
            subset = [
                r
                for r in self.rows
                if r.get("body_length") is not None
                and lo <= float(r["body_length"]) < hi
            ]
            n = len(subset)
            nm = sum(1 for r in subset if r.get("state") == "MERGED")
            labels_b.append(lbl)
            pcts_b.append(nm / n * 100 if n else 0)
            ns_b.append(n)

        bars2 = ax2.bar(
            labels_b,
            pcts_b,
            color=PALETTE[:4],
            width=0.55,
            edgecolor="white",
            linewidth=1.2,
        )
        ax2.set_title("% PRs MERGED por Faixa de Descrição", fontsize=10)
        ax2.set_ylabel("% MERGED", fontsize=9)
        ax2.set_ylim(0, 118)
        ax2.axhline(50, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        for bar, pct, n in zip(bars2, pcts_b, ns_b):
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + 2,
                f"{pct:.1f}%\n(n={n})",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )
        self._clean(ax2)

        fig.tight_layout(rect=[0, 0, 1, 0.93])
        self._embed(fig, parent)

    def _tab_rq04(self, parent):
        metrics = [
            ("comments_count", "Comentários"),
            ("participants_count", "Participantes"),
            ("reviews_count", "Reviews"),
        ]
        fig, axes = plt.subplots(1, 3, figsize=(13, 5))
        fig.suptitle(
            "RQ04 – Interações nos PRs vs Feedback Final\n"
            "Medianas: MERGED vs CLOSED",
            fontsize=12,
            fontweight="bold",
        )
        for ax, (key, label) in zip(axes, metrics):
            m_med = safe_median(self._vals(key, "MERGED"))
            c_med = safe_median(self._vals(key, "CLOSED"))
            top = max(m_med, c_med) * 1.35 or 1.0
            bars = ax.bar(
                ["MERGED", "CLOSED"],
                [m_med, c_med],
                color=[C_MERGED, C_CLOSED],
                width=0.5,
                edgecolor="white",
                linewidth=1.2,
            )
            ax.set_title(f"Mediana — {label}", fontsize=10)
            ax.set_ylabel(label, fontsize=9)
            ax.set_ylim(bottom=0, top=top)
            self._bar_labels(ax, bars, "{:,.2f}")
            self._clean(ax)

        fig.tight_layout(rect=[0, 0, 1, 0.92])
        self._embed(fig, parent)

    def _tab_rq05(self, parent):
        metrics = [
            ("changed_files", "Arquivos Modificados", PALETTE[0]),
            ("additions", "Adições (linhas)", PALETTE[1]),
            ("deletions", "Remoções (linhas)", PALETTE[2]),
            ("total_changes", "Total de Mudanças", PALETTE[3]),
        ]
        fig, axes = plt.subplots(2, 2, figsize=(13, 8))
        fig.suptitle(
            "RQ05 – Tamanho dos PRs vs Número de Revisões\n"
            "Box plot por quintil do tamanho  (Q1 = menor  →  Q5 = maior)",
            fontsize=12,
            fontweight="bold",
        )
        for ax, (xkey, xlabel, color) in zip(axes.flat, metrics):
            self._quintile_ax(ax, xkey, "reviews_count", xlabel, color=color, y_max=20)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        self._embed(fig, parent)

    def _tab_rq06(self, parent):
        xs, ys = self._paired("time_to_close_hours", "reviews_count")
        if not xs:
            ttk.Label(
                parent,
                text="Dados insuficientes.",
                font=("Arial", 11),
                foreground="gray",
            ).pack(expand=True)
            return
        rho, pval = spearman_corr(xs, ys)

        X_LIM, Y_LIM = 1000, 30
        pairs_f = [(x, y) for x, y in zip(xs, ys) if x <= X_LIM and y <= Y_LIM]
        n_filt = len(pairs_f)
        pct_shown = n_filt / len(xs) * 100

        if not pairs_f:
            ttk.Label(
                parent,
                text="Sem dados no intervalo definido.",
                font=("Arial", 11),
                foreground="gray",
            ).pack(expand=True)
            return

        xf, yf = zip(*pairs_f)

        bins_x = np.linspace(0, X_LIM, 51)
        bins_y = np.arange(0.5, Y_LIM + 1.5, 1)
        H, xedges, yedges = np.histogram2d(xf, yf, bins=[bins_x, bins_y])

        from matplotlib.colors import LogNorm

        fig, ax = plt.subplots(figsize=(10, 5.5))
        pcm = ax.pcolormesh(xedges, yedges, H.T, cmap="YlOrRd", norm=LogNorm())
        fig.colorbar(pcm, ax=ax, label="Nº de PRs na célula (escala log)")

        ax.set_xlim(0, X_LIM)
        ax.set_ylim(0.5, Y_LIM + 0.5)
        ax.set_xticks(np.arange(0, X_LIM + 1, 100))
        ax.set_yticks(np.arange(5, Y_LIM + 1, 5))

        rho_txt = f"Spearman ρ = {rho:+.3f}" if not math.isnan(rho) else "ρ = N/D"
        p_txt = f"  p = {pval:.2e}" if not math.isnan(pval) else ""
        ax.set_title(
            f"RQ06 – Tempo de Análise vs Número de Revisões  (heatmap 2D)\n"
            f"{rho_txt}{p_txt}   n total={len(xs):,}  ({pct_shown:.1f}% exibido)\n"
            f"Limite: tempo ≤ {X_LIM}h  |  revisões ≤ {Y_LIM}",
            fontsize=11,
            fontweight="bold",
        )
        ax.set_xlabel("Tempo de Análise (h)", fontsize=9)
        ax.set_ylabel("Número de Revisões", fontsize=9)
        self._clean(ax)
        fig.tight_layout()
        self._embed(fig, parent)

    def _tab_rq06_zoom(self, parent):
        xs, ys = self._paired("time_to_close_hours", "reviews_count")
        if not xs:
            ttk.Label(
                parent,
                text="Dados insuficientes.",
                font=("Arial", 11),
                foreground="gray",
            ).pack(expand=True)
            return
        rho, pval = spearman_corr(xs, ys)

        X_LIM, Y_LIM = 10000, 30
        pairs_f = [(x, y) for x, y in zip(xs, ys) if x <= X_LIM and y <= Y_LIM]
        n_filt = len(pairs_f)
        pct_shown = n_filt / len(xs) * 100

        xf, yf = zip(*pairs_f)
        bins_x = np.linspace(0, X_LIM, 101)
        bins_y = np.arange(0.5, Y_LIM + 1.5, 1)
        H, xedges, yedges = np.histogram2d(xf, yf, bins=[bins_x, bins_y])

        from matplotlib.colors import LogNorm
        from matplotlib.ticker import MultipleLocator

        fig, ax = plt.subplots(figsize=(10, 5.5))
        pcm = ax.pcolormesh(xedges, yedges, H.T, cmap="YlOrRd", norm=LogNorm())
        fig.colorbar(pcm, ax=ax, label="Nº de PRs na célula (escala log)")

        ax.set_xlim(0, X_LIM)
        ax.set_ylim(0.5, Y_LIM + 0.5)
        ax.xaxis.set_major_locator(MultipleLocator(1000))
        ax.tick_params(axis="x", labelrotation=45, labelsize=8)
        ax.set_yticks(np.arange(5, Y_LIM + 1, 5))

        rho_txt = f"Spearman ρ = {rho:+.3f}" if not math.isnan(rho) else "ρ = N/D"
        p_txt = f"  p = {pval:.2e}" if not math.isnan(pval) else ""
        ax.set_title(
            f"RQ06 – Tempo de Análise vs Número de Revisões  (heatmap 2D — ZoomOut)\n"
            f"{rho_txt}{p_txt}   n total={len(xs):,}  ({pct_shown:.1f}% exibido)\n"
            f"Limite: tempo ≤ {X_LIM:,}h  |  revisões ≤ {Y_LIM}",
            fontsize=11,
            fontweight="bold",
        )
        ax.set_xlabel("Tempo de Análise (h)", fontsize=9)
        ax.set_ylabel("Número de Revisões", fontsize=9)
        self._clean(ax)
        fig.tight_layout()
        self._embed(fig, parent)

    def _tab_rq07(self, parent):
        pairs = [
            (float(r["body_length"]), float(r["reviews_count"]))
            for r in self.rows
            if r.get("body_length") is not None and r.get("reviews_count") is not None
        ]
        if not pairs:
            ttk.Label(
                parent,
                text="Dados insuficientes.",
                font=("Arial", 11),
                foreground="gray",
            ).pack(expand=True)
            return
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        rho, pval = spearman_corr(xs, ys)

        n_bins = 10
        raw_edges = np.percentile(xs, np.linspace(0, 100, n_bins + 1)).tolist()
        edges = sorted(dict.fromkeys(raw_edges))
        n_actual = len(edges) - 1

        centers, medians, q1s, q3s, ns = [], [], [], [], []
        for i in range(n_actual):
            lo, hi = edges[i], edges[i + 1]
            grp = [
                y for x, y in pairs if (lo <= x < hi if i < n_actual - 1 else x >= lo)
            ]
            if grp:
                centers.append((lo + hi) / 2)
                medians.append(float(np.median(grp)))
                q1s.append(float(np.percentile(grp, 25)))
                q3s.append(float(np.percentile(grp, 75)))
                ns.append(len(grp))

        fig, ax = plt.subplots(figsize=(10, 5.5))
        idx = list(range(len(medians)))
        ax.fill_between(
            idx, q1s, q3s, alpha=0.25, color=PALETTE[5], label="IQR (Q1–Q3)"
        )
        ax.plot(
            idx,
            medians,
            "o-",
            color=PALETTE[5],
            linewidth=2,
            markersize=7,
            label="Mediana de revisões",
            zorder=3,
        )

        ax.set_xticks(idx)
        ax.set_xticklabels(
            [f"{c:.0f}\n(n={n:,})" for c, n in zip(centers, ns)],
            fontsize=7,
        )
        rho_txt = f"Spearman ρ = {rho:+.3f}" if not math.isnan(rho) else "ρ = N/D"
        p_txt = f"  p = {pval:.2e}" if not math.isnan(pval) else ""
        ax.set_title(
            f"RQ07 – Comprimento da Descrição vs Número de Revisões\n"
            f"Mediana por faixa de body_length  ({n_actual} faixas de igual frequência)\n"
            f"{rho_txt}{p_txt}   n={len(xs):,}",
            fontsize=11,
            fontweight="bold",
        )
        ax.set_xlabel("Centro da faixa de body_length (chars)", fontsize=9)
        ax.set_ylabel("Revisões (mediana ± IQR)", fontsize=9)
        ax.legend(fontsize=9)
        self._clean(ax)
        fig.tight_layout()
        self._embed(fig, parent)

    def _tab_rq08(self, parent):
        metrics = [
            ("comments_count", "Comentários", PALETTE[0]),
            ("participants_count", "Participantes", PALETTE[2]),
        ]
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
        fig.suptitle(
            "RQ08 – Interações nos PRs vs Número de Revisões\n"
            "Box plot por quintil das interações  (Q1 = menos  →  Q5 = mais)",
            fontsize=12,
            fontweight="bold",
        )
        for ax, (xkey, xlabel, color) in zip([ax1, ax2], metrics):
            self._quintile_ax(ax, xkey, "reviews_count", xlabel, color=color, y_max=20)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        self._embed(fig, parent)

    def _tab_merge_rate(self, parent):
        fig, axes = plt.subplots(2, 2, figsize=(13, 9))
        fig.suptitle(
            "Taxa de Merge por Categoria  (% PRs MERGED por faixa)",
            fontsize=12,
            fontweight="bold",
        )

        def plot_rate(ax, title, buckets_def, key, palette):
            labels, pcts, ns = [], [], []
            for lbl, lo, hi in buckets_def:
                subset = [
                    r
                    for r in self.rows
                    if r.get(key) is not None and lo <= float(r[key]) < hi
                ]
                n = len(subset)
                nm = sum(1 for r in subset if r.get("state") == "MERGED")
                labels.append(lbl)
                pcts.append(nm / n * 100 if n else 0)
                ns.append(n)

            bars = ax.bar(
                labels,
                pcts,
                color=palette[: len(labels)],
                edgecolor="white",
                linewidth=1.1,
            )
            ax.set_title(title, fontsize=10)
            ax.set_ylabel("% MERGED", fontsize=9)
            ax.set_ylim(0, 118)
            ax.axhline(50, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
            for bar, pct, n in zip(bars, pcts, ns):
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    bar.get_height() + 2,
                    f"{pct:.1f}%\nn={n}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    fontweight="bold",
                )
            self._clean(ax)

        plot_rate(
            axes[0][0],
            "Taxa de Merge por Tamanho (total_changes)",
            [
                ("Mínimo\n(1-10)", 0, 11),
                ("Pequeno\n(11-100)", 11, 101),
                ("Médio\n(101-1k)", 101, 1001),
                ("Grande\n(>1k)", 1001, float("inf")),
            ],
            "total_changes",
            PALETTE,
        )
        plot_rate(
            axes[0][1],
            "Taxa de Merge por Tempo de Análise",
            [
                ("< 24h", 0, 24),
                ("1–7 dias\n(24-168h)", 24, 168),
                ("7–30 dias\n(168-720h)", 168, 720),
                ("> 30 dias\n(>720h)", 720, float("inf")),
            ],
            "time_to_close_hours",
            PALETTE[4:],
        )
        plot_rate(
            axes[1][0],
            "Taxa de Merge por Descrição (body_length)",
            [
                ("Sem\n(0)", 0, 1),
                ("Curta\n(1-100)", 1, 101),
                ("Média\n(101-500)", 101, 501),
                ("Longa\n(>500)", 501, float("inf")),
            ],
            "body_length",
            PALETTE,
        )
        plot_rate(
            axes[1][1],
            "Taxa de Merge por Nº de Comentários",
            [
                ("0", 0, 1),
                ("1–5", 1, 6),
                ("6–20", 6, 21),
                ("> 20", 21, float("inf")),
            ],
            "comments_count",
            PALETTE[4:],
        )
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        self._embed(fig, parent)

    def _rq_verdicts(self):
        results = []

        for key, _ in [
            ("changed_files", ""),
            ("total_changes", ""),
        ]:
            m = safe_median(self._vals(key, "MERGED"))
            c = safe_median(self._vals(key, "CLOSED"))
            results.append(
                (
                    "RQ01",
                    "Tamanho maior → menos merges",
                    f"Mediana MERGED={m:.0f} / CLOSED={c:.0f}",
                    "Sim" if c > m else "Nao",
                )
            )
            break

        m_t = safe_median(self._vals("time_to_close_hours", "MERGED"))
        c_t = safe_median(self._vals("time_to_close_hours", "CLOSED"))
        results.append(
            (
                "RQ02",
                "Tempo maior → menos merges",
                f"Mediana MERGED={m_t:.0f}h / CLOSED={c_t:.0f}h",
                "Sim" if c_t > m_t else "Nao",
            )
        )

        m_b = safe_median(self._vals("body_length", "MERGED"))
        c_b = safe_median(self._vals("body_length", "CLOSED"))
        results.append(
            (
                "RQ03",
                "Descricao maior → mais merges",
                f"Mediana MERGED={m_b:.0f} / CLOSED={c_b:.0f} chars",
                "Sim" if m_b > c_b else "Nao",
            )
        )

        m_c = safe_median(self._vals("comments_count", "MERGED"))
        c_c = safe_median(self._vals("comments_count", "CLOSED"))
        results.append(
            (
                "RQ04",
                "Interacoes maiores → menos merges",
                f"Mediana comments MERGED={m_c:.1f} / CLOSED={c_c:.1f}",
                "Sim" if c_c > m_c else "Nao",
            )
        )

        corr_rqs = [
            ("RQ05", "Tamanho maior → mais revisoes", "total_changes", True),
            ("RQ06", "Tempo maior → mais revisoes", "time_to_close_hours", True),
            ("RQ07", "Descricao maior → menos revisoes", "body_length", False),
            ("RQ08", "Interacoes maiores → mais revisoes", "comments_count", True),
        ]
        for rq_id, hip, xkey, expect_positive in corr_rqs:
            xs, ys = self._paired(xkey, "reviews_count")
            if len(xs) >= 3:
                rho, pval = spearman_corr(xs, ys)
                sig = (not math.isnan(pval)) and pval < 0.05
                direction_ok = (rho > 0) if expect_positive else (rho < 0)
                confirmed = sig and direction_ok and not math.isnan(rho)
                p_txt = f"p={pval:.2e}" if not math.isnan(pval) else "sem scipy"
                detail = f"rho={rho:+.3f}, {p_txt}"
            else:
                confirmed, detail = False, "N/D"
            results.append((rq_id, hip, detail, "Sim" if confirmed else "Nao"))
        return results

    def _tab_summary(self, parent):
        ttk.Label(
            parent,
            text="Comprovacao das Questoes de Pesquisa (RQs)",
            font=("Arial", 10, "bold"),
        ).pack(pady=(8, 2))

        v_cols = ("RQ", "Hipotese", "Resultado", "Comprovada?")
        v_tree = ttk.Treeview(parent, columns=v_cols, show="headings", height=8)
        for col, w in zip(v_cols, [55, 265, 280, 85]):
            v_tree.heading(col, text=col)
            v_tree.column(
                col, width=w, anchor=tk.CENTER if col in ("RQ", "Comprovada?") else tk.W
            )
        v_tree.pack(fill=tk.X, padx=12, pady=(0, 8))
        v_tree.tag_configure("yes", foreground=C_MERGED)
        v_tree.tag_configure("no", foreground=C_CLOSED)

        for rq_id, hip, detail, verdict in self._rq_verdicts():
            v_tree.insert(
                "",
                tk.END,
                values=(rq_id, hip, detail, verdict),
                tags=("yes" if verdict == "Sim" else "no",),
            )

        ttk.Label(
            parent,
            text="Estatísticas Descritivas por Métrica",
            font=("Arial", 10, "bold"),
        ).pack(pady=(8, 2))

        stat_cols = ("Métrica", "N", "Mín", "Mediana", "Média", "Máx")
        stat_tree = ttk.Treeview(
            parent,
            columns=stat_cols,
            show="headings",
            height=10,
        )
        for col, w in zip(stat_cols, [220, 60, 110, 110, 110, 110]):
            stat_tree.heading(col, text=col)
            stat_tree.column(
                col,
                width=w,
                anchor=tk.W if col == "Métrica" else tk.CENTER,
            )
        stat_tree.pack(fill=tk.X, padx=12)

        stat_metrics = [
            ("Tempo de Análise (h)", "time_to_close_hours"),
            ("Arquivos Modificados", "changed_files"),
            ("Adições", "additions"),
            ("Remoções", "deletions"),
            ("Total de Mudanças", "total_changes"),
            ("Comprimento do Corpo", "body_length"),
            ("Número de Reviews", "reviews_count"),
            ("Participantes", "participants_count"),
            ("Comentários", "comments_count"),
        ]
        for label, key in stat_metrics:
            vals = self._vals(key)
            if not vals:
                stat_tree.insert("", tk.END, values=(label, 0, "—", "—", "—", "—"))
                continue
            try:
                stat_tree.insert(
                    "",
                    tk.END,
                    values=(
                        label,
                        len(vals),
                        f"{min(vals):,.2f}",
                        f"{_st.median(vals):,.2f}",
                        f"{_st.mean(vals):,.2f}",
                        f"{max(vals):,.2f}",
                    ),
                )
            except Exception:
                stat_tree.insert(
                    "", tk.END, values=(label, len(vals), "err", "err", "err", "err")
                )

        suffix = "" if SCIPY_AVAILABLE else " [sem scipy — p não disponível]"
        ttk.Label(
            parent,
            text=f"Correlação de Spearman (ρ) — Variáveis Explicativas vs Respostas{suffix}",
            font=("Arial", 10, "bold"),
        ).pack(pady=(12, 2))

        corr_cols = (
            "Variável Explicativa",
            "vs Estado (ρ)",
            "vs Nº Reviews (ρ)",
            "p-valor",
        )
        corr_tree = ttk.Treeview(
            parent,
            columns=corr_cols,
            show="headings",
            height=9,
        )
        for col, w in zip(corr_cols, [230, 130, 140, 120]):
            corr_tree.heading(col, text=col)
            corr_tree.column(
                col,
                width=w,
                anchor=tk.W if col == "Variável Explicativa" else tk.CENTER,
            )
        corr_tree.pack(fill=tk.X, padx=12, pady=(0, 12))

        explain_metrics = [
            ("Arquivos Modificados", "changed_files"),
            ("Adições", "additions"),
            ("Remoções", "deletions"),
            ("Total de Mudanças", "total_changes"),
            ("Tempo de Análise (h)", "time_to_close_hours"),
            ("Comprimento do Corpo", "body_length"),
            ("Participantes", "participants_count"),
            ("Comentários", "comments_count"),
        ]
        for label, key in explain_metrics:
            pairs_s = [
                (float(r[key]), 1.0 if r.get("state") == "MERGED" else 0.0)
                for r in self.rows
                if r.get(key) is not None
            ]
            pairs_r = [
                (float(r[key]), float(r["reviews_count"]))
                for r in self.rows
                if r.get(key) is not None and r.get("reviews_count") is not None
            ]

            if len(pairs_s) >= 3:
                xs, ys = zip(*pairs_s)
                rho_s, _ = spearman_corr(list(xs), list(ys))
                rho_s_txt = f"{rho_s:+.4f}" if not math.isnan(rho_s) else "N/D"
            else:
                rho_s_txt = "— (n<3)"

            if len(pairs_r) >= 3:
                xr, yr = zip(*pairs_r)
                rho_r, pval_r = spearman_corr(list(xr), list(yr))
                rho_r_txt = f"{rho_r:+.4f}" if not math.isnan(rho_r) else "N/D"
                p_txt = (
                    f"{pval_r:.4f}" if not math.isnan(pval_r) else "N/D (instale scipy)"
                )
            else:
                rho_r_txt, p_txt = "— (n<3)", "—"

            corr_tree.insert("", tk.END, values=(label, rho_s_txt, rho_r_txt, p_txt))

    def _quintile_ax(
        self, ax, xkey, ykey, xlabel, n_bins=5, color="#1565C0", y_max=None
    ):
        pairs = [
            (float(r[xkey]), float(r[ykey]))
            for r in self.rows
            if r.get(xkey) is not None and r.get(ykey) is not None
        ]
        if not pairs:
            ax.set_visible(False)
            return
        xs, ys = zip(*pairs)
        xs, ys = list(xs), list(ys)

        raw_edges = np.percentile(xs, np.linspace(0, 100, n_bins + 1)).tolist()
        edges = sorted(dict.fromkeys(raw_edges))
        n_actual = len(edges) - 1

        groups, labels = [], []
        for i in range(n_actual):
            lo, hi = edges[i], edges[i + 1]
            grp = [
                y
                for x, y in zip(xs, ys)
                if (lo <= x < hi if i < n_actual - 1 else x >= lo)
            ]
            groups.append(grp if grp else [0])
            lo_lbl = f"{lo/1e3:.0f}k" if lo >= 1e4 else f"{lo:.0f}"
            hi_lbl = f"{hi/1e3:.0f}k" if hi >= 1e4 else f"{hi:.0f}"
            labels.append(f"Q{i+1}\n[{lo_lbl}–{hi_lbl}]\nn={len(grp):,}")

        bp = ax.boxplot(
            groups,
            tick_labels=labels,
            patch_artist=True,
            medianprops={"color": "red", "linewidth": 1.8},
            flierprops={"marker": ".", "markersize": 2, "alpha": 0.2},
            whiskerprops={"linewidth": 1},
            capprops={"linewidth": 1},
        )
        for patch in bp["boxes"]:
            patch.set_facecolor(color)
            patch.set_alpha(0.45)

        if y_max is not None:
            ax.set_ylim(bottom=0, top=y_max)
        else:
            y_cap = float(np.percentile(ys, 99))
            ax.set_ylim(bottom=0, top=y_cap * 1.15)

        rho, pval = spearman_corr(xs, ys)
        rho_txt = f"ρ={rho:+.3f}" if not math.isnan(rho) else "ρ=N/D"
        p_txt = f"  p={pval:.2e}" if not math.isnan(pval) else ""
        ax.set_title(
            f"{xlabel} vs Reviews\n{rho_txt}{p_txt}   n={len(xs):,}",
            fontsize=9,
        )
        ax.set_xlabel(f"{xlabel} (quintis)", fontsize=8)
        ax.set_ylabel("Revisões", fontsize=8)
        self._clean(ax)


def main():
    root = tk.Tk()
    PRAnalyzerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
