"""
modelo.py — a matemática do projeto.

Aqui fica tudo o que é cálculo: as funções de doação e consumo, a integração
simbólica com SymPy e os métodos numéricos implementados na mão.

Nada de Flask neste arquivo. A interface é problema do app.py.

Tempo t em meses, com t = 0 em 1º de janeiro e t = 6 no fim de junho.
Todas as funções devolvem bolsas por mês.
"""

import sympy as sp

t = sp.symbols("t", real=True)


# ---------------------------------------------------------------------------
# As funções do modelo
# ---------------------------------------------------------------------------

def doacao(a=80, b=950):
    """Taxa de doação de O negativo: uma reta só.

    Parte de 950 bolsas em janeiro, no fundo das férias, e chega a 1430 em
    junho. O coeficiente angular positivo traduz a recuperação da captação
    ao longo do semestre.
    """
    return a * t + b


# Consumo definido por partes: (t_inicial, t_final, coef_angular, termo_indep).
# Um evento de Carnaval e um de São João não cabem numa reta só.
PECAS_CONSUMO = [
    (0, 2, 100, 1100),    # verão, subindo até o pico do Carnaval
    (2, 5, -120, 1540),   # queda depois do Carnaval
    (5, 6, 160, 140),     # subida do São João
]


def consumo_no_trecho(i):
    """Devolve a expressão da i-ésima reta do consumo."""
    _, _, a, b = PECAS_CONSUMO[i]
    return a * t + b


def verificar_continuidade():
    """Confere se as retas do consumo se encontram sem salto.

    É o primeiro passo de conferência do modelo, e uma boa coisa para
    mostrar na apresentação. Devolve uma lista de (t, valor pela esquerda,
    valor pela direita) nos pontos de junção.
    """
    juncoes = []
    for i in range(len(PECAS_CONSUMO) - 1):
        _, fim, a1, b1 = PECAS_CONSUMO[i]
        _, _, a2, b2 = PECAS_CONSUMO[i + 1]
        juncoes.append((fim, a1 * fim + b1, a2 * fim + b2))
    return juncoes


def consumo_em(valor):
    """Avalia o consumo num instante, escolhendo a reta certa."""
    for inicio, fim, a, b in PECAS_CONSUMO:
        if inicio <= valor <= fim:
            return a * valor + b
    inicio, fim, a, b = PECAS_CONSUMO[0] if valor < 0 else PECAS_CONSUMO[-1]
    return a * valor + b


# ---------------------------------------------------------------------------
# Integração exata, via SymPy
# ---------------------------------------------------------------------------

def primitiva(expr):
    """A antiderivada da expressão, sem os limites. É o que vai no caderno."""
    return sp.integrate(expr, t)


def integral_doacao(t0, t1, a=80, b=950):
    """Integral definida da doação, resolvida simbolicamente."""
    resultado = sp.integrate(doacao(a, b), (t, sp.nsimplify(t0), sp.nsimplify(t1)))
    return float(sp.N(resultado))


def detalhar_consumo(t0, t1):
    """Integra o consumo peça a peça e devolve cada parcela separada.

    Como C é definida por partes, a integral se quebra em três — uma para
    cada intervalo. Cada parcela é calculada sobre a interseção entre o
    intervalo pedido e o trecho da reta. A soma das partes é a integral do
    todo: é a propriedade de aditividade em relação ao intervalo.
    """
    linhas = []
    for i, (inicio, fim, a, b) in enumerate(PECAS_CONSUMO):
        lo, hi = max(t0, inicio), min(t1, fim)
        if hi > lo:
            parcela = sp.integrate(
                consumo_no_trecho(i), (t, sp.nsimplify(lo), sp.nsimplify(hi))
            )
            sinal = "+" if b >= 0 else "−"
            linhas.append({
                "intervalo": "[%g, %g]" % (lo, hi),
                "funcao": "%gt %s %g" % (a, sinal, abs(b)),
                "valor": float(sp.N(parcela)),
            })
    return linhas


def integral_consumo(t0, t1):
    """Integral definida do consumo: a soma das parcelas."""
    return sum(linha["valor"] for linha in detalhar_consumo(t0, t1))


# ---------------------------------------------------------------------------
# Teorema do Valor Médio para Integrais
# ---------------------------------------------------------------------------
#
# A integral definida devolve o total acumulado no período, não a taxa média.
# A taxa média se obtém dividindo esse total pela largura do intervalo:
#
#   V_médio = 1/(b - a) · ∫ₐᵇ f(t) dt
#
# O teorema garante ainda que existe pelo menos um instante c dentro do
# intervalo em que a taxa instantânea coincide com essa média.

def valor_medio(total, t0, t1):
    """Taxa média no intervalo: o total dividido pela largura do intervalo."""
    return total / (t1 - t0)


def instante_doacao_na_media(media, a=80, b=950):
    """Resolve D(c) = média: em que instante a doação bate a própria média.

    Como a doação é uma única reta, há sempre exatamente um instante c.
    """
    return float(sp.solve(sp.Eq(a * t + b, media), t)[0])


def instantes_consumo_na_media(media, t0, t1):
    """Resolve C(t) = média em cada trecho do consumo, dentro de [t0, t1].

    Por ser definido por partes, o consumo pode bater a própria média mais de
    uma vez — o teorema garante ao menos um instante, não exatamente um.
    """
    instantes = []
    for inicio, fim, a, b in PECAS_CONSUMO:
        lo, hi = max(t0, inicio), min(t1, fim)
        if hi <= lo:
            continue
        for solucao in sp.solve(sp.Eq(a * t + b, media), t):
            valor = float(solucao)
            if lo <= valor <= hi:
                instantes.append(valor)
    return instantes


# ---------------------------------------------------------------------------
# Métodos numéricos, implementados na mão
# ---------------------------------------------------------------------------

def _amostrar(t0, t1, n, a, b):
    """Avalia D(t) − C(t) em n+1 pontos igualmente espaçados."""
    h = (t1 - t0) / n
    return h, [(a * (t0 + i * h) + b) - consumo_em(t0 + i * h) for i in range(n + 1)]


def riemann_esquerda(t0, t1, n=12, a=80, b=950):
    """Soma de Riemann com retângulos pela esquerda.

    Um retângulo nunca acompanha uma reta inclinada, então este método erra
    mesmo com funções lineares. É o único da lista que produz erro aqui.
    """
    h, y = _amostrar(t0, t1, n, a, b)
    return sum(y[:-1]) * h


def trapezio(t0, t1, n=12, a=80, b=950):
    """Regra do trapézio: aproxima cada fatia por uma reta.

    Com funções lineares o resultado é exato, porque a aproximação coincide
    com a função original.
    """
    h, y = _amostrar(t0, t1, n, a, b)
    return ((y[0] + y[-1]) / 2 + sum(y[1:-1])) * h


def simpson(t0, t1, n=12, a=80, b=950):
    """Regra de Simpson: aproxima cada par de fatias por uma parábola.

    Precisa de n par. É exata até polinômios de grau 3, então também acerta
    em cheio o caso linear.
    """
    if n % 2:
        n += 1
    h, y = _amostrar(t0, t1, n, a, b)
    soma = y[0] + y[-1]
    for i in range(1, n):
        soma += y[i] * (4 if i % 2 else 2)
    return soma * h / 3


# ---------------------------------------------------------------------------
# O relatório que a interface consome
# ---------------------------------------------------------------------------

def analisar(a=80, b=950, t0=0, t1=6, n=12):
    """Roda os quatro métodos no intervalo pedido e devolve tudo num dicionário."""
    entrada = integral_doacao(t0, t1, a, b)
    parcelas = detalhar_consumo(t0, t1)
    saida = sum(linha["valor"] for linha in parcelas)
    exata = entrada - saida

    ri = riemann_esquerda(t0, t1, n, a, b)
    tr = trapezio(t0, t1, n, a, b)
    si = simpson(t0, t1, n, a, b)

    media_doacao = valor_medio(entrada, t0, t1)
    media_consumo = valor_medio(saida, t0, t1)

    return {
        "entrada": entrada,
        "saida": saida,
        "exata": exata,
        "riemann": ri,
        "trapezio": tr,
        "simpson": si,
        "erro_riemann": abs(ri - exata),
        "erro_trapezio": abs(tr - exata),
        "erro_simpson": abs(si - exata),
        "parcelas": parcelas,
        "primitiva_doacao": sp.pretty(primitiva(doacao(a, b)), use_unicode=True),
        "continuidade": verificar_continuidade(),
        "n": n if n % 2 == 0 else n + 1,
        "media_doacao": media_doacao,
        "media_consumo": media_consumo,
        "media_saldo": valor_medio(exata, t0, t1),
        "instante_doacao": instante_doacao_na_media(media_doacao, a, b),
        "instantes_consumo": instantes_consumo_na_media(media_consumo, t0, t1),
    }


if __name__ == "__main__":
    # Rode `python modelo.py` para conferir os números sem abrir o site.
    print("Continuidade do consumo nas junções:")
    for ponto, esq, dir_ in verificar_continuidade():
        marca = "ok" if abs(esq - dir_) < 1e-9 else "SALTO"
        print("  t = %g:  %g  |  %g   %s" % (ponto, esq, dir_, marca))

    print("\nSaldos:")
    for rotulo, x, y in [("Fevereiro", 1, 2), ("Abril", 3, 4), ("Semestre", 0, 6)]:
        r = analisar(t0=x, t1=y)
        print("  %-10s doação %8.2f   consumo %8.2f   saldo %8.2f"
              % (rotulo, r["entrada"], r["saida"], r["exata"]))

    print("\nTaxa média pelo Teorema do Valor Médio (semestre):")
    r = analisar(t0=0, t1=6)
    print("  doação média  %8.2f bolsas/mês   (bate a média em t = %g)"
          % (r["media_doacao"], r["instante_doacao"]))
    print("  consumo médio %8.2f bolsas/mês   (bate a média em t = %s)"
          % (r["media_consumo"], ", ".join("%.2f" % v for v in r["instantes_consumo"])))
    print("  saldo médio   %8.2f bolsas/mês" % r["media_saldo"])

    print("\nMétodos numéricos no semestre (n = 12):")
    r = analisar(t0=0, t1=6, n=12)
    for nome, chave in [("Riemann", "riemann"), ("Trapézio", "trapezio"),
                        ("Simpson", "simpson")]:
        print("  %-10s %10.4f   erro %.2e" % (nome, r[chave], r["erro_" + chave]))
