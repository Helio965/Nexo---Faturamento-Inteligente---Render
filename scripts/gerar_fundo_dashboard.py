"""Gera o fundo do painel autenticado (arte original e procedural da NEXO).

Paisagem de crepúsculo estilizada: céu índigo/violeta, brilho quente no
horizonte, cordilheiras em camadas com névoa atmosférica e um lago que reflete
a cena. A imagem sai desfocada e escura de propósito: ela fica atrás do vidro
(glassmorphism) do painel e não pode competir com o conteúdo.

Por ser gerada por código, não depende de foto de terceiros nem de licença
externa. A semente é fixa: rodar de novo produz o mesmo arquivo.

Uso: python scripts/gerar_fundo_dashboard.py
Saída: static/img/painel/nexo-fundo-crepusculo.jpg (1920x1080, JPEG progressivo)
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

LARGURA, ALTURA = 1920, 1080
ESCALA = 2  # desenha em 2x e reduz: bordas suaves sem serrilhado
SEMENTE = 20261026
DESTINO = Path(__file__).resolve().parent.parent / "static" / "img" / "painel" / "nexo-fundo-crepusculo.jpg"


def _cor(hexa):
    hexa = hexa.lstrip("#")
    return np.array([int(hexa[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def _mistura(a, b, t):
    t = np.clip(t, 0.0, 1.0)[..., None]
    return a * (1.0 - t) + b * t


def _gradiente_vertical(y, paradas):
    """Interpola cores por posição vertical (0 = topo, 1 = base)."""
    pos = np.array([p for p, _ in paradas], dtype=np.float32)
    cores = np.stack([_cor(c) for _, c in paradas])
    saida = np.empty(y.shape + (3,), dtype=np.float32)
    for canal in range(3):
        saida[..., canal] = np.interp(y, pos, cores[:, canal])
    return saida


def _cumeeira(rng, largura, base, amplitude, oitavas=6, rugosidade=0.52):
    """Perfil de montanha por soma de senoides em várias escalas (ruído fractal 1D)."""
    x = np.linspace(0.0, 1.0, largura, dtype=np.float32)
    perfil = np.zeros_like(x)
    amp, freq = 1.0, 1.6
    for _ in range(oitavas):
        fase = rng.uniform(0, 2 * np.pi)
        perfil += amp * np.sin(2 * np.pi * freq * x + fase)
        perfil += 0.5 * amp * np.sin(2 * np.pi * freq * 1.93 * x + rng.uniform(0, 2 * np.pi))
        amp *= rugosidade
        freq *= 2.07
    perfil = (perfil - perfil.min()) / (perfil.max() - perfil.min())
    return base - amplitude * perfil


def gerar():
    rng = np.random.default_rng(SEMENTE)
    w, h = LARGURA * ESCALA, ALTURA * ESCALA
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = yy / h
    u = xx / w
    horizonte = 0.66

    # Céu: índigo profundo no alto, violeta NEXO no meio, pêssego/rosado no horizonte.
    ceu = _gradiente_vertical(v / horizonte, [
        (0.00, "#070512"), (0.30, "#140c33"), (0.55, "#2b1659"),
        (0.78, "#5a2d7c"), (0.92, "#a2508a"), (1.00, "#e08a7a"),
    ])
    # Brilho do sol já posto, deslocado à direita.
    sol = np.exp(-(((u - 0.70) / 0.20) ** 2 + ((v - horizonte) / 0.10) ** 2))
    ceu = ceu + sol[..., None] * _cor("#ffb38a") * 0.55
    halo = np.exp(-(((u - 0.70) / 0.55) ** 2 + ((v - horizonte) / 0.32) ** 2))
    ceu = ceu + halo[..., None] * _cor("#8e44c9") * 0.22

    # Estrelas discretas no topo (somem com o desfoque, viram textura).
    estrelas = rng.random((h, w)) > 0.99965
    brilho = np.where(estrelas & (v < 0.35), (0.35 - v) / 0.35, 0.0)
    ceu = ceu + brilho[..., None] * 160.0

    imagem = ceu.copy()

    # Cordilheiras: do fundo (claro, enevoado) para a frente (escuro).
    camadas = [
        (0.585, 0.15, "#4a2c79", 0.70),
        (0.615, 0.16, "#3a2066", 0.52),
        (0.640, 0.13, "#25144a", 0.34),
        (0.665, 0.10, "#160b31", 0.18),
    ]
    for base, amplitude, cor, nevoa in camadas:
        topo = _cumeeira(rng, w, base, amplitude)[None, :]
        mascara = (v >= topo) & (v <= horizonte + 0.0005)
        cor_camada = _mistura(_cor(cor)[None, None, :], ceu, np.full(v.shape, nevoa))
        # Névoa mais densa perto do pé da montanha.
        pe = np.clip((v - topo) / 0.08, 0.0, 1.0)
        cor_camada = _mistura(cor_camada, _cor("#c06a9a")[None, None, :], pe * 0.18 * nevoa)
        imagem = np.where(mascara[..., None], cor_camada, imagem)

    # Lago: reflexo espelhado da faixa acima do horizonte, mais escuro e com ondulação.
    linhas_lago = np.arange(int(horizonte * h), h)
    for linha in linhas_lago:
        dist = linha - horizonte * h
        origem = int(horizonte * h - dist * 0.92)
        origem = max(0, origem)
        deslocamento = int(6 * ESCALA * np.sin(linha * 0.11) * (dist / h))
        faixa = np.roll(imagem[origem], deslocamento, axis=0)
        escurece = 0.62 - 0.30 * (dist / (h * (1 - horizonte)))
        imagem[linha] = faixa * escurece + _cor("#0a0718") * (1 - escurece)
    # Trilha de luz do sol na água.
    trilha = np.exp(-(((u - 0.70) / 0.035) ** 2)) * np.clip((v - horizonte) / 0.30, 0, 1) * (v > horizonte)
    ondas = 0.5 + 0.5 * np.sin(yy * 0.9 / ESCALA)
    imagem = imagem + (trilha * ondas)[..., None] * _cor("#f3a07e") * 0.30

    # Vinheta e escurecimento geral: o painel fica por cima.
    vinheta = 1.0 - 0.55 * (((u - 0.5) / 0.75) ** 2 + ((v - 0.45) / 0.85) ** 2)
    imagem = imagem * np.clip(vinheta, 0.35, 1.0)[..., None] * 0.92

    figura = Image.fromarray(np.clip(imagem, 0, 255).astype(np.uint8), "RGB")
    figura = figura.resize((LARGURA, ALTURA), Image.LANCZOS)
    figura = figura.filter(ImageFilter.GaussianBlur(radius=7))
    # Pontilhado leve: evita faixas visíveis no degradê do céu (8 bits + JPEG).
    pixels = np.asarray(figura, dtype=np.float32)
    pixels += rng.triangular(-1.6, 0.0, 1.6, size=pixels.shape).astype(np.float32)
    figura = Image.fromarray(np.clip(pixels + 0.5, 0, 255).astype(np.uint8), "RGB")
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    figura.save(DESTINO, "JPEG", quality=84, optimize=True, progressive=True)
    return DESTINO


if __name__ == "__main__":
    caminho = gerar()
    print(f"{caminho} ({caminho.stat().st_size // 1024} KB)")
