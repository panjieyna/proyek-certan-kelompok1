"""CASE UNKNOWN: The Last Clue  -  game detektif 2D (Python + Pygame).

Data kasus dibaca dari folder data/ (file CSV), algoritma Bayes ada di bayes_engine.py.
Jalankan:  python game.py
"""
import math
import os
import random
import sys
from collections import deque

import pygame

import bayes_engine as be
from ui import GameUI, W, H, BG, TEXT, ACCENT, GOOD, BAD, ARIA_C, font, card

# ------------------------------------------------------------------ konstanta
MAP_W, MAP_H = 800, 600
FPS = 60
SPEED = 175.0
CELL = 20
GW, GH = MAP_W // CELL, MAP_H // CELL
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ------------------------------------------------------------------ util
ANCH = {"tl": "topleft", "c": "center", "tr": "topright", "ml": "midleft", "mr": "midright", "tc": "midtop"}


def text(surf, font, s, color, x, y, anchor="tl"):
    img = font.render(s, True, color)
    r = img.get_rect()
    setattr(r, ANCH[anchor], (x, y))
    surf.blit(img, r)
    return r


def lerp(a, b, k):
    return a + (b - a) * k


def box(surf, rect, fill, border=None, radius=8, width=1):
    pygame.draw.rect(surf, fill, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width, border_radius=radius)


def draw_char(surf, x, y, coat, facing, phase, moving, t, hat=(58, 48, 52), band=(200, 60, 70),
              skin=(240, 202, 164)):
    """Karakter kecil (x,y = titik kaki). Berjalan: kaki & tangan berayun."""
    swing = math.sin(phase) * 5 if moving else 0.0
    bob = abs(math.sin(phase)) * 2.0 if moving else math.sin(t * 2.2) * 0.8
    pygame.draw.ellipse(surf, (10, 10, 18), (x - 11, y - 4, 22, 8))
    leg = (34, 38, 58)
    ly = y - 12 - max(0, swing) * 0.6
    ry = y - 12 - max(0, -swing) * 0.6
    pygame.draw.rect(surf, leg, (x - 7, ly, 5, 12), border_radius=2)
    pygame.draw.rect(surf, leg, (x + 2, ry, 5, 12), border_radius=2)
    pygame.draw.rect(surf, (20, 20, 28), (x - 7, ly + 9, 6, 3))
    pygame.draw.rect(surf, (20, 20, 28), (x + 1, ry + 9, 6, 3))
    top = y - 31 - bob
    dark = tuple(max(0, c - 40) for c in coat)
    if facing in ("l", "r"):
        pygame.draw.rect(surf, dark, (x - 3, top + 3 + swing * 0.4, 6, 12), border_radius=3)
    pygame.draw.rect(surf, coat, (x - 9, top, 18, 20), border_radius=5)
    pygame.draw.rect(surf, dark, (x - 9, top + 14, 18, 3))
    if facing == "d":
        pygame.draw.polygon(surf, (235, 235, 240), [(x - 3, top), (x + 3, top), (x, top + 8)])
        pygame.draw.rect(surf, dark, (x - 12, top + 2 - swing * 0.4, 4, 13), border_radius=2)
        pygame.draw.rect(surf, dark, (x + 8, top + 2 + swing * 0.4, 4, 13), border_radius=2)
    elif facing == "u":
        pygame.draw.rect(surf, dark, (x - 12, top + 2 + swing * 0.4, 4, 13), border_radius=2)
        pygame.draw.rect(surf, dark, (x + 8, top + 2 - swing * 0.4, 4, 13), border_radius=2)
    hy = top - 6
    pygame.draw.circle(surf, skin, (x, hy), 7)
    if facing == "u":
        pygame.draw.circle(surf, (50, 40, 36), (x, hy - 1), 7)
    else:
        ex = {"d": 0, "l": -2, "r": 2}[facing]
        pygame.draw.circle(surf, (30, 30, 40), (x - 3 + ex, hy), 1)
        pygame.draw.circle(surf, (30, 30, 40), (x + 3 + ex, hy), 1)
    if hat:
        pygame.draw.ellipse(surf, hat, (x - 11, hy - 6, 22, 6))
        pygame.draw.rect(surf, hat, (x - 6, hy - 13, 12, 9), border_radius=3)
        pygame.draw.rect(surf, band, (x - 6, hy - 8, 12, 2))


# ------------------------------------------------------------------ peta
def build_walls(lokasi):
    T = 10
    door = 90
    cor = next(l for l in lokasi if l.nama == "Lorong")
    walls = [pygame.Rect(-T, -T, MAP_W + 2 * T, T), pygame.Rect(-T, MAP_H, MAP_W + 2 * T, T),
             pygame.Rect(-T, -T, T, MAP_H + 2 * T), pygame.Rect(MAP_W, -T, T, MAP_H + 2 * T)]
    for l in lokasi:
        if l is cor:
            continue
        if l.x > 0:
            walls.append(pygame.Rect(l.x - T // 2, l.y, T, l.h))
        y = l.y + l.h if l.y < cor.y else l.y
        cx = l.x + l.w // 2
        walls.append(pygame.Rect(l.x, y - T // 2, cx - door // 2 - l.x, T))
        walls.append(pygame.Rect(cx + door // 2, y - T // 2, l.x + l.w - (cx + door // 2), T))
    return walls


# dekorasi statis: (nama ruangan, x, y, w, h, warna)
DEKOR = [
    ("Ruang Kontrol", 90, 40, 150, 46, (66, 76, 104)), ("Ruang Kontrol", 14, 150, 92, 90, (50, 56, 82)),
    ("Ruang Kontrol", 140, 150, 100, 12, (36, 90, 120)),
    ("Ruang Pameran", 340, 50, 120, 90, (96, 70, 80)), ("Ruang Pameran", 276, 10, 60, 8, (170, 130, 90)),
    ("Ruang Pameran", 460, 10, 60, 8, (170, 130, 90)), ("Ruang Pameran", 290, 150, 100, 70, (88, 64, 74)),
    ("Ruang Kurator", 560, 8, 230, 28, (92, 70, 54)), ("Ruang Kurator", 610, 110, 120, 50, (86, 66, 100)),
    ("Ruang Kurator", 560, 190, 70, 44, (60, 52, 90)),
    ("Lorong", 40, 288, 720, 24, (118, 44, 62)),
    ("Pos Jaga", 14, 520, 90, 60, (80, 88, 70)), ("Pos Jaga", 150, 420, 90, 40, (92, 82, 62)),
    ("Pos Jaga", 214, 360, 40, 40, (70, 84, 76)),
    ("Gudang", 276, 366, 240, 22, (96, 76, 50)), ("Gudang", 276, 440, 80, 40, (110, 84, 52)),
    ("Gudang", 440, 400, 80, 50, (104, 80, 52)), ("Gudang", 276, 540, 240, 36, (92, 72, 50)),
    ("Lobi", 600, 380, 150, 44, (110, 80, 54)), ("Lobi", 560, 520, 90, 30, (86, 70, 60)),
    ("Lobi", 700, 520, 90, 30, (86, 70, 60)),
]


def render_static(kasus, walls):
    s = pygame.Surface((MAP_W, MAP_H))
    s.fill(BG)
    f = font(13, bold=True)
    for l in kasus.lokasi:
        floor = tuple(int(c * .35 + base * .65) for c, base in zip(l.warna, (31, 40, 45)))
        pygame.draw.rect(s, floor, (l.x, l.y, l.w, l.h))
        lite = tuple(c + 4 for c in floor)
        for ty in range(l.y, l.y + l.h, 40):
            pygame.draw.line(s, lite, (l.x, ty), (l.x + l.w, ty))
        for tx in range(l.x, l.x + l.w, 40):
            pygame.draw.line(s, lite, (tx, l.y), (tx, l.y + l.h))
    for (nama, x, y, w, h, col) in DEKOR:
        col = tuple(int(c * .65 + base * .35) for c, base in zip(col, (34, 44, 49)))
        pygame.draw.rect(s, (15, 21, 26), (x + 3, y + 5, w, h), border_radius=4)
        pygame.draw.rect(s, col, (x, y, w, h), border_radius=4)
        pygame.draw.rect(s, tuple(min(255, c + 20) for c in col), (x, y, w, h), 1, border_radius=4)
        if h > 30:
            pygame.draw.line(s, tuple(min(255, c + 12) for c in col), (x + 5, y + 5), (x + w - 5, y + 5))
    for w in walls:
        pygame.draw.rect(s, (19, 29, 36), w)
        pygame.draw.rect(s, (70, 88, 96), w, 1)
    for l in kasus.lokasi:
        title = l.nama.upper()
        y = l.y + 13 if l.nama != "Lorong" else l.y + 68
        rect = pygame.Rect(l.x + 12, y - 3, f.size(title)[0] + 20, 24)
        card(s, rect, (23, 32, 39), (55, 70, 77), 4)
        text(s, f, title, (188, 202, 205), rect.x + 10, rect.y + 4)
    return s


def make_mask(radius, peak):
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -3):
        a = int(peak * (1 - r / radius) ** 0.8)
        pygame.draw.circle(s, (0, 0, 0, a), (radius, radius), r)
    pygame.draw.circle(s, (0, 0, 0, peak), (radius, radius), 6)
    return s


def draw_icon(s, bid, x, y, t):
    """Ikon objek bukti sederhana (tampak atas)."""
    if bid == "E1":
        pygame.draw.rect(s, (18, 22, 34), (x - 24, y - 15, 48, 30), border_radius=3)
        pygame.draw.rect(s, (26, 64, 118), (x - 21, y - 12, 42, 22))
        off = int(t * 30) % 22
        pygame.draw.rect(s, (90, 150, 230), (x - 21, y - 12 + off, 42, 2))
        if int(t * 2) % 2 == 0:
            pygame.draw.circle(s, BAD, (x - 16, y - 7), 3)
        pygame.draw.rect(s, (40, 46, 70), (x - 10, y + 20, 20, 3))
    elif bid == "E2":
        pygame.draw.rect(s, (42, 48, 66), (x - 15, y - 23, 30, 46), border_radius=3)
        for i in range(4):
            pygame.draw.rect(s, (24, 28, 40), (x - 12, y - 19 + i * 10, 24, 7))
            on = (int(t * 3) + i) % 3 != 0
            pygame.draw.circle(s, GOOD if on else (40, 90, 60), (x + 8, y - 15 + i * 10), 2)
    elif bid == "E3":
        pygame.draw.rect(s, (150, 196, 235), (x - 26, y - 14, 52, 30), border_radius=4)
        pygame.draw.rect(s, (230, 245, 255), (x - 26, y - 14, 52, 30), 2, border_radius=4)
        pygame.draw.ellipse(s, (150, 52, 76), (x - 14, y - 4, 28, 14))
        pygame.draw.line(s, (255, 255, 255), (x - 22, y - 10), (x - 10, y - 10), 2)
    elif bid == "E4":
        pygame.draw.circle(s, (240, 196, 70), (x - 9, y), 7)
        pygame.draw.circle(s, (80, 60, 30), (x - 9, y), 3)
        pygame.draw.rect(s, (240, 196, 70), (x - 3, y - 2, 18, 4))
        pygame.draw.rect(s, (240, 196, 70), (x + 8, y + 2, 3, 5))
        pygame.draw.rect(s, (240, 196, 70), (x + 13, y + 2, 3, 4))
    elif bid == "E6":
        pygame.draw.rect(s, (50, 56, 76), (x - 13, y - 18, 26, 36), border_radius=3)
        pygame.draw.rect(s, (30, 110, 90), (x - 9, y - 14, 18, 12))
        pygame.draw.circle(s, GOOD if int(t * 2) % 2 else (40, 90, 60), (x, y + 8), 3)
    elif bid == "E7":
        pygame.draw.rect(s, (236, 226, 196), (x - 20, y - 11, 19, 22), border_radius=2)
        pygame.draw.rect(s, (226, 216, 186), (x + 1, y - 11, 19, 22), border_radius=2)
        for i in range(4):
            pygame.draw.line(s, (120, 100, 80), (x - 16, y - 6 + i * 5), (x - 5, y - 6 + i * 5))
            pygame.draw.line(s, (120, 100, 80), (x + 5, y - 6 + i * 5), (x + 16, y - 6 + i * 5))
    elif bid == "E8":
        pygame.draw.rect(s, (112, 82, 52), (x - 28, y - 15, 56, 30), border_radius=3)
        pygame.draw.polygon(s, (236, 232, 222), [(x - 18, y - 8), (x + 6, y - 11), (x + 14, y + 4), (x - 10, y + 9)])
        pygame.draw.line(s, (30, 30, 40), (x + 16, y - 6), (x + 24, y + 6), 3)
    else:
        pygame.draw.circle(s, ACCENT, (x, y), 10)


# ------------------------------------------------------------------ game
class Game(GameUI):
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("CASE UNKNOWN: The Last Clue")
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.init_ui()
        self.k = be.muat_kasus(DATA_DIR)
        self.aria = be.Aria(self.k)
        self.walls = build_walls(self.k.lokasi)
        self.static = render_static(self.k, self.walls)
        self.grid = [[self._cell_ok(cx, cy) for cx in range(GW)] for cy in range(GH)]
        self.mask_big = make_mask(230, 150)
        self.mask_small = make_mask(70, 95)
        self.dark = pygame.Surface((MAP_W, MAP_H), pygame.SRCALPHA)
        self.pelaku = next(t for t in self.k.tersangka if t.nama == self.k.meta["Pelaku sebenarnya (kunci)"])
        self.warna = {t.id: t.warna for t in self.k.tersangka}
        self.t = 0.0
        self.state = "menu"
        self.running = True
        self.reset()

    # ---------------------------------------------------------- setup
    def _cell_ok(self, cx, cy):
        x, y = cx * CELL + CELL // 2, cy * CELL + CELL // 2
        return pygame.Rect(x - 9, y - 12, 18, 12).collidelist(self.walls) == -1

    def reset(self):
        self.ui_buttons = []
        self.aria_scroll = self.journal_scroll = 0
        self.found = []
        prior = be.hitung_posterior(self.k, set())
        self.history = [prior]
        self.post = prior
        self.prev = dict(prior)
        self.disp = dict(prior)
        self.px, self.py = 400.0, 306.0
        self.face, self.phase, self.moving = "d", 0.0, False
        self.dialog = None
        self.elapsed = 0.0
        self.actions = 0
        self.hints = 0
        self.talked = set()
        self.target = None
        self.guide = False
        self.auto = False
        self.path, self.path_t = [], 0.0
        self.particles = []
        self.aria_text, self.aria_shown = ("Halo Detektif, aku ARIA, asisten AI-mu. Aku menghitung peluang setiap tersangka "
                                          "dengan Teorema Bayes. Jelajahi museum dan periksa objek bercahaya. "
                                          "Tekan H kalau butuh petunjuk."), 0.0
        self.toast = None
        self.sel = 0
        self.acc_suspect, self.acc_cur, self.acc_picks = None, 0, set()
        self.result = None
        self.inter = []
        npc_names = {s.nama for s in self.k.saksi}
        for b in self.k.bukti:
            if not any(n in b.objek for n in npc_names):
                self.inter.append({"kind": "obj", "x": b.x, "y": b.y, "name": b.objek, "bukti": b})
        for s in self.k.saksi:
            bk = next((b for b in self.k.bukti if s.nama in b.objek), None)
            self.inter.append({"kind": "npc", "x": s.x, "y": s.y, "name": s.nama, "bukti": bk, "saksi": s,
                               "facing": "d"})

    # ---------------------------------------------------------- ARIA
    def aria_say(self, s):
        self.aria_text, self.aria_shown = s, 0.0
        self.aria_scroll = 0

    def nearest(self):
        best, bd = None, 58
        for it in self.inter:
            d = math.hypot(it["x"] - self.px, it["y"] - (self.py - 10))
            if self.target is not None and it["bukti"] is self.target:
                d -= 15          # utamakan objek yang sedang ditunjuk ARIA
            if d < bd:
                best, bd = it, d
        return best

    def hint(self):
        self.hints += 1
        ditemukan = set(self.found)
        saran = self.aria.saran_berikutnya(ditemukan)
        if saran is None:
            self.target = None
            self.guide = self.auto = False
            self.aria_say("Semua bukti sudah ditemukan. Saatnya menyimpulkan, tekan K.")
            return
        self.target = saran
        self.guide = True
        ig = self.aria.nilai_informasi(saran, ditemukan)
        self.aria_say(f"{self.aria.status(ditemukan)} Saranku: periksa {saran.objek} di {saran.lokasi}. "
                      f"Bukti itu diperkirakan paling banyak mengurangi ketidakpastian ({ig:.2f} bit). "
                      f"Ikuti garis putus-putus, atau tekan G agar aku menemanimu jalan.")
        self.compute_path()
        self.path_t = 0.1

    def compute_path(self):
        if not self.target:
            self.path = []
            return
        self.path = self.find_path((self.px, self.py), (self.target.x, self.target.y))

    def find_path(self, start, goal, radius=24):
        sx = min(max(int(start[0] // CELL), 0), GW - 1)
        sy = min(max(int(start[1] // CELL), 0), GH - 1)
        q = deque([(sx, sy)])
        prev = {(sx, sy): None}
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        while q:
            c = q.popleft()
            cx, cy = c
            px, py = cx * CELL + CELL // 2, cy * CELL + CELL // 2
            if math.hypot(px - goal[0], py - goal[1]) <= radius:
                out = []
                while c is not None:
                    out.append((c[0] * CELL + CELL // 2, c[1] * CELL + CELL // 2))
                    c = prev[c]
                return out[::-1]
            for dx, dy in dirs:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < GW and 0 <= ny < GH and (nx, ny) not in prev and self.grid[ny][nx]:
                    if dx and dy and not (self.grid[cy][nx] and self.grid[ny][cx]):
                        continue
                    prev[(nx, ny)] = c
                    q.append((nx, ny))
        return []

    # ---------------------------------------------------------- aksi
    def prect(self, x=None, y=None):
        x = self.px if x is None else x
        y = self.py if y is None else y
        return pygame.Rect(int(x) - 9, int(y) - 12, 18, 12)

    def move(self, dx, dy):
        nx = self.px + dx
        if self.prect(x=nx).collidelist(self.walls) == -1:
            self.px = nx
        ny = self.py + dy
        if self.prect(y=ny).collidelist(self.walls) == -1:
            self.py = ny

    def interact(self):
        it = self.nearest()
        if not it:
            return
        self.actions += 1
        b = it["bukti"]
        baru = b is not None and b.id not in self.found
        if it["kind"] == "npc":
            s = it["saksi"]
            line = s.dialog2 if s.nama in self.talked else s.dialog1
            self.talked.add(s.nama)
            who = s.nama
            tcol = self.warna[s.tid]
        else:
            line = b.deskripsi if baru else f"{b.nama}: sudah tercatat di Evidence Journal."
            who = it["name"]
            tcol = ACCENT
        if not baru and b is not None and it["kind"] == "npc":
            line += "  (Keterangan ini sudah ada di jurnal.)"
        self.dialog = {"who": who, "text": line, "shown": 0.0, "bukti": b if baru else None, "col": tcol}
        if baru:
            self.add_bukti(b)

    def add_bukti(self, b):
        self.prev = dict(self.post)
        self.found.append(b.id)
        self.post = be.hitung_posterior(self.k, set(self.found))
        self.history.append(self.post)
        self.aria_say(self.aria.jelaskan(b, self.prev, self.post) + " " + self.aria.status(set(self.found)))
        if self.target is not None and self.target.id == b.id:
            self.target, self.guide, self.auto = None, False, False
        for _ in range(26):
            a = random.uniform(0, 6.283)
            sp = random.uniform(30, 120)
            self.particles.append([b.x, b.y, math.cos(a) * sp, math.sin(a) * sp - 20, random.uniform(0.5, 1.1),
                                   random.choice([ACCENT, ARIA_C, (255, 255, 255)])])

    def submit(self):
        picks = [b for b in self.k.bukti if b.id in self.acc_picks]
        p = self.k.param
        benar = self.acc_suspect == self.pelaku.id
        relevan = [b for b in self.k.bukti if b.relevan]
        ok = sum(1 for b in picks if b.relevan)
        bad = len(picks) - ok
        s_t = int(p["skor_tersangka"]) if benar else 0
        s_b = max(0, round(p["skor_bukti"] * ok / max(1, len(relevan)) - p["penalti_bukti_salah"] * bad))
        lewat = max(0.0, self.elapsed - float(p["batas_waktu_efisien_detik"]))
        s_e = max(0, round(p["skor_efisiensi"] - lewat / 15))
        total = s_t + s_b + s_e
        grade = ("Detektif Legendaris" if total >= 85 else "Detektif Handal" if total >= 65
                 else "Detektif Magang" if total >= 40 else "Perlu latihan lagi")
        top = be.peringkat(self.post)[0]
        nama = self.k.tersangka_by_id(top[1]).nama
        if benar:
            debrief = (f"Tepat! Peluang tertinggi ada pada {nama} ({top[2]:.0%}) dan kesimpulanmu cocok. "
                       f"Dari {len(self.found)} bukti yang kamu kumpulkan, {ok} relevan untuk kesimpulan.")
        else:
            debrief = (f"Kesimpulanmu keliru. Pelakunya {self.pelaku.nama}. Analisis akhirku condong ke {nama} "
                       f"({top[2]:.0%}); coba cari lebih banyak bukti yang andal sebelum menyimpulkan.")
        self.result = dict(benar=benar, s_t=s_t, s_b=s_b, s_e=s_e, total=total, grade=grade, ok=ok, bad=bad,
                           debrief=debrief, n=len(picks))
        self.state = "result"

    # ---------------------------------------------------------- input
    def handle(self, e):
        if self.ui_event(e):
            return
        if e.type == pygame.QUIT:
            self.running = False
            return
        if e.type != pygame.KEYDOWN:
            return
        k = e.key
        if self.state == "menu":
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                self.reset()
                self.state = "play"
            elif k == pygame.K_ESCAPE:
                self.running = False
        elif self.state == "play":
            if self.dialog:
                if k in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                    full = len(self.dialog["text"])
                    if self.dialog["shown"] < full:
                        self.dialog["shown"] = full
                    else:
                        self.dialog = None
                return
            if k == pygame.K_e:
                self.interact()
            elif k == pygame.K_h:
                self.hint()
            elif k == pygame.K_g:
                if not self.target:
                    self.hint()
                if self.target:
                    self.auto = not self.auto
                    self.guide = True
                    self.compute_path()
                    self.path_t = 0.1
            elif k == pygame.K_j:
                self.state, self.sel = "journal", 0
                self.journal_scroll = 0
            elif k == pygame.K_k:
                self.state = "accuse"
                self.acc_suspect, self.acc_cur, self.acc_picks = None, 0, set()
            elif k == pygame.K_ESCAPE:
                self.state = "menu"
        elif self.state == "journal":
            if k in (pygame.K_ESCAPE, pygame.K_j):
                self.state = "play"
            elif k in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.k.bukti)
                self.journal_scroll = 0
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.k.bukti)
                self.journal_scroll = 0
        elif self.state == "accuse":
            n = len(self.found)
            if k == pygame.K_ESCAPE:
                self.state = "play"
            elif k in (pygame.K_1, pygame.K_2, pygame.K_3):
                i = k - pygame.K_1
                if i < len(self.k.tersangka):
                    self.acc_suspect = self.k.tersangka[i].id
            elif k in (pygame.K_UP, pygame.K_w) and n:
                self.acc_cur = (self.acc_cur - 1) % n
            elif k in (pygame.K_DOWN, pygame.K_s) and n:
                self.acc_cur = (self.acc_cur + 1) % n
            elif k == pygame.K_SPACE and n:
                bid = self.found[self.acc_cur]
                self.acc_picks ^= {bid}
            elif k == pygame.K_RETURN and self.acc_suspect:
                self.submit()
        elif self.state == "result":
            if k == pygame.K_r:
                self.reset()
                self.state = "play"
            elif k in (pygame.K_ESCAPE, pygame.K_q):
                self.state = "menu"

    # ---------------------------------------------------------- update
    def update(self, dt):
        self.t += dt
        self.aria_shown = min(len(self.aria_text), self.aria_shown + 70 * dt)
        for h in self.disp:
            self.disp[h] = lerp(self.disp[h], self.post[h], min(1.0, dt * 5))
        if self.state != "play":
            return
        self.elapsed += dt
        if self.dialog:
            self.dialog["shown"] = min(len(self.dialog["text"]), self.dialog["shown"] + 90 * dt)
            self.moving = False
        else:
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
            if (dx or dy) and self.auto:
                self.auto = False
            if self.auto and self.target:
                dx, dy = self.auto_step(dt)
            self.moving = bool(dx or dy)
            if self.moving:
                n = math.hypot(dx, dy)
                self.move(dx / n * SPEED * dt, dy / n * SPEED * dt)
                self.phase += dt * 13
                if abs(dx) >= abs(dy):
                    self.face = "r" if dx > 0 else "l"
                else:
                    self.face = "d" if dy > 0 else "u"
        if self.guide and self.target:
            self.path_t -= dt
            if self.path_t <= 0:
                self.compute_path()
                self.path_t = 0.1
        # NPC menghadap pemain
        for it in self.inter:
            if it["kind"] == "npc":
                ddx, ddy = self.px - it["x"], self.py - it["y"]
                if math.hypot(ddx, ddy) < 120:
                    it["facing"] = ("r" if ddx > 0 else "l") if abs(ddx) > abs(ddy) else ("d" if ddy > 0 else "u")
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 90 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]

    def auto_step(self, dt):
        tg = self.target
        wp = None
        if math.hypot(tg.x - self.px, tg.y - (self.py - 10)) > 36:
            if len(self.path) > 1:
                j = min(range(len(self.path)),
                        key=lambda i: math.hypot(self.path[i][0] - self.px, self.path[i][1] - self.py))
                wp = self.path[min(j + 1, len(self.path) - 1)]
                if math.hypot(wp[0] - self.px, wp[1] - self.py) < 3:
                    wp = None
        if wp is None:
            self.auto = False
            self.aria_say(f"Kita sudah dekat {tg.objek}. Tekan E untuk memeriksanya.")
            return 0, 0
        return wp[0] - self.px, wp[1] - self.py

    # ---------------------------------------------------------- gambar
    def draw(self):
        s = self.screen
        self.ui_buttons = []
        s.fill(BG)
        if self.state == "menu":
            self.draw_menu(s)
        else:
            self.draw_world()
            self.draw_panel(s)
            self.draw_bars(s)
            if self.state == "journal":
                self.draw_journal(s)
            elif self.state == "accuse":
                self.draw_accuse(s)
            elif self.state == "result":
                self.draw_result(s)

    def draw_world(self):
        m = pygame.Surface((MAP_W, MAP_H))
        m.blit(self.static, (0, 0))
        t = self.t
        if self.guide and self.path:
            for i, (x, y) in enumerate(self.path):
                if i % 2 == 0:
                    r = 3 + int(1.5 * math.sin(t * 6 - i * 0.5))
                    pygame.draw.circle(m, ARIA_C, (x, y), max(2, r))
        items = []
        for it in self.inter:
            b = it["bukti"]
            done = b is None or b.id in self.found
            if it["kind"] == "obj":
                draw_icon(m, b.id, it["x"], it["y"], t)
                if done:
                    pygame.draw.circle(m, GOOD, (it["x"] + 22, it["y"] - 20), 8)
                    pygame.draw.lines(m, (10, 40, 20), False,
                                      [(it["x"] + 18, it["y"] - 20), (it["x"] + 21, it["y"] - 17),
                                       (it["x"] + 26, it["y"] - 24)], 2)
                else:
                    r = 26 + int(4 * math.sin(t * 4))
                    pygame.draw.circle(m, ACCENT, (it["x"], it["y"]), r, 2)
            else:
                items.append(("npc", it))
        items.append(("pl", None))
        items.sort(key=lambda a: a[1]["y"] if a[0] == "npc" else self.py)
        for kind, it in items:
            if kind == "pl":
                draw_char(m, int(self.px), int(self.py), (150, 112, 72), self.face, self.phase, self.moving, t)
            else:
                tcol = self.warna[it["saksi"].tid]
                draw_char(m, it["x"], it["y"] + 12, tcol, it["facing"], 0, False, t + it["x"], hat=(48, 52, 70))
                text(m, self.f_s, it["name"], (255, 255, 255), it["x"], it["y"] - 48, "c")
                b = it["bukti"]
                if b is not None and b.id not in self.found:
                    yy = it["y"] - 62 + int(3 * math.sin(t * 4))
                    pygame.draw.circle(m, ACCENT, (it["x"], yy), 8)
                    text(m, self.f_b, "!", (30, 20, 0), it["x"], yy, "c")
        # target petunjuk
        if self.target:
            ty = self.target.y - 40 + int(4 * math.sin(t * 5))
            pygame.draw.polygon(m, ARIA_C, [(self.target.x - 8, ty - 10), (self.target.x + 8, ty - 10),
                                            (self.target.x, ty)])
        # gelap + cahaya sekitar pemain
        self.dark.fill((3, 8, 13, 90))
        self.dark.blit(self.mask_big, (int(self.px) - 230, int(self.py) - 230), special_flags=pygame.BLEND_RGBA_SUB)
        for it in self.inter:
            b = it["bukti"]
            if b is not None and b.id not in self.found:
                self.dark.blit(self.mask_small, (it["x"] - 70, it["y"] - 70), special_flags=pygame.BLEND_RGBA_SUB)
        m.blit(self.dark, (0, 0))
        for p in self.particles:
            pygame.draw.circle(m, p[5], (int(p[0]), int(p[1])), 3)
        near = self.nearest()
        if near and not self.dialog and self.state == "play":
            label = f"[E] {'Bicara dengan' if near['kind'] == 'npc' else 'Periksa'} {near['name']}"
            r = self.f_m.render(label, True, TEXT).get_rect(center=(int(self.px), int(self.py) - 64))
            r = r.inflate(14, 8)
            r.clamp_ip(pygame.Rect(0, 0, MAP_W, MAP_H))
            box(m, r, (20, 24, 50), ACCENT, 6)
            text(m, self.f_m, label, (255, 255, 255), r.centerx, r.centery, "c")
        self.world_surface = m


    def draw_aria_face(self, s, x, y):
        pygame.draw.line(s, ARIA_C, (x + 26, y), (x + 26, y + 6), 2)
        pygame.draw.circle(s, ACCENT if int(self.t * 2) % 2 else ARIA_C, (x + 26, y), 3)
        box(s, pygame.Rect(x, y + 6, 52, 40), (28, 70, 86), ARIA_C, 10, 2)
        blink = (int(self.t * 10) % 40) == 0
        eh = 2 if blink else 8
        pygame.draw.rect(s, ARIA_C, (x + 10, y + 16, 8, eh), border_radius=3)
        pygame.draw.rect(s, ARIA_C, (x + 34, y + 16, 8, eh), border_radius=3)
        talking = self.aria_shown < len(self.aria_text)
        mh = 3 + int(abs(math.sin(self.t * 18)) * 5) if talking else 3
        pygame.draw.rect(s, ARIA_C, (x + 17, y + 32, 18, mh), border_radius=2)
    # ---------------------------------------------------------- loop
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                self.handle(e)
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()


def main():
    try:
        Game().run()
    except FileNotFoundError as ex:
        print(ex)
        sys.exit(1)


if __name__ == "__main__":
    main()
