"""Genera tiles.png: sprites en pixel art (16x16) + letras para el texto del juego.
Solo hace falta ejecutarlo si quieres modificar los gráficos:  pip install pillow  y  python make_tiles.py

Distribución: hoja de 16x16 tiles. Los tiles 0-223 son texto (códigos 32-255) y
los tiles 224+ son sprites (códigos privados U+E000 + n). Edita los dibujos de SPRITES abajo.
"""
import os
import random
from PIL import Image, ImageDraw, ImageFont

T = 16
PAL = {"k": (24, 18, 36), "w": (245, 245, 255), "g": (176, 182, 204), "G": (112, 118, 144), "s": (240, 196, 150),
       "r": (214, 48, 72), "R": (140, 24, 48), "c": (8, 230, 240), "b": (60, 110, 220), "B": (30, 60, 140),
       "y": (255, 210, 63), "Y": (200, 150, 30), "n": (150, 95, 50), "N": (90, 55, 30), "o": (110, 175, 80),
       "O": (60, 110, 50), "l": (130, 175, 95), "L": (72, 112, 62), "p": (190, 90, 255), "P": (110, 40, 170),
       "m": (240, 226, 170), "e": (255, 255, 255)}

SPRITES = {  # nombre: 16 filas de 16 caracteres ('.' = transparente)
    "player": ["................", "......kkkk......", ".....kggggk.....", "....kggGGggk....", "....kgccccgk....",
               "....kkggggkk....", "...kkbbbbbbkk...", "..krkbBbbBbkrk..", "..krkbbyybbkrk..", "..krkbbbbbbkrk..",
               "...kkbbbbbbkk...", "....kbbkkbbk....", "....kBBk.kBBk...", "....kggk.kggk...", "...kkkkk.kkkkk..", "................"],
    "orc": ["................", ".....kkkkkk.....", "....kooooook....", "...kooyooyook...", "...kooooooook...",
            "...kookwwkook...", "....kooooook....", "..kkNNNNNNNkk...", ".kooknnnnnkook..", ".kooknnnnnkook..",
            "..kkknnnnnkkk...", "....kNNkkNNk....", "....kook.kook...", "....kook.kook...", "...kkkkk.kkkkk..", "................"],
    "troll": ["..k..........k..", "..kk.kkkkkk.kk..", "...kkllllllkk...", "..kllrllllrllk..", "..kllllllllllk..",
              "..klkwlwwlwlk...", "...kllllllllk...", ".kkkLLLLLLLLkkk.", "kllkLLnnnnLLkllk", "kllkLnnnnnnLkllk",
              "kllkLLnnnnLLkllk", ".kkkkLLLLLLkkkk.", "...kLLk..kLLk...", "...kLLk..kLLk...", "..kkkkk..kkkkk..", "................"],
    "potion": ["................", "......kkkk......", "......kwwk......", "......kwwk......", "....kwwwwwwk....",
               "...kppppppppk...", "..kpewpppppPPk..", "..kppppppppPPk..", "..kppppppppPPk..", "..kpppppppPPPk..",
               "...kPPPPPPPPk...", "....kkkkkkkk....", "................", "................", "................", "................"],
    "scroll": ["................", "...kkkkkkkkkk...", "..kmmmmmmmmmmk..", "..kmkkkkkkkkmk..", "..kmmmmmmmmmmk..",
               "..kmkkkkkkmmmk..", "..kmmmmmmmmmmk..", "..kmkkkkkkkkmk..", "..kmmmmrrmmmmk..", "...kmmmrrmmmk...",
               "....kkkkkkkk....", "................", "................", "................", "................", "................"],
    "weapon": ["..............kk", ".............kwk", "............kwgk", "...........kwgk.", "..........kwgk..",
               ".........kwgk...", "..k.....kwgk....", "..kyk..kwgk.....", "...kykkwgk......", "....kyyyk.......",
               "..kyk.kyk.......", ".knk....k.......", "knk.............", "kk..............", "................", "................"],
    "armor": ["................", "..kkk......kkk..", ".kgggkkkkkkgggk.", ".kgggggkkgggggk.", "..kgggbbbbgggk..",
              "..kggbbbbbbggk..", "..kggbbyybbggk..", "..kggbbbbbbggk..", "...kgbbbbbbgk...", "...kggbbbbggk...",
              "....kgGggGgk....", "....kkkkkkkk....", "................", "................", "................", "................"],
}


def sprite(rows):
    im = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row.ljust(T, ".")[:T]):
            if ch != ".":
                im.putpixel((x, y), PAL[ch] + (255,))
    return im


def floor(variant):
    rnd = random.Random(variant)
    im = Image.new("RGBA", (T, T), (36, 32, 56, 255))
    d = ImageDraw.Draw(im)
    d.line([(0, 0), (T - 1, 0)], fill=(48, 44, 72, 255))
    d.line([(0, 0), (0, T - 1)], fill=(48, 44, 72, 255))
    for _ in range(5 + variant * 4):
        d.point((rnd.randint(1, 14), rnd.randint(1, 14)), fill=(58, 52, 86, 255))
    if variant:
        d.line([(4, 9), (7, 11), (9, 10), (12, 13)], fill=(26, 22, 42, 255))
    return im


def wall(variant):
    im = Image.new("RGBA", (T, T), (92, 74, 128, 255))
    d = ImageDraw.Draw(im)
    for row in range(4):
        y = row * 4
        d.line([(0, y), (T - 1, y)], fill=(48, 38, 74, 255))
        off = 0 if (row + variant) % 2 == 0 else 8
        for x in (off, off + 8):
            if x < T:
                d.line([(x, y), (x, y + 3)], fill=(48, 38, 74, 255))
        d.line([(1, y + 1), (6, y + 1)], fill=(120, 100, 158, 255))
    return im


def stairs():
    im = Image.new("RGBA", (T, T), (30, 24, 50, 255))
    d = ImageDraw.Draw(im)
    for i, c in enumerate([(52, 46, 80), (40, 34, 64), (26, 20, 44), (14, 10, 26)]):
        d.rectangle([i * 2, i * 2, T - 1 - i * 2, T - 1 - i * 2], fill=c + (255,))
    for dy in range(3):
        d.line([(4 + dy, 5 + dy * 3), (11 - dy, 5 + dy * 3)], fill=(8, 230, 240, 255), width=1)
    return im


def corpse():
    im = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([2, 6, 13, 13], fill=(130, 20, 34, 255))
    d.ellipse([5, 8, 10, 11], fill=(170, 30, 44, 255))
    d.line([(4, 5), (7, 3)], fill=(235, 235, 240, 255))
    d.line([(9, 4), (12, 6)], fill=(235, 235, 240, 255))
    return im


def amulet():
    im = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line([(4, 0), (6, 4), (9, 4), (11, 0)], fill=(200, 150, 30, 255))
    d.ellipse([3, 4, 12, 13], outline=(255, 210, 63, 255), width=2)
    d.ellipse([6, 7, 9, 10], fill=(214, 48, 72, 255))
    d.point((6, 7), fill=(255, 255, 255, 255))
    return im


def glyph(font, cp):
    mask = Image.new("L", (T, T), 0)
    ImageDraw.Draw(mask).text((T // 2, 12), chr(cp), font=font, fill=255, anchor="ms")
    im = Image.new("RGBA", (T, T), (255, 255, 255, 0))
    im.putalpha(mask)
    return im


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in ("DejaVuSansMono-Bold.ttf", "DejaVuSansMono.ttf", "LiberationMono-Bold.ttf", "consolab.ttf", "consola.ttf"):
        for base in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation", "C:/Windows/Fonts"):
            if os.path.exists(os.path.join(base, p)):
                font = ImageFont.truetype(os.path.join(base, p), 14)
                break
        else:
            continue
        break
    else:
        raise SystemExit("No encontré una fuente monoespaciada. Indica la ruta de una .ttf en make_tiles.py")
    sheet = Image.new("RGBA", (T * 16, T * 16), (0, 0, 0, 0))
    for i in range(224):
        cp = 32 + i
        if not 127 <= cp <= 160:
            sheet.paste(glyph(font, cp), ((i % 16) * T, (i // 16) * T))
    order = [floor(0), wall(0), sprite(SPRITES["player"]), sprite(SPRITES["orc"]), sprite(SPRITES["troll"]),
             sprite(SPRITES["potion"]), sprite(SPRITES["scroll"]), sprite(SPRITES["weapon"]), sprite(SPRITES["armor"]),
             stairs(), corpse(), amulet(), floor(1), wall(1)]
    for k, im in enumerate(order):
        i = 224 + k
        sheet.paste(im, ((i % 16) * T, (i // 16) * T))
    sheet.save(os.path.join(here, "tiles.png"))
    print("tiles.png generado")


if __name__ == "__main__":
    main()
