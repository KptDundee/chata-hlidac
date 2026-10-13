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

# tři stejné subdialy do trojúhelníku (vlevo nahoře, vpravo nahoře, dole)
SUB_D, SUB_R = 100, 76
SUBS = {"chata": (C - SUB_D * math.sin(math.radians(60)), C - SUB_D / 2),
        "bat": (C + SUB_D * math.sin(math.radians(60)), C - SUB_D / 2),
        "temp": (C, C + SUB_D)}
SWEEP = 135          # ukazatel subdialu: −135° … +135° (270°), dole mezera
MARK_R = SUB_R - 14  # poloměr špičky trojúhelníku

# texty – stejné polohy používá watchface.xml
DIALFONT = "Saira Expanded Chata"        # široké „zploštělé“ písmo Saira (wdth 125, wght 600; SIL OFL) – i na hodinkách (res/font/saira.ttf)
SUN_Y, SUN_SIZE = 100, 26                # nejbližší východ / západ, nahoře
DAY_POS, DATE_POS, DD_SIZE = (118, 300), (362, 300), 26   # den vlevo dole, datum vpravo dole
NUM_SIZE = 32                            # číslo uprostřed subdialu
NUMERALS = (12, 1, 3, 4, 5, 7, 8, 9, 11) # hodinové číslice (kromě míst se subdialy)
NUM_R, NUM_SIZE_DIAL = 184, 32

# barvy
LUME = (0.93, 0.91, 0.82)
ORANGE = (1.0, 0.33, 0.06)


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


# ---------------------------------------------------------------- ikonky
def icon_house(cr, x, y, s, col):
    cr.save(); cr.translate(x, y); cr.scale(s / 24, s / 24)
    cr.move_to(-12, -1); cr.line_to(0, -12); cr.line_to(12, -1)
    cr.set_line_width(2.6); cr.set_line_join(cairo.LINE_JOIN_ROUND); cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_source_rgb(*col); cr.stroke()
    cr.rectangle(-8, -3, 16, 13); cr.fill()
    cr.set_source_rgba(0, 0, 0, 0.55); cr.rectangle(-2.5, 3, 5, 7); cr.fill()
    cr.restore()


def icon_battery(cr, x, y, s, col):
    cr.save(); cr.translate(x, y); cr.scale(s / 24, s / 24)
    rr(cr, -12, -7, 21, 14, 2.5); cr.set_line_width(2.2); cr.set_source_rgb(*col); cr.stroke()
    cr.rectangle(9.5, -3, 3, 6); cr.fill()
    cr.move_to(1, -6); cr.line_to(-5, 1); cr.line_to(-0.5, 1); cr.line_to(-2, 6); cr.line_to(4, -1); cr.line_to(-0.5, -1); cr.close_path()
    cr.fill()
    cr.restore()


def icon_thermo(cr, x, y, s, col):
    cr.save(); cr.translate(x, y); cr.scale(s / 24, s / 24)
    cr.set_source_rgb(*col); cr.set_line_width(2.2)
    rr(cr, -3.5, -12, 7, 16, 3.5); cr.stroke()
    cr.arc(0, 7, 5.5, 0, 2 * math.pi); cr.fill()
    cr.rectangle(-1.3, -6, 2.6, 10); cr.fill()
    cr.restore()


def icon_sun(cr, x, y, s, col, up):
    """Stejná ikonka jako v aplikaci (ic_sunrise / ic_sunset): slunce na obzoru + šipka."""
    cr.save(); cr.translate(x - s / 2, y - s / 2); cr.scale(s / 24, s / 24)
    cr.set_source_rgb(*col)
    cr.rectangle(1, 20.2, 22, 1.8); cr.fill()
    cr.arc(12, 20.2, 5.8, math.pi, 2 * math.pi); cr.close_path(); cr.fill()
    pts = [(12, 0.5), (18, 7.2), (14, 7.2), (14, 12.6), (10, 12.6), (10, 7.2), (6, 7.2)] if up else \
          [(12, 13.2), (18, 6.5), (14, 6.5), (14, 0.8), (10, 0.8), (10, 6.5), (6, 6.5)]
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path(); cr.fill()
    cr.restore()


ICONS = {"chata": icon_house, "bat": icon_battery, "temp": icon_thermo}


# ---------------------------------------------------------------- ciferník
def dial():
    s, cr = new()
    cr.arc(C, C, C, 0, 2 * math.pi)
    cr.clip()
    # základ: hluboká tmavá modř, k okraji do černa
    g = cairo.RadialGradient(C, C, 0, C, C, C)
    g.add_color_stop_rgb(0, *rgb("#14427c"))
    g.add_color_stop_rgb(0.40, *rgb("#0c2b56"))
    g.add_color_stop_rgb(0.75, *rgb("#061630"))
    g.add_color_stop_rgb(1, *rgb("#01050c"))
    cr.set_source(g)
    cr.paint()
    # sunburst: jemné paprsky + světlo dopadající šikmo (dvě světlé výseče na úhlopříčce, kolmo tmavé)
    import random
    rnd = random.Random(7)
    for i in range(1440):
        a = i * 0.25
        a0, a1 = math.radians(a - 90), math.radians(a - 90 + 0.25)
        lobe = abs(math.cos(math.radians(a - 45))) ** 6          # světlo ze směru 45° / 225°
        cr.move_to(C, C)
        cr.arc(C, C, C, a0, a1)
        cr.close_path()
        n = rnd.random()
        cr.set_source_rgba(0.75, 0.86, 1.0, 0.012 + 0.16 * lobe * (0.75 + 0.5 * n))
        cr.fill()
        cr.move_to(C, C)
        cr.arc(C, C, C, a0, a1)
        cr.close_path()
        cr.set_source_rgba(0, 0, 0, 0.28 * (1 - lobe) ** 2 * (0.8 + 0.4 * n))
        cr.fill()
    # střed světlejší, okraj tmavý (hloubka)
    g = cairo.RadialGradient(C, C, 40, C, C, C)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.05)
    g.add_color_stop_rgba(0.55, 0, 0, 0, 0.0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.55)
    cr.set_source(g)
    cr.paint()

    # rehaut – šikmý vnější kroužek: nahoře vlevo světlejší, dole vpravo tmavší
    for i in range(360):
        a0, a1 = math.radians(i - 90), math.radians(i + 1.2 - 90)
        lit = (math.cos(math.radians(i + 45)) + 1) / 2         # světlo zleva nahoře
        cr.set_line_width(30)
        cr.set_source_rgb(0.02 + 0.05 * lit, 0.035 + 0.07 * lit, 0.07 + 0.11 * lit)
        cr.arc(C, C, 224, a0, a1)
        cr.stroke()
    cr.set_line_width(4)                        # stín rehautu na ciferníku
    cr.set_source_rgba(0, 0, 0, 0.55)
    cr.arc(C, C, 207, 0, 2 * math.pi)
    cr.stroke()
    cr.set_line_width(1)
    cr.set_source_rgba(1, 1, 1, 0.28)
    cr.arc(C, C, 209.5, 0, 2 * math.pi)
    cr.stroke()
    for i in range(240):                        # čtvrtsekundy
        if i % 4 == 0:
            continue
        x0, y0 = polar(C, C, 230, i * 1.5)
        x1, y1 = polar(C, C, 235, i * 1.5)
        cr.set_source_rgba(1, 1, 1, 0.28)
        cr.set_line_width(0.8)
        cr.move_to(x0, y0); cr.line_to(x1, y1); cr.stroke()
    for i in range(60):                         # minuty
        if i % 5 == 0:
            continue
        x0, y0 = polar(C, C, 221, i * 6)
        x1, y1 = polar(C, C, 236, i * 6)
        cr.set_source_rgba(1, 1, 1, 0.82)
        cr.set_line_width(1.8)
        cr.move_to(x0, y0); cr.line_to(x1, y1); cr.stroke()

    # aplikované prvky (hodinové čárky + číslice) – vrhají stín
    app, ca = new()
    for h in range(12):
        ca.save()
        ca.translate(C, C)
        ca.rotate(math.radians(h * 30))
        w = 10 if h else 14
        rr(ca, -w / 2, -238, w, 28, 2)
        g = cairo.LinearGradient(-w / 2, 0, w / 2, 0)
        g.add_color_stop_rgb(0, 0.98, 0.98, 1.0)
        g.add_color_stop_rgb(0.45, 0.80, 0.82, 0.86)
        g.add_color_stop_rgb(0.55, 0.45, 0.48, 0.53)
        g.add_color_stop_rgb(1, 0.30, 0.32, 0.36)
        ca.set_source(g); ca.fill()
        rr(ca, -w / 2 + 2.4, -235.5, w - 4.8, 23, 1)
        ca.set_source_rgb(*LUME); ca.fill()
        ca.restore()
    for h in NUMERALS:
        x, y = polar(C, C, NUM_R, h * 30)
        num3d(ca, str(h), x, y, NUM_SIZE_DIAL)
    cr.set_source_surface(blur_shadow(app, 3, 0.85, 2, 3), 0, 0); cr.paint()
    cr.set_source_surface(app, 0, 0); cr.paint()

    for k in SUBS:
        subdial(cr, *SUBS[k], kind=k)
    return s


ZONES = {"chata": (11.6, 13.0, [(11.6, 12.0, "#ff4b3e"), (12.0, 12.2, "#ffb020"), (12.6, 13.0, "#3ddc84")], 0.1, 0.5),
         "bat": (0, 100, [(0, 15, "#ff4b3e")], 5, 25),
         "temp": (-20, 40, [(-20, 0, "#4aa8ff")], 5, 10)}


def subdial(cr, cx, cy, kind):
    R = SUB_R
    # vrhaný stín vystouplé obruby na ciferník
    sh, cs = new()
    cs.arc(cx, cy, R + 4, 0, 2 * math.pi); cs.set_source_rgb(0, 0, 0); cs.fill()
    cr.set_source_surface(blur_shadow(sh, 5, 0.9, 2, 4), 0, 0); cr.paint()
    # zapuštěná plocha
    g = cairo.RadialGradient(cx + 10, cy + 14, 4, cx, cy, R)
    g.add_color_stop_rgb(0, *rgb("#0f2f5c"))
    g.add_color_stop_rgb(0.7, *rgb("#081d3d"))
    g.add_color_stop_rgb(1, *rgb("#030b19"))
    cr.arc(cx, cy, R, 0, 2 * math.pi); cr.set_source(g); cr.fill()
    # azuráž s úhlovým leskem (soustředné drážky lesknou se jen v pruhu ke světlu)
    for r in range(3, R - 2, 2):
        for k in range(36):
            a = k * 10
            lit = abs(math.cos(math.radians(a - 45))) ** 4
            cr.arc(cx, cy, r, math.radians(a - 90), math.radians(a - 80))
            cr.set_source_rgba(0.8, 0.9, 1, 0.02 + 0.09 * lit)
            cr.set_line_width(0.9)
            cr.stroke()
    # vnitřní stín (hloubka): od horního levého okraje
    g = cairo.RadialGradient(cx + 8, cy + 10, R * 0.55, cx, cy, R + 2)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.75)
    cr.arc(cx, cy, R, 0, 2 * math.pi); cr.set_source(g); cr.fill()
    # leštěná obruba – světlo zleva nahoře
    for i in range(360):
        lit = (math.cos(math.radians(i + 45)) + 1) / 2
        v = 0.25 + 0.72 * lit ** 1.5
        cr.set_source_rgb(v * 0.95, v * 0.97, v)
        cr.set_line_width(5)
        cr.arc(cx, cy, R + 1.5, math.radians(i - 90), math.radians(i - 88.8))
        cr.stroke()
    cr.set_line_width(1)
    cr.set_source_rgba(0, 0, 0, 0.7)
    cr.arc(cx, cy, R - 1.2, 0, 2 * math.pi); cr.stroke()
    lo, hi, zones, step, major = ZONES[kind]
    for a, b, col in zones:
        cr.set_line_width(4)
        cr.set_source_rgba(*rgb(col), 0.95)
        arc_deg(cr, cx, cy, R - 7, val_deg(a, lo, hi), val_deg(b, lo, hi)); cr.stroke()
    n = int(round((hi - lo) / step))
    for i in range(n + 1):
        v = lo + i * step
        d = val_deg(v, lo, hi)
        mj = abs((v - lo) / major - round((v - lo) / major)) < 1e-6
        x0, y0 = polar(cx, cy, R - (15 if mj else 12), d)
        x1, y1 = polar(cx, cy, R - 4, d)
        cr.set_source_rgba(1, 1, 1, 0.95 if mj else 0.55)
        cr.set_line_width(2 if mj else 1)
        cr.move_to(x0, y0); cr.line_to(x1, y1); cr.stroke()
    ICONS[kind](cr, cx, cy - 33, 24, (0.82, 0.86, 0.92))


def marker(color):
    """Trojúhelník, který jezdí po obvodu subdialu (místo ručičky). Obrázek 2R × 2R, otáčí se kolem středu."""
    W = 2 * SUB_R
    body, cr = new(W, W)
    c = SUB_R
    tip = c - MARK_R
    cr.move_to(c, tip)
    cr.line_to(c + 10, tip + 18)
    cr.line_to(c - 10, tip + 18)
    cr.close_path()
    g = cairo.LinearGradient(c - 7, 0, c + 7, 0)
    g.add_color_stop_rgb(0, *[min(1, x * 1.15) for x in color])
    g.add_color_stop_rgb(0.5, *color)
    g.add_color_stop_rgb(1, *[x * 0.65 for x in color])
    cr.set_source(g)
    cr.fill()
    out, co = new(W, W)
    co.set_source_surface(blur_shadow(body, 2, 0.9), 0, 0); co.paint()
    co.set_source_surface(body, 0, 0); co.paint()
    return out


def num3d(cr, t, x, y, size):
    """Aplikovaná kovová číslice: světlá hrana nahoře, tmavší dole, tenký obrys."""
    cr.select_font_face(DIALFONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    e = cr.text_extents(t)
    x0, y0 = x - e.x_advance / 2, y - (e.y_bearing + e.height / 2)
    cr.move_to(x0, y0)
    cr.text_path(t)
    g = cairo.LinearGradient(0, y - e.height / 2, 0, y + e.height / 2)
    g.add_color_stop_rgb(0, 1.0, 1.0, 1.0)
    g.add_color_stop_rgb(0.5, 0.90, 0.91, 0.93)
    g.add_color_stop_rgb(0.52, 0.72, 0.74, 0.78)
    g.add_color_stop_rgb(1, 0.86, 0.87, 0.90)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_line_width(0.8)
    cr.set_source_rgba(0.1, 0.12, 0.16, 0.8)
    cr.stroke()


def glare():
    """Diagonální odlesk sklíčka pod 45° přes střed (kreslí se nad ručkami, v úsporném režimu zmizí)."""
    s, cr = new()
    cr.arc(C, C, C, 0, 2 * math.pi)
    cr.clip()
    cr.translate(C, C)
    cr.rotate(math.radians(45))                 # pruh „/“ – zleva dole doprava nahoru
    g = cairo.LinearGradient(-C, 0, C, 0)
    g.add_color_stop_rgba(0.00, 1, 1, 1, 0.0)
    g.add_color_stop_rgba(0.30, 1, 1, 1, 0.0)
    g.add_color_stop_rgba(0.42, 1, 1, 1, 0.07)
    g.add_color_stop_rgba(0.47, 1, 1, 1, 0.13)
    g.add_color_stop_rgba(0.50, 1, 1, 1, 0.18)
    g.add_color_stop_rgba(0.53, 1, 1, 1, 0.12)
    g.add_color_stop_rgba(0.60, 1, 1, 1, 0.04)
    g.add_color_stop_rgba(0.70, 1, 1, 1, 0.0)
    g.add_color_stop_rgba(1.00, 1, 1, 1, 0.0)
    cr.set_source(g)
    cr.rectangle(-S, -S, 2 * S, 2 * S)
    cr.fill()
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


def second_hand(length=214, tail=58):
    W, H = 34, int(2 * length + 8)
    cx, cy = W / 2, H / 2
    body, cr = new(W, H)
    col = ORANGE
    cr.set_source_rgb(*col)
    cr.move_to(cx - 2.2, cy + tail)
    cr.line_to(cx - 1.6, cy - length + 16)
    cr.line_to(cx, cy - length)
    cr.line_to(cx + 1.6, cy - length + 16)
    cr.line_to(cx + 2.2, cy + tail)
    cr.close_path()
    cr.fill()
    # kosočtverec se svítící hmotou
    cr.move_to(cx, cy - length + 4)
    cr.line_to(cx + 6.5, cy - length + 26)
    cr.line_to(cx, cy - length + 48)
    cr.line_to(cx - 6.5, cy - length + 26)
    cr.close_path()
    cr.fill()
    cr.move_to(cx, cy - length + 11)
    cr.line_to(cx + 3.6, cy - length + 26)
    cr.line_to(cx, cy - length + 41)
    cr.line_to(cx - 3.6, cy - length + 26)
    cr.close_path()
    cr.set_source_rgb(*LUME)
    cr.fill()
    # protizávaží
    cr.set_source_rgb(*col)
    cr.arc(cx, cy + tail - 12, 9, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgb(*LUME)
    cr.arc(cx, cy + tail - 12, 4.5, 0, 2 * math.pi)
    cr.fill()
    # středová krytka
    g = cairo.RadialGradient(cx - 2.5, cy - 2.5, 1, cx, cy, 10)
    g.add_color_stop_rgb(0, 1.0, 0.75, 0.55)
    g.add_color_stop_rgb(1, *[c * 0.75 for c in col])
    cr.set_source(g)
    cr.arc(cx, cy, 9, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgb(0.85, 0.87, 0.9)
    cr.arc(cx, cy, 3, 0, 2 * math.pi)
    cr.fill()
    out, co = new(W, H)
    co.set_source_surface(blur_shadow(body, 3, 0.9, 1, 2), 0, 0)
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




# ---------------------------------------------------------------- ambient (úsporný režim: skoro vše černé)
def amb_dial():
    s, cr = new()
    cr.set_source_rgb(0, 0, 0)
    cr.paint()
    for h in range(12):
        x0, y0 = polar(C, C, 234, h * 30)
        x1, y1 = polar(C, C, 214, h * 30)
        cr.set_source_rgb(0.7, 0.7, 0.7)
        cr.set_line_width(4 if h == 0 else 2.5)
        cr.move_to(x0, y0); cr.line_to(x1, y1); cr.stroke()
    cx, cy = SUBS["chata"]
    cr.set_source_rgb(0.35, 0.35, 0.35)
    cr.set_line_width(1.2)
    cr.arc(cx, cy, SUB_R, 0, 2 * math.pi); cr.stroke()
    icon_house(cr, cx, cy - 33, 24, (0.5, 0.5, 0.5))
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


def place(cr, img, cx, cy, deg):
    w, h = img.get_width(), img.get_height()
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(math.radians(deg))
    cr.set_source_surface(img, -w / 2, -h / 2)
    cr.paint()
    cr.restore()




def preview(hh=10, mm=8, ss=34, volt=12.64, bat=72, temp=14, day="PO", date="21/12", sun="↓ 18:16", ambient=False, name="preview"):
    ld = lambda n: cairo.ImageSurface.create_from_png(os.path.join(OUT, n + ".png"))
    s, cr = new()
    cr.arc(C, C, C, 0, 2 * math.pi)
    cr.clip()
    if True:
        cr.set_source_surface(ld("dial"), 0, 0); cr.paint()
        arrow, tm = sun.split(" ", 1)
        icon_sun(cr, 110 + 58 + 18, SUN_Y, 36, (0.88, 0.91, 0.95), arrow == "↑")
        cr.select_font_face(DIALFONT); cr.set_font_size(SUN_SIZE)
        text(cr, tm, 212 + cr.text_extents(tm).x_advance / 2, SUN_Y, SUN_SIZE, (0.88, 0.91, 0.95), family=DIALFONT, weight=cairo.FONT_WEIGHT_NORMAL)
        text(cr, day, *DAY_POS, DD_SIZE, (0.92, 0.93, 0.95), family=DIALFONT, weight=cairo.FONT_WEIGHT_NORMAL)
        text(cr, date, *DATE_POS, DD_SIZE, (0.92, 0.93, 0.95), family=DIALFONT, weight=cairo.FONT_WEIGHT_NORMAL)
        for k, v, lo, hi, txt, mk in (("chata", volt, 11.6, 13.0, f"{volt:.1f}".replace(".", ","), "marker_chata"),
                                        ("bat", bat, 0, 100, f"{bat}%", "marker"),
                                        ("temp", temp, -20, 40, f"{temp}°", "marker")):
            cx, cy = SUBS[k]
            text(cr, txt, cx, cy + 6, NUM_SIZE, (1, 1, 1), family=DIALFONT, weight=cairo.FONT_WEIGHT_NORMAL)
            place(cr, ld(mk), cx, cy, val_deg(max(lo, min(hi, v)), lo, hi))
        place(cr, ld("hand_hour"), C, C, (hh % 12 + mm / 60) * 30)
        place(cr, ld("hand_minute"), C, C, mm * 6 + ss / 10)
        if ambient:                            # úsporný režim: stejný ciferník, jen bez vteřinovky
            place(cr, ld("cap"), C, C, 0)
        else:
            place(cr, ld("hand_second"), C, C, ss * 6)
        cr.set_source_surface(ld("glare"), 0, 0); cr.paint()
    save(s, name)


def main():
    save(dial(), "dial")
    save(glare(), "glare")
    save(marker((0.96, 0.97, 0.99)), "marker")
    save(marker(ORANGE), "marker_chata")
    h, W, H = hand(125, 30, 24)
    save(h, "hand_hour"); HANDS["hour"] = (W, H)
    m, W, H = hand(200, 24, 28)
    save(m, "hand_minute"); HANDS["minute"] = (W, H)
    sc, W, H = second_hand()
    save(sc, "hand_second"); HANDS["second"] = (W, H)
    save(cap(), "cap")
    for up, nm in ((True, "sun_up"), (False, "sun_down")):     # ikonky východ / západ (72 px, na ciferníku 36)
        ic, ci = new(72, 72)
        icon_sun(ci, 36, 36, 68, (0.88, 0.91, 0.95), up)
        save(ic, nm)
    for k, v in HANDS.items():
        print(k, v)
    for k, v in SUBS.items():
        print(k, [round(x, 1) for x in v])
    preview()


if __name__ == "__main__":
    main()
