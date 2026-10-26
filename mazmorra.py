"""Mazmorra: un roguelike completo en Python con TCOD.
 
Requisitos: Python 3.9+ y  pip install tcod
Ejecutar:   python mazmorra.py
 
Objetivo: baja por 8 pisos y recupera el Amuleto de la Mazmorra.
Pulsa ? dentro del juego para ver los controles.
Los gráficos están en tiles.png (debe estar junto a este archivo).
"""
import os
import pickle
import random
from collections import deque
 
import tcod
import tcod.console
import tcod.context
import tcod.event
import tcod.tileset
 
W, H = 80, 43            # tamaño del mapa
SW, SH = 80, 50          # pantalla completa (mapa + panel)
FOV_R, MAX_DEPTH = 8, 8
SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "partida.sav")
WHITE, GREY, RED, GREEN, CYAN, YELLOW = (255, 255, 255), (150, 150, 170), (255, 64, 64), (80, 255, 120), (8, 247, 254), (255, 210, 63)
TILES = [chr(0xE000 + i) for i in range(14)]   # sprites de tiles.png
T_FLOOR, T_WALL, T_PLAYER, T_ORC, T_TROLL, T_POTION, T_SCROLL, T_WEAPON, T_ARMOR, T_STAIRS, T_CORPSE, T_AMULET, T_FLOOR2, T_WALL2 = TILES
DIM = (95, 95, 125)
DIRS8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
MOVES = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0),
         "k": (0, -1), "j": (0, 1), "h": (-1, 0), "l": (1, 0), "y": (-1, -1), "u": (1, -1), "b": (-1, 1), "n": (1, 1),
         "8": (0, -1), "2": (0, 1), "4": (-1, 0), "6": (1, 0), "7": (-1, -1), "9": (1, -1), "1": (-1, 1), "3": (1, 1)}
# (nombre, símbolo, color, tipo, cantidad, bonus, piso mínimo, peso)
SPECS = [("Poción de curación", T_POTION, (190, 70, 255), "heal", 15, 0, 1, 35),
         ("Pergamino del rayo", T_SCROLL, (255, 255, 60), "lightning", 20, 0, 1, 15),
         ("Pergamino de confusión", T_SCROLL, (207, 63, 255), "confuse", 8, 0, 2, 12),
         ("Pergamino de bola de fuego", T_SCROLL, (255, 90, 0), "fireball", 12, 0, 3, 10),
         ("Daga", T_WEAPON, (0, 191, 255), "arma", 0, 2, 1, 6),
         ("Espada", T_WEAPON, (0, 191, 255), "arma", 0, 4, 3, 8),
         ("Armadura de cuero", T_ARMOR, (160, 90, 30), "armadura", 0, 1, 1, 10),
         ("Cota de malla", T_ARMOR, (160, 90, 30), "armadura", 0, 3, 3, 8)]
SP = {s[0]: s for s in SPECS}
AMULET = ("Amuleto de la Mazmorra", T_AMULET, YELLOW, "amulet", 0, 0, 0, 0)
 
 
class Entity:
    def __init__(s, x, y, ch, color, name):
        s.x, s.y, s.ch, s.color, s.name = x, y, ch, color, name
 
 
class Item(Entity):
    def __init__(s, x, y, spec):
        super().__init__(x, y, spec[1], spec[2], spec[0])
        s.kind, s.amount, s.bonus = spec[3], spec[4], spec[5]
 
 
class Actor(Entity):
    def __init__(s, x, y, ch, color, name, hp, power, defense, xp=0):
        super().__init__(x, y, ch, color, name)
        s.max_hp = s.hp = hp
        s.base_power, s.base_def, s.xp_value, s.confused = power, defense, xp, 0
 
    @property
    def power(s):
        return s.base_power
 
    @property
    def defense(s):
        return s.base_def
 
 
class Player(Actor):
    def __init__(s, x, y):
        super().__init__(x, y, T_PLAYER, WHITE, "Jugador", 30, 1, 0)
        s.inv, s.eq, s.level, s.xp = [], {"arma": None, "armadura": None}, 1, 0
 
    @property
    def xp_next(s):
        return 200 + 150 * (s.level - 1)
 
    @property
    def power(s):
        return s.base_power + (s.eq["arma"].bonus if s.eq["arma"] else 0)
 
    @property
    def defense(s):
        return s.base_def + (s.eq["armadura"].bonus if s.eq["armadura"] else 0)
 
 
def line(x0, y0, x1, y1):
    pts, dx, dy = [], abs(x1 - x0), abs(y1 - y0)
    sx, sy, err = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1), dx - dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
 
 
class Game:
    def __init__(s):
        s.depth = s.turn = s.pending = 0
        s.msgs, s.over, s.won = [], False, False
        s.player = p = Player(0, 0)
        p.inv = [Item(0, 0, SP["Poción de curación"]), Item(0, 0, SP["Daga"])]
        p.eq["arma"] = p.inv[1]
        s.new_level()
        s.log("Bajas a la mazmorra. Encuentra el Amuleto en el piso %d. (? = ayuda)" % MAX_DEPTH, CYAN)
 
    def log(s, t, c=WHITE):
        s.msgs = (s.msgs + [(t, c)])[-100:]
 
    # ---------- generación ----------
    def hline(s, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            s.tiles[x][y] = 1
 
    def vline(s, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            s.tiles[x][y] = 1
 
    def gen(s):
        s.tiles = [[0] * H for _ in range(W)]
        s.explored = [[False] * H for _ in range(W)]
        rooms = []
        for _ in range(80):
            if len(rooms) >= 12:
                break
            w, h = random.randint(5, 10), random.randint(4, 8)
            x, y = random.randint(1, W - w - 2), random.randint(1, H - h - 2)
            if any(x <= r[2] + 1 and x + w >= r[0] - 1 and y <= r[3] + 1 and y + h >= r[1] - 1 for r in rooms):
                continue
            for i in range(x, x + w):
                for j in range(y, y + h):
                    s.tiles[i][j] = 1
            r = (x, y, x + w - 1, y + h - 1)
            if rooms:
                (x1, y1), (x2, y2) = [((a[0] + a[2]) // 2, (a[1] + a[3]) // 2) for a in (rooms[-1], r)]
                if random.random() < .5:
                    s.hline(x1, x2, y1)
                    s.vline(y1, y2, x2)
                else:
                    s.vline(y1, y2, x1)
                    s.hline(x1, x2, y2)
            rooms.append(r)
        return rooms
 
    def new_level(s):
        rooms = []
        while len(rooms) < 3:
            rooms = s.gen()
        s.depth += 1
        d, p = s.depth, s.player
        p.x, p.y = (rooms[0][0] + rooms[0][2]) // 2, (rooms[0][1] + rooms[0][3]) // 2
        last = rooms[-1]
        s.stairs = ((last[0] + last[2]) // 2, (last[1] + last[3]) // 2)
        s.ents = []
        for r in rooms[1:]:
            for kind in ("m", "i"):
                for _ in range(random.randint(0, 1 + min(d, 3)) if kind == "m" else random.randint(0, 2)):
                    x, y = random.randint(r[0], r[2]), random.randint(r[1], r[3])
                    if (x, y) == s.stairs or any(e.x == x and e.y == y for e in s.ents):
                        continue
                    s.ents.append(s.make_monster(x, y) if kind == "m" else s.make_item(x, y))
        if d == MAX_DEPTH:
            sx, sy = s.stairs
            s.ents = [e for e in s.ents if (e.x, e.y) != (sx, sy)] + [Item(sx, sy, AMULET)]
        s.update_fov()
 
    def make_monster(s, x, y):
        d = s.depth
        if d >= 2 and random.random() < min(.6, .15 + .08 * d):
            a = ("Troll", T_TROLL, (0, 160, 0), 16, 4, 1, 100)
        else:
            a = ("Orco", T_ORC, (90, 170, 90), 10, 3, 0, 35)
        return Actor(x, y, a[1], a[2], a[0], a[3] + d // 2, a[4] + d // 4, a[5], a[6])
 
    def make_item(s, x, y):
        pool = [sp for sp in SPECS if sp[6] <= s.depth]
        return Item(x, y, random.choices(pool, [sp[7] for sp in pool])[0])
 
    # ---------- utilidades ----------
    def monsters(s):
        return [e for e in s.ents if isinstance(e, Actor)]
 
    def actor_at(s, x, y):
        return next((m for m in s.monsters() if (m.x, m.y) == (x, y)), None)
 
    def walkable(s, x, y):
        return 0 <= x < W and 0 <= y < H and s.tiles[x][y] == 1
 
    def update_fov(s):
        p = s.player
        vis = {(p.x, p.y)}
        for x in range(p.x - FOV_R, p.x + FOV_R + 1):
            for y in range(p.y - FOV_R, p.y + FOV_R + 1):
                if not (0 <= x < W and 0 <= y < H) or (x - p.x) ** 2 + (y - p.y) ** 2 > FOV_R ** 2:
                    continue
                for lx, ly in line(p.x, p.y, x, y)[1:]:
                    vis.add((lx, ly))
                    if not s.tiles[lx][ly]:
                        break
        s.vis = vis
        for x, y in vis:
            s.explored[x][y] = True
 
    def dist_map(s):
        p = s.player
        dist, q = {(p.x, p.y): 0}, deque([(p.x, p.y)])
        while q:
            x, y = q.popleft()
            if dist[(x, y)] >= 25:
                continue
            for dx, dy in DIRS8:
                n = (x + dx, y + dy)
                if n not in dist and s.walkable(*n):
                    dist[n] = dist[(x, y)] + 1
                    q.append(n)
        return dist
 
    # ---------- combate ----------
    def attack(s, a, d):
        dmg = max(1, a.power - d.defense + random.randint(-1, 1))
        mine = a is s.player
        s.log("%s ataca a %s y causa %d de daño." % ("Atacas" if mine else a.name, d.name if mine else "ti", dmg), WHITE if mine else RED)
        s.hurt(d, dmg)
 
    def hurt(s, d, dmg):
        d.hp -= dmg
        if d.hp > 0:
            return
        p = s.player
        if d is p:
            s.over = True
            s.log("Has muerto...", RED)
            return
        s.ents.remove(d)
        s.ents.insert(0, Entity(d.x, d.y, T_CORPSE, (150, 0, 0), "cadáver de " + d.name.lower()))
        s.log("%s muere. Ganas %d XP." % (d.name, d.xp_value), (255, 160, 60))
        p.xp += d.xp_value
        while p.xp >= p.xp_next:
            p.xp -= p.xp_next
            p.level += 1
            s.pending += 1
            s.log("¡Subes al nivel %d!" % p.level, GREEN)
 
    def levelup(s, choice):
        p = s.player
        if choice == 0:
            p.max_hp += 20
            p.hp += 20
        elif choice == 1:
            p.base_power += 1
        else:
            p.base_def += 1
        s.pending -= 1
 
    def monsters_act(s):
        p, dist = s.player, s.dist_map()
        for m in s.monsters():
            if s.over:
                return
            if m.confused > 0:
                m.confused -= 1
                dx, dy = random.choice(DIRS8)
                nx, ny = m.x + dx, m.y + dy
                t = p if (nx, ny) == (p.x, p.y) else s.actor_at(nx, ny)
                if t:
                    s.attack(m, t)
                elif s.walkable(nx, ny):
                    m.x, m.y = nx, ny
            elif (m.x, m.y) in s.vis:
                if max(abs(m.x - p.x), abs(m.y - p.y)) <= 1:
                    s.attack(m, p)
                    continue
                best, bd = None, dist.get((m.x, m.y), 999)
                for dx, dy in DIRS8:
                    n = (m.x + dx, m.y + dy)
                    if dist.get(n, 999) < bd and not s.actor_at(*n) and n != (p.x, p.y):
                        best, bd = n, dist[n]
                if best:
                    m.x, m.y = best
 
    def end_turn(s):
        s.turn += 1
        s.update_fov()
        s.monsters_act()
        p = s.player
        if s.turn % 10 == 0 and not s.over and p.hp < p.max_hp:
            p.hp += 1
 
    # ---------- acciones del jugador ----------
    def move(s, dx, dy):
        p = s.player
        nx, ny = p.x + dx, p.y + dy
        t = s.actor_at(nx, ny)
        if t:
            s.attack(p, t)
            return True
        if not s.walkable(nx, ny):
            return False
        p.x, p.y = nx, ny
        it = next((e for e in s.ents if isinstance(e, Item) and (e.x, e.y) == (nx, ny)), None)
        if it:
            s.log("Ves aquí: %s (g para recoger)." % it.name, YELLOW)
        return True
 
    def pickup(s):
        p = s.player
        it = next((e for e in s.ents if isinstance(e, Item) and (e.x, e.y) == (p.x, p.y)), None)
        if not it:
            s.log("No hay nada que recoger aquí.", GREY)
            return False
        if it.kind == "amulet":
            s.won = True
            s.log("¡Tienes el Amuleto de la Mazmorra!", YELLOW)
            return True
        if len(p.inv) >= 26:
            s.log("Tu inventario está lleno.", RED)
            return False
        s.ents.remove(it)
        p.inv.append(it)
        s.log("Recoges: %s." % it.name, GREEN)
        return True
 
    def drop(s, i):
        p = s.player
        it = p.inv.pop(i)
        for slot in p.eq:
            if p.eq[slot] is it:
                p.eq[slot] = None
        it.x, it.y = p.x, p.y
        s.ents.insert(0, it)
        s.log("Sueltas: %s." % it.name)
        return True
 
    def use(s, i):
        p = s.player
        it = p.inv[i]
        if it.kind == "heal":
            if p.hp >= p.max_hp:
                s.log("Ya tienes la salud completa.", GREY)
                return False
            n = min(it.amount, p.max_hp - p.hp)
            p.hp += n
            s.log("Bebes la poción y recuperas %d de vida." % n, GREEN)
        elif it.kind in ("arma", "armadura"):
            if p.eq[it.kind] is it:
                p.eq[it.kind] = None
                s.log("Te quitas: %s." % it.name)
            else:
                p.eq[it.kind] = it
                s.log("Equipas: %s." % it.name, GREEN)
            return True
        else:
            seen = [m for m in s.monsters() if (m.x, m.y) in s.vis]
            if not seen:
                s.log("No hay enemigos a la vista.", GREY)
                return False
            t = min(seen, key=lambda m: (m.x - p.x) ** 2 + (m.y - p.y) ** 2)
            if it.kind == "lightning":
                s.log("Un rayo golpea a %s causando %d de daño." % (t.name, it.amount), YELLOW)
                s.hurt(t, it.amount)
            elif it.kind == "confuse":
                t.confused = it.amount
                s.log("%s queda confundido." % t.name, (207, 63, 255))
            else:
                s.log("Una bola de fuego explota sobre %s." % t.name, (255, 90, 0))
                for m in s.monsters():
                    if (m.x - t.x) ** 2 + (m.y - t.y) ** 2 <= 4:
                        s.hurt(m, it.amount)
        p.inv.pop(i)
        return True
 
    def descend(s):
        p = s.player
        if (p.x, p.y) != s.stairs or s.depth >= MAX_DEPTH:
            s.log("No hay escaleras aquí." if s.depth < MAX_DEPTH else "No hay más pisos: busca el Amuleto.", GREY)
            return
        s.new_level()
        p.hp = min(p.max_hp, p.hp + p.max_hp // 2)
        s.log("Descansas un momento y bajas al piso %d." % s.depth, CYAN)
        save(s)
 
 
# ---------- guardado ----------
def save(g):
    if g and not g.over and not g.won:
        try:
            with open(SAVE, "wb") as f:
                pickle.dump(g, f)
        except OSError:
            pass
 
 
def load():
    try:
        with open(SAVE, "rb") as f:
            g = pickle.load(f)
        return g if isinstance(g, Game) else None
    except Exception:
        return None
 
 
def wipe():
    try:
        os.remove(SAVE)
    except OSError:
        pass
 
 
# ---------- lógica de teclado ----------
def after(g):
    if g.over or g.won:
        wipe()
        return "end"
    return "level" if g.pending else "play"
 
 
def handle(mode, g, k):
    if mode == "main":
        if k == "n":
            return "play", Game()
        if k == "c":
            g2 = load()
            return ("play", g2) if g2 else (mode, g)
        return ("quit", g) if k == "q" else (mode, g)
    if mode == "end":
        return "main", None
    if mode in ("help", "hist", "char"):
        return "play", g
    if mode == "level":
        if k in ("1", "2", "3"):
            g.levelup(int(k) - 1)
        return ("level" if g.pending else "play"), g
    if mode in ("inv", "drop"):
        if k == "ESC":
            return "play", g
        if k and len(k) == 1 and "a" <= k <= "z" and ord(k) - 97 < len(g.player.inv):
            i = ord(k) - 97
            if (g.use(i) if mode == "inv" else g.drop(i)):
                g.end_turn()
                return after(g), g
        return mode, g
    if k == "ESC":
        save(g)
        return "main", None
    acted = False
    if k in MOVES:
        acted = g.move(*MOVES[k])
    elif k in (".", "5"):
        acted = True
    elif k in ("g", ","):
        acted = g.pickup()
    elif k in (">", "ENTER"):
        g.descend()
    elif k in ("i", "d", "c", "v", "?"):
        if k in ("i", "d") and not g.player.inv:
            g.log("No llevas nada.", GREY)
        else:
            return {"i": "inv", "d": "drop", "c": "char", "v": "hist", "?": "help"}[k], g
    if acted:
        g.end_turn()
    return after(g), g
 
 
# ---------- dibujo ----------
def txt(con, x, y, t, fg=WHITE, bg=None):
    con.print(x, y, t, fg=fg, bg=bg)
 
 
def bar(con, x, y, w, cur, mx, label, fill, back):
    n = int(w * max(0, cur) / mx) if mx else 0
    txt(con, x, y, " " * w, bg=back)
    if n:
        txt(con, x, y, " " * n, bg=fill)
    txt(con, x + 1, y, "%s: %d/%d" % (label, cur, mx), WHITE)
 
 
def box(con, title, lines, w=56):
    h, bg = len(lines) + 4, (14, 10, 30)
    x, y = (SW - w) // 2, (SH - h) // 2
    for j in range(h):
        txt(con, x, y + j, " " * w, bg=bg)
        txt(con, x, y + j, ("+" + "-" * (w - 2) + "+") if j in (0, h - 1) else "|", CYAN, bg)
        if 0 < j < h - 1:
            txt(con, x + w - 1, y + j, "|", CYAN, bg)
    txt(con, x + 2, y, " %s " % title, YELLOW, bg)
    for j, (t, c) in enumerate(lines):
        txt(con, x + 3, y + 2 + j, t[:w - 6], c, bg)
 
 
def draw_game(con, g):
    vis, p = g.vis, g.player
    for x in range(W):
        for y in range(H):
            if g.explored[x][y]:
                c = WHITE if (x, y) in vis else DIM
                if g.tiles[x][y]:
                    txt(con, x, y, T_FLOOR2 if (x * 7 + y * 13) % 5 == 0 else T_FLOOR, c)
                else:
                    txt(con, x, y, T_WALL2 if (x + y) % 4 == 0 else T_WALL, c)
    sx, sy = g.stairs
    if g.explored[sx][sy] and g.depth < MAX_DEPTH:
        txt(con, sx, sy, T_STAIRS, WHITE if (sx, sy) in vis else DIM)
    for e in sorted(g.ents, key=lambda e: isinstance(e, Actor)):
        if (e.x, e.y) in vis:
            txt(con, e.x, e.y, e.ch, WHITE)
    txt(con, p.x, p.y, T_PLAYER, WHITE)
    bar(con, 1, H, 22, p.hp, p.max_hp, "Vida", (190, 30, 60), (70, 10, 25))
    bar(con, 1, H + 1, 22, p.xp, p.xp_next, "XP", (40, 90, 200), (15, 30, 70))
    txt(con, 1, H + 3, "Piso %d/%d   Nivel %d" % (g.depth, MAX_DEPTH, p.level), CYAN)
    txt(con, 1, H + 4, "Poder %d   Defensa %d" % (p.power, p.defense), YELLOW)
    txt(con, 1, H + 6, "? ayuda", GREY)
    for j, (t, c) in enumerate(g.msgs[-7:]):
        txt(con, 26, H + j, t[:SW - 27], c)
 
 
def item_lines(p, verb):
    out = []
    for i, it in enumerate(p.inv):
        tag = " (equipado)" if any(v is it for v in p.eq.values()) else ""
        out.append(("%s) %s%s" % (chr(97 + i), it.name, tag), it.color))
    return out + [("", WHITE), ("[letra] %s    [Esc] volver" % verb, GREY)]
 
 
def draw(con, g, mode):
    con.clear()
    if mode == "main":
        for j, t in enumerate(("M A Z M O R R A", "", "Un roguelike en Python", "", "[N] Nueva partida", "[C] Continuar" + ("" if os.path.exists(SAVE) else " (no hay partida)"), "[Q] Salir")):
            txt(con, (SW - len(t)) // 2, 16 + j, t, YELLOW if j == 0 else WHITE)
        for j, t in enumerate((T_PLAYER, T_ORC, T_TROLL, T_POTION, T_SCROLL, T_WEAPON, T_ARMOR, T_AMULET)):
            txt(con, (SW - 15) // 2 + j * 2, 13, t, WHITE)
        return
    draw_game(con, g)
    p = g.player
    if mode == "inv":
        box(con, "Inventario", item_lines(p, "usar / equipar"))
    elif mode == "drop":
        box(con, "Soltar objeto", item_lines(p, "soltar"))
    elif mode == "level":
        box(con, "¡Subiste de nivel!", [("1) Vitalidad  (+20 vida máxima)", WHITE), ("2) Fuerza     (+1 poder)", WHITE), ("3) Agilidad   (+1 defensa)", WHITE)])
    elif mode == "hist":
        box(con, "Historial", [(t, c) for t, c in g.msgs[-24:]] + [("", WHITE), ("[cualquier tecla] volver", GREY)], 70)
    elif mode == "char":
        box(con, "Personaje", [("Nivel %d   XP %d/%d" % (p.level, p.xp, p.xp_next), WHITE), ("Vida %d/%d" % (p.hp, p.max_hp), RED),
                               ("Poder %d   Defensa %d" % (p.power, p.defense), YELLOW), ("Piso %d   Turnos %d" % (g.depth, g.turn), CYAN),
                               ("", WHITE), ("[cualquier tecla] volver", GREY)])
    elif mode == "help":
        box(con, "Controles", [(t, WHITE) for t in (
            "Mover/atacar: flechas, hjklyubn o teclado numérico", "Esperar: . o 5      Recoger: g o ,", "Inventario: i (usar/equipar)   Soltar: d",
            "Bajar escaleras: > o Enter (sobre el símbolo >)", "Personaje: c      Historial: v", "Guardar y salir al menú: Esc",
            "", "Pergaminos y bolas de fuego apuntan al enemigo", "más cercano a la vista. Muerte permanente.")] + [("", WHITE), ("[cualquier tecla] volver", GREY)], 60)
    elif mode == "end":
        win = g.won
        box(con, "¡VICTORIA!" if win else "HAS MUERTO", [("Recuperaste el Amuleto de la Mazmorra." if win else "La mazmorra te ha reclamado.", YELLOW if win else RED),
                                                       ("Piso %d, nivel %d, %d turnos." % (g.depth, p.level, g.turn), WHITE), ("", WHITE), ("[cualquier tecla] menú principal", GREY)])
 
 
# ---------- teclado y ventana ----------
SYM = {1073741906: "UP", 1073741905: "DOWN", 1073741904: "LEFT", 1073741903: "RIGHT", 27: "ESC", 13: "ENTER", 1073741912: "ENTER"}
SYM.update({1073741913 + i: str(i + 1) for i in range(9)})
 
 
def key_of(sym):
    s = int(sym)
    if s in SYM:
        return SYM[s]
    return chr(s) if 97 <= s <= 122 or 48 <= s <= 57 else None
 
 
def load_tileset():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiles.png")
    if not os.path.exists(path):
        raise SystemExit("Falta tiles.png junto a mazmorra.py (puedes regenerarlo con make_tiles.py).")
    charmap = list(range(32, 256)) + [0xE000 + i for i in range(32)]   # 224 de texto + 32 de sprites
    return tcod.tileset.load_tilesheet(path, 16, 16, charmap)
 
 
def main():
    g, mode = None, "main"
    with tcod.context.new(width=1024, height=640, tileset=load_tileset(), title="Mazmorra",
                          sdl_window_flags=tcod.context.SDL_WINDOW_RESIZABLE, vsync=True) as ctx:
        try:
            ctx.sdl_window.start_text_input()
        except Exception:
            pass
        con = tcod.console.Console(SW, SH, order="F")
        while True:
            draw(con, g, mode)
            ctx.present(con, keep_aspect=True, integer_scaling=False)
            for ev in tcod.event.wait():
                k = None
                if isinstance(ev, tcod.event.Quit):
                    save(g)
                    return
                if isinstance(ev, tcod.event.KeyDown):
                    k = key_of(ev.sym)
                elif isinstance(ev, tcod.event.TextInput) and ev.text in (".", ",", "<", ">", "?"):
                    k = ev.text
                if k is None:
                    continue
                mode, g = handle(mode, g, k)
                if mode == "quit":
                    return
 
 
if __name__ == "__main__":
    main()
 