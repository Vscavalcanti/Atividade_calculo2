"""
app.py — a interface web.

Só cuida de receber os parâmetros do formulário, chamar o modelo.py e
devolver a página. A matemática não mora aqui.

Para rodar:  python app.py
Depois abra http://127.0.0.1:5000 no navegador.
"""

import base64
import io

import matplotlib
matplotlib.use("Agg")  # backend sem janela: obrigatório dentro de um servidor
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, render_template, request

import modelo

app = Flask(__name__)

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]


def gerar_grafico(a, b, t0, t1):
    """Desenha as duas curvas e pinta a área entre elas.

    A área é a parte visual do argumento: onde o vermelho passa por cima do
    amarelo, a integral é negativa e o estoque encolhe.
    """
    ts = np.linspace(t0, t1, 400)
    d = a * ts + b
    c = np.array([modelo.consumo_em(x) for x in ts])

    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=110)

    ax.fill_between(ts, d, c, where=(d >= c), color="#2E5E6B", alpha=0.18,
                    interpolate=True, label="Estoque cresce")
    ax.fill_between(ts, d, c, where=(d < c), color="#8E1B32", alpha=0.18,
                    interpolate=True, label="Estoque encolhe")

    ax.plot(ts, d, color="#B8860B", linewidth=2.4, label="Doação D(t)")
    ax.plot(ts, c, color="#8E1B32", linewidth=2.4, label="Consumo C(t)")

    # marca as junções entre as retas do consumo que caem dentro do intervalo
    for ponto, valor, _ in modelo.verificar_continuidade():
        if t0 < ponto < t1:
            ax.plot([ponto], [valor], "o", color="#8E1B32", markersize=5)

    marcas = list(range(int(np.ceil(t0)), int(np.floor(t1)) + 1))
    ax.set_xticks(marcas)
    ax.set_xticklabels([MESES[m % 12] for m in marcas])
    ax.set_ylabel("bolsas por mês")
    ax.set_xlim(t0, t1)
    ax.grid(axis="y", color="#D2DAD8", linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.legend(loc="lower left", fontsize=8, frameon=False, ncol=2)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", transparent=True)
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def ler_float(nome, padrao):
    """Lê um campo do formulário sem quebrar se vier vazio ou com lixo."""
    try:
        return float(request.values.get(nome, padrao))
    except (TypeError, ValueError):
        return padrao


@app.route("/", methods=["GET", "POST"])
def index():
    a = ler_float("a", 80)
    b = ler_float("b", 950)
    t0 = ler_float("t0", 0)
    t1 = ler_float("t1", 6)
    n = int(ler_float("n", 12))

    erro = None
    if t1 <= t0:
        erro = "O mês final precisa ser maior que o inicial."
        t0, t1 = 0, 6
    if t0 < 0 or t1 > 6:
        erro = "O modelo cobre apenas de janeiro (0) a junho (6)."
        t0, t1 = max(t0, 0), min(t1, 6)
    if n < 2:
        n = 2

    resultado = modelo.analisar(a, b, t0, t1, n)
    grafico = gerar_grafico(a, b, t0, t1)

    return render_template(
        "index.html",
        r=resultado,
        grafico=grafico,
        erro=erro,
        campos={"a": a, "b": b, "t0": t0, "t1": t1, "n": n},
    )


if __name__ == "__main__":
    app.run(debug=True)
