"""Grafika ciferníku „Chata“ (Watch Face Format). Spuštění: python3 generuj.py  (potřebuje pycairo)

Kreslí do ../src/main/res/drawable-nodpi/: ciferník, ručky, ručičky subdialů, ambientní (úsporné) verze a náhled.
Rozměr plátna 480 × 480 (Xiaomi Watch 5 má 480 × 480 px), střed 240/240.
"""
import math
import os

import cairo

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "main", "res", "drawable-nodpi")
S, C = 480, 240
FONT = "Inter Display"

# polohy subdialů (střed x, y) a poloměr
SUB_R = 57
SUBS = {"chata": (146, 240), "bat": (334, 240), "temp": (240, 340)}
SWEEP = 135          # ručička subdialu: −135° … +135° (270°)

# barvy
LUME = (0.93, 0.91, 0.82)
ORANGE = (1.0, 0.36, 0.10)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def new(w=S, h=S):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    return s, cairo.Context(s)


def save(s, name):
    os.makedirs(OUT, exist_ok=True)
    s.write_to_png(os.path.join(OUT, name + ".png"))


def polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def text(cr, s, x, y, size, color=(1, 1, 1), weight=cairo.FONT_WEIGHT_BOLD, family=FONT, alpha=1.0, spacing=0.0):
    cr.select_font_face(family, cairo.FONT_SLANT_NORMAL, weight)
    cr.set_font_size(size)
    ext = cr.text_extents(s)
    w = ext.x_advance + spacing * (len(s) - 1)
    cx = x - w / 2
    cy = y - (ext.y_bearing + ext.height / 2)
    cr.set_source_rgba(*color, alpha)
    for ch in s:
        cr.move_to(cx, cy)
        cr.show_text(ch)
        cx += cr.text_extents(ch).x_advance + spacing


def blur_shadow(src, radius=4, alpha=0.6, dx=0, dy=0):
    """Měkký stín z alfa kanálu (jednoduchý box blur přes několik posunutých kopií)."""
    w, h = src.get_width(), src.get_height()
    sh, cr = new(w, h)
    n = 0
    steps = [(i, j) for i in range(-radius, radius + 1, 2) for j in range(-radius, radius + 1, 2)]
    for i, j in steps:
        cr.set_source_rgba(0, 0, 0, 1)
        cr.mask_surface(src, i + dx, j + dy)
        n += 1
    out, c2 = new(w, h)
    c2.set_source_surface(sh, 0, 0)
    c2.paint_with_alpha(alpha * 4 / n)
    return out


# ---------------------------------------------------------------- ciferník
def dial():
    s, cr = new()
    cr.arc(C, C, C, 0, 2 * math.pi)
    cr.clip()
    # základ: hluboká modrá, světlejší střed
    g = cairo.RadialGradient(C - 30, C - 40, 10, C, C, C)
    g.add_color_stop_rgb(0, *rgb("#1d4f8c"))
    g.add_color_stop_rgb(0.45, *rgb("#103463"))
    g.add_color_stop_rgb(0.85, *rgb("#081c38"))
    g.add_color_stop_rgb(1, *rgb("#040d1c"))
    cr.set_source(g)
    cr.paint()
    # sunburst – jemné paprsky
    for i in range(720):
        a0 = math.radians(i * 0.5)
        a1 = math.radians(i * 0.5 + 0.25)
        cr.move_to(C, C)
        cr.arc(C, C, C, a0, a1)
        cr.close_path()
        light = (math.sin(a0 * 2 + 0.6) + 1) / 2          # dvě světlé „odlesky“ jako u kovu
        cr.set_source_rgba(1, 1, 1, 0.018 + 0.05 * light ** 3)
        cr.fill()
    # odlesk přes ciferník
    g = cairo.LinearGradient(0, 0, S, S)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.07)
    g.add_color_stop_rgba(0.5, 1, 1, 1, 0.0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.18)
    cr.set_source(g)
    cr.paint()

    # rehaut (šikmý vnější kroužek) s minutovou stupnicí
    cr.set_line_width(26)
    g = cairo.LinearGradient(0, 0, 0, S)
    g.add_color_stop_rgb(0, *rgb("#0a1e3a"))
    g.add_color_stop_rgb(1, *rgb("#030a15"))
    cr.set_source(g)
    cr.arc(C, C, 227, 0, 2 * math.pi)
    cr.stroke()
    cr.set_line_width(1.2)
    cr.set_source_rgba(1, 1, 1, 0.25)
    cr.arc(C, C, 213.5, 0, 2 * math.pi)
    cr.stroke()
    for i in range(240):                       # čtvrtsekundy
        if i % 4 == 0:
            continue
        x0, y0 = polar(C, C, 228, i * 1.5)
        x1, y1 = polar(C, C, 233, i * 1.5)
        cr.set_source_rgba(1, 1, 1, 0.35)
        cr.set_line_width(0.8)
        cr.move_to(x0, y0)
        cr.line_to(x1, y1)
        cr.stroke()
    for i in range(60):
        big = i % 5 == 0
        x0, y0 = polar(C, C, 216 if big else 221, i * 6)
        x1, y1 = polar(C, C, 235, i * 6)
        cr.set_source_rgba(1, 1, 1, 0.95 if big else 0.75)
        cr.set_line_width(3 if big else 1.6)
        cr.move_to(x0, y0)
        cr.line_to(x1, y1)
        cr.stroke()

    # aplikované indexy (ocel + luminiscence) se stínem
    idx, ci = new()
    for h in range(12):
        deg = h * 30
        offs = [-6.5, 6.5] if h == 0 else [0]
        for o in offs:
            ci.save()
            ci.translate(C, C)
            ci.rotate(math.radians(deg))
            ci.translate(o, 0)
            w, r0, r1 = (9, -211, -186) if h != 0 else (8, -211, -184)
            rr(ci, -w / 2, r0, w, r1 - r0, 2)
            g = cairo.LinearGradient(-w / 2, 0, w / 2, 0)
            g.add_color_stop_rgb(0, 0.95, 0.96, 0.98)
            g.add_color_stop_rgb(0.5, 0.62, 0.65, 0.70)
            g.add_color_stop_rgb(1, 0.35, 0.37, 0.42)
            ci.set_source(g)
            ci.fill()
            rr(ci, -w / 2 + 2, r0 + 2, w - 4, r1 - r0 - 4, 1)
            ci.set_source_rgb(*LUME)
            ci.fill()
            ci.restore()
    cr.set_source_surface(blur_shadow(idx, 3, 0.7, 1, 2), 0, 0)
    cr.paint()
    cr.set_source_surface(idx, 0, 0)
    cr.paint()

    # číslice
    for h in range(1, 13):
        if h in (3, 6, 9, 11, 12, 1):          # místo nich subdialy a nahoře datum
            continue
        x, y = polar(C, C, 160, h * 30)
        text(cr, str(h), x + 1, y + 2, 36, (0, 0, 0), alpha=0.45)
        text(cr, str(h), x, y, 36, (0.96, 0.96, 0.94))

    # subdialy
    subdial(cr, *SUBS["chata"], kind="chata")
    subdial(cr, *SUBS["bat"], kind="bat")
    subdial(cr, *SUBS["temp"], kind="temp")

    # vnitřní stín u okraje (hloubka pod sklíčkem)
    g = cairo.RadialGradient(C, C, 200, C, C, C)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.55)
    cr.set_source(g)
    cr.paint()
    return s


def rr(cr, x, y, w, h, r):
    if h < 0:
        y, h = y + h, -h
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def val_deg(v, lo, hi):
    return -SWEEP + 2 * SWEEP * (v - lo) / (hi - lo)


def arc_deg(cr, cx, cy, r, d0, d1):
    cr.arc(cx, cy, r, math.radians(d0 - 90), math.radians(d1 - 90))


def subdial(cr, cx, cy, kind):
    R = SUB_R
    # zapuštění: tmavší kruh se stínem
    g = cairo.RadialGradient(cx, cy - 10, 5, cx, cy, R)
    g.add_color_stop_rgb(0, *rgb("#0d2a52"))
    g.add_color_stop_rgb(1, *rgb("#06152b"))
    cr.arc(cx, cy, R, 0, 2 * math.pi)
    cr.set_source(g)
    cr.fill()
    # azuráž (soustředné kroužky)
    for r in range(3, R, 2):
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.set_source_rgba(1, 1, 1, 0.045 if r % 4 == 1 else 0.0)
        cr.set_line_width(1)
        cr.stroke()
    # vnitřní stín nahoře (zapuštěno)
    g = cairo.LinearGradient(cx, cy - R, cx, cy + R)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.45)
    g.add_color_stop_rgba(0.35, 0, 0, 0, 0)
    cr.arc(cx, cy, R, 0, 2 * math.pi)
    cr.set_source(g)
    cr.fill()
    # ocelový okraj
    g = cairo.LinearGradient(cx - R, cy - R, cx + R, cy + R)
    g.add_color_stop_rgb(0, 0.92, 0.93, 0.95)
    g.add_color_stop_rgb(0.5, 0.55, 0.58, 0.64)
    g.add_color_stop_rgb(1, 0.25, 0.27, 0.31)
    cr.set_source(g)
    cr.set_line_width(3)
    cr.arc(cx, cy, R + 0.5, 0, 2 * math.pi)
    cr.stroke()

    if kind == "chata":
        lo, hi = 11.6, 13.0
        zones = [(11.6, 12.0, rgb("#ff4b3e")), (12.0, 12.2, rgb("#ffb020")), (12.6, 13.0, rgb("#3ddc84"))]
        minor = [lo + i * 0.1 for i in range(15)]
        major = [11.6, 12.0, 12.5, 13.0]
        labels = {}
        title = "CHATA"
    elif kind == "bat":
        lo, hi = 0, 100
        zones = [(0, 15, rgb("#ff4b3e"))]
        minor = list(range(0, 101, 5))
        major = [0, 25, 50, 75, 100]
        labels = {}
        title = "HODINKY"
    else:
        lo, hi = -20, 40
        zones = [(-20, 0, rgb("#4aa8ff"))]
        minor = list(range(-20, 41, 5))
        major = [-20, 0, 20, 40]
        labels = {}
        title = "°C"
    for a, b, col in zones:
        cr.set_line_width(3.2)
        cr.set_source_rgba(*col, 0.95)
        arc_deg(cr, cx, cy, R - 6, val_deg(a, lo, hi), val_deg(b, lo, hi))
        cr.stroke()
    for v in minor:
        d = val_deg(v, lo, hi)
        mj = any(abs(v - m) < 1e-6 for m in major)
        x0, y0 = polar(cx, cy, R - (13 if mj else 10), d)
        x1, y1 = polar(cx, cy, R - 4, d)
        cr.set_source_rgba(1, 1, 1, 0.95 if mj else 0.6)
        cr.set_line_width(1.8 if mj else 0.9)
        cr.move_to(x0, y0)
        cr.line_to(x1, y1)
        cr.stroke()
    for v, t in labels.items():
        x, y = polar(cx, cy, R - 26, val_deg(v, lo, hi))
        text(cr, t, x, y, 10, (0.9, 0.92, 0.95), weight=cairo.FONT_WEIGHT_BOLD)
    text(cr, title, cx, cy - 25, 13, (0.82, 0.86, 0.92), spacing=1.0)


# ---------------------------------------------------------------- ručky
def hand(length, width, tail, lume=True, color=None, name=""):
    """Masivní mečová ručka: fazetovaná ocel (světlá / tmavá polovina) + luminiscenční vložka.
    Obrázek má výšku 2*length, osa otáčení je přesně uprostřed."""
    W, H = int(width + 16), int(2 * length + 8)
    cx, cy = W / 2, H / 2
    body, cr = new(W, H)

    def outline(c, inset=0.0):
        hw = width / 2 - inset
        tip = cy - length + inset * 2.2
        c.move_to(cx, tip)
        c.line_to(cx + hw, cy - length * 0.62)
        c.line_to(cx + hw * 0.62, cy + tail - inset)
        c.line_to(cx - hw * 0.62, cy + tail - inset)
        c.line_to(cx - hw, cy - length * 0.62)
        c.close_path()

    outline(cr)
    cr.clip()
    g = cairo.LinearGradient(cx - width / 2, 0, cx + width / 2, 0)
    if color:
        g.add_color_stop_rgb(0, *[min(1, c * 1.15) for c in color])
        g.add_color_stop_rgb(0.5, *color)
        g.add_color_stop_rgb(1, *[c * 0.6 for c in color])
    else:
        g.add_color_stop_rgb(0, 0.97, 0.98, 1.0)
        g.add_color_stop_rgb(0.49, 0.80, 0.82, 0.86)
        g.add_color_stop_rgb(0.51, 0.42, 0.45, 0.50)
        g.add_color_stop_rgb(1, 0.30, 0.32, 0.37)
    cr.set_source(g)
    cr.paint()
    cr.reset_clip()
    if lume:
        hw = width / 2 - 5.5
        cr.move_to(cx, cy - length + 16)
        cr.line_to(cx + hw, cy - length * 0.62)
        cr.line_to(cx + hw * 0.5, cy - 30)
        cr.line_to(cx - hw * 0.5, cy - 30)
        cr.line_to(cx - hw, cy - length * 0.62)
        cr.close_path()
        cr.set_source_rgb(*LUME)
        cr.fill()
    # hrana
    outline(cr)
    cr.set_line_width(0.8)
    cr.set_source_rgba(0, 0, 0, 0.5)
    cr.stroke()
    out, co = new(W, H)
    co.set_source_surface(blur_shadow(body, 4, 0.75, 0, 0), 0, 0)
    co.paint()
    co.set_source_surface(body, 0, 0)
    co.paint()
    return out, W, H


def second_hand(length=212, tail=52):
    W, H = 28, int(2 * length + 8)
    cx, cy = W / 2, H / 2
    body, cr = new(W, H)
    cr.set_source_rgb(*ORANGE)
    # tenká ručka s hrotem
    cr.move_to(cx - 1.4, cy + tail)
    cr.line_to(cx - 1.1, cy - length + 14)
    cr.line_to(cx, cy - length)
    cr.line_to(cx + 1.1, cy - length + 14)
    cr.line_to(cx + 1.4, cy + tail)
    cr.close_path()
    cr.fill()
    # luminiscenční kosočtverec na konci
    cr.move_to(cx, cy - length + 6)
    cr.line_to(cx + 4.5, cy - length + 22)
    cr.line_to(cx, cy - length + 38)
    cr.line_to(cx - 4.5, cy - length + 22)
    cr.close_path()
    cr.fill_preserve()
    cr.set_source_rgb(*LUME)
    cr.set_line_width(0)
    cr.move_to(cx, cy - length + 11)
    cr.line_to(cx + 2.4, cy - length + 22)
    cr.line_to(cx, cy - length + 33)
    cr.line_to(cx - 2.4, cy - length + 22)
    cr.close_path()
    cr.fill()
    # protizávaží – kroužek
    cr.set_source_rgb(*ORANGE)
    cr.arc(cx, cy + tail - 10, 7, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgb(0.05, 0.1, 0.2)
    cr.arc(cx, cy + tail - 10, 3.2, 0, 2 * math.pi)
    cr.fill()
    # středová krytka (je součástí vteřinové ručky, aby vždy ležela nahoře)
    g = cairo.RadialGradient(cx - 2, cy - 2, 1, cx, cy, 8)
    g.add_color_stop_rgb(0, 1.0, 0.7, 0.5)
    g.add_color_stop_rgb(1, *[c * 0.8 for c in ORANGE])
    cr.set_source(g)
    cr.arc(cx, cy, 7.5, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgb(0.85, 0.87, 0.9)
    cr.arc(cx, cy, 2.6, 0, 2 * math.pi)
    cr.fill()
    out, co = new(W, H)
    co.set_source_surface(blur_shadow(body, 3, 0.7), 0, 0)
    co.paint()
    co.set_source_surface(body, 0, 0)
    co.paint()
    return out, W, H


def cap():
    """Ocelová krytka středu pod vteřinovou ručkou (pro ambient, kde vteřinovka není)."""
    s, cr = new(24, 24)
    g = cairo.RadialGradient(10, 10, 1, 12, 12, 10)
    g.add_color_stop_rgb(0, 0.98, 0.98, 1)
    g.add_color_stop_rgb(1, 0.4, 0.42, 0.48)
    cr.set_source(g)
    cr.arc(12, 12, 9, 0, 2 * math.pi)
    cr.fill()
    return s


def sub_needle(length=44, color=(0.95, 0.96, 0.98), name=""):
    W, H = 16, int(2 * length + 4)
    cx, cy = W / 2, H / 2
    body, cr = new(W, H)
    cr.move_to(cx, cy - length)
    cr.line_to(cx + 2.4, cy - 4)
    cr.line_to(cx + 2.4, cy + 10)
    cr.line_to(cx - 2.4, cy + 10)
    cr.line_to(cx - 2.4, cy - 4)
    cr.close_path()
    cr.set_source_rgb(*color)
    cr.fill()
    cr.set_source_rgb(*color)
    cr.arc(cx, cy, 4.5, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgb(0.2, 0.22, 0.26)
    cr.arc(cx, cy, 1.6, 0, 2 * math.pi)
    cr.fill()
    out, co = new(W, H)
    co.set_source_surface(blur_shadow(body, 2, 0.8), 0, 0)
    co.paint()
    co.set_source_surface(body, 0, 0)
    co.paint()
    return out, W, H


# ---------------------------------------------------------------- ambient (úsporný režim: skoro vše černé)
def amb_dial():
    s, cr = new()
    cr.set_source_rgb(0, 0, 0)
    cr.paint()
    for h in range(12):
        x0, y0 = polar(C, C, 212, h * 30)
        x1, y1 = polar(C, C, 196 if h % 3 else 188, h * 30)
        cr.set_source_rgba(0.75, 0.75, 0.75, 1)
        cr.set_line_width(2 if h % 3 else 3)
        cr.move_to(x0, y0)
        cr.line_to(x1, y1)
        cr.stroke()
    for k in ("chata",):
        cx, cy = SUBS[k]
        cr.set_source_rgba(0.45, 0.45, 0.45, 1)
        cr.set_line_width(1)
        cr.arc(cx, cy, SUB_R, 0, 2 * math.pi)
        cr.stroke()
        text(cr, "CHATA", cx, cy - 25, 13, (0.55, 0.55, 0.55), spacing=1.0)
    return s


def amb_hand(length, width, tail):
    W, H = int(width + 8), int(2 * length + 8)
    cx, cy = W / 2, H / 2
    s, cr = new(W, H)
    hw = width / 2
    cr.move_to(cx, cy - length)
    cr.line_to(cx + hw, cy - length * 0.62)
    cr.line_to(cx + hw * 0.62, cy + tail)
    cr.line_to(cx - hw * 0.62, cy + tail)
    cr.line_to(cx - hw, cy - length * 0.62)
    cr.close_path()
    cr.set_line_width(2)
    cr.set_source_rgb(0.85, 0.85, 0.85)
    cr.stroke()
    return s, W, H


HANDS = {}

# texty na ciferníku – stejné polohy používá watchface.xml
DATE_R, DATE_SIZE = 163, 28          # datum po obvodu nahoře
SUN_Y, SUN_SIZE = 128, 26            # východ / západ slunce
SUBTXT_DY, SUBTXT_SIZE = 28, 26      # číslo dole v subdialu


def curved(cr, s, r, size, color, spacing=1.0):
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(size)
    widths = [cr.text_extents(ch).x_advance + spacing for ch in s]
    total = sum(widths) - spacing
    a = -total / 2 / r
    for ch, w in zip(s, widths):
        mid = a + (w - spacing) / 2 / r
        cr.save()
        x, y = C + r * math.sin(mid), C - r * math.cos(mid)
        cr.translate(x, y)
        cr.rotate(mid)
        e = cr.text_extents(ch)
        cr.move_to(-e.x_advance / 2, size * 0.36)
        cr.set_source_rgb(*color)
        cr.show_text(ch)
        cr.restore()
        a += w / r


def place(cr, img, cx, cy, deg):
    w, h = img.get_width(), img.get_height()
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(math.radians(deg))
    cr.set_source_surface(img, -w / 2, -h / 2)
    cr.paint()
    cr.restore()


def preview(hh=10, mm=8, ss=34, volt=12.64, bat=72, temp=14, date="PONDĚLÍ 21/12", sun="↑ 7:20  ↓ 18:16", ambient=False, name="preview"):
    ld = lambda n: cairo.ImageSurface.create_from_png(os.path.join(OUT, n + ".png"))
    s, cr = new()
    cr.arc(C, C, C, 0, 2 * math.pi)
    cr.clip()
    if ambient:
        cr.set_source_surface(ld("amb_dial"), 0, 0); cr.paint()
        cx, cy = SUBS["chata"]
        text(cr, f"{volt:.2f}".replace(".", ","), cx, cy + 6, 30, (0.6, 0.6, 0.6))
        place(cr, ld("amb_hour"), C, C, (hh % 12 + mm / 60) * 30)
        place(cr, ld("amb_minute"), C, C, mm * 6 + ss / 10)
        place(cr, ld("cap"), C, C, 0)
    else:
        cr.set_source_surface(ld("dial"), 0, 0); cr.paint()
        curved(cr, date, DATE_R, DATE_SIZE, (0.92, 0.93, 0.95))
        text(cr, sun, C, SUN_Y, SUN_SIZE, (0.85, 0.88, 0.93), weight=cairo.FONT_WEIGHT_BOLD)
        for k, v, lo, hi, txt, nd in (("chata", volt, 11.6, 13.0, f"{volt:.2f}".replace(".", ","), "needle_chata"),
                                        ("bat", bat, 0, 100, f"{bat}%", "needle"),
                                        ("temp", temp, -20, 40, f"{temp}°", "needle")):
            cx, cy = SUBS[k]
            text(cr, txt, cx, cy + SUBTXT_DY, SUBTXT_SIZE, (1, 1, 1))
            place(cr, ld(nd), cx, cy, val_deg(max(lo, min(hi, v)), lo, hi))
        place(cr, ld("hand_hour"), C, C, (hh % 12 + mm / 60) * 30)
        place(cr, ld("hand_minute"), C, C, mm * 6 + ss / 10)
        place(cr, ld("hand_second"), C, C, ss * 6)
    save(s, name)


def main():
    save(dial(), "dial")
    h, W, H = hand(125, 30, 24)
    save(h, "hand_hour"); HANDS["hour"] = (W, H)
    m, W, H = hand(200, 24, 28)
    save(m, "hand_minute"); HANDS["minute"] = (W, H)
    sc, W, H = second_hand()
    save(sc, "hand_second"); HANDS["second"] = (W, H)
    save(cap(), "cap")
    n, W, H = sub_needle(44)
    save(n, "needle"); HANDS["needle"] = (W, H)
    n2, W, H = sub_needle(44, ORANGE)
    save(n2, "needle_chata"); HANDS["needle_chata"] = (W, H)
    save(amb_dial(), "amb_dial")
    a, W, H = amb_hand(125, 30, 24)
    save(a, "amb_hour"); HANDS["amb_hour"] = (W, H)
    a, W, H = amb_hand(200, 24, 28)
    save(a, "amb_minute"); HANDS["amb_minute"] = (W, H)
    for k, v in HANDS.items():
        print(k, v)
    preview()


if __name__ == "__main__":
    main()
