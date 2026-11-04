"""Visual theme and screens for CASE UNKNOWN (all artwork is drawn in Pygame)."""
import math
import os

import pygame

import bayes_engine as be

W, H = 1280, 800
MAP_OX, MAP_OY = 24, 104
PANEL_X = 848
BG = (12, 17, 23)
PANEL = (20, 28, 36)
CARD = (26, 35, 44)
TEXT = (233, 235, 230)
DIM = (149, 166, 177)
ACCENT = (230, 183, 105)
ARIA_C = (105, 211, 203)
GOOD = (124, 213, 165)
BAD = (237, 128, 126)
LINE = (48, 63, 74)


def font(size, bold=False, display=False):
    name = "Rajdhani-SemiBold.ttf" if display else "Barlow-SemiBold.ttf" if bold else "Barlow-Regular.ttf"
    path = os.path.join(os.path.dirname(__file__), "assets", "fonts", name)
    if os.path.isfile(path):
        return pygame.font.Font(path, size)
    return pygame.font.SysFont("bahnschrift,dejavusans,arial", size, bold=bold)


def label(s, f, value, color, x, y, anchor="topleft"):
    img = f.render(str(value), True, color)
    rect = img.get_rect(**{anchor: (x, y)})
    s.blit(img, rect)
    return rect


def fit(f, value, width):
    value = str(value)
    if f.size(value)[0] <= width:
        return value
    while value and f.size(value + "...")[0] > width:
        value = value[:-1]
    return value.rstrip() + "..."


def lines(f, value, width):
    result = []
    for block in str(value).split("\n"):
        current = ""
        for word in block.split():
            candidate = (current + " " + word).strip()
            if f.size(candidate)[0] > width and current:
                result.append(current)
                current = word
            else:
                current = candidate
        result.append(current)
    return result


def prose(s, f, value, color, rect, step=23):
    """Draw wrapping text inside its bounds; callers use scrolling for long content."""
    rect = pygame.Rect(rect)
    old = s.get_clip()
    s.set_clip(old.clip(rect))
    y = rect.y
    for line in lines(f, value, rect.w):
        if y + f.get_height() > rect.bottom:
            break
        label(s, f, line, color, rect.x, y)
        y += step
    s.set_clip(old)
    return y


def card(s, rect, fill=PANEL, border=LINE, radius=12):
    rect = pygame.Rect(rect)
    pygame.draw.rect(s, fill, rect, border_radius=radius)
    if border:
        pygame.draw.rect(s, border, rect, 1, border_radius=radius)
    return rect


def rule(s, x, y, width, color=LINE):
    pygame.draw.line(s, color, (x, y), (x + width, y))


def progress(s, rect, value, color):
    rect = pygame.Rect(rect)
    card(s, rect, (38, 49, 59), None, rect.h // 2)
    if value > 0:
        fill = rect.copy()
        fill.w = max(rect.h, int(rect.w * min(1, value)))
        card(s, fill, color, None, rect.h // 2)


def keycap(s, f, key, x, y, color=DIM):
    width = max(25, f.size(key)[0] + 14)
    card(s, (x, y, width, 25), (30, 40, 50), LINE, 5)
    label(s, f, key, color, x + width // 2, y + 12, "center")
    return width


def magnifier(s, x, y, color=ACCENT, size=16):
    pygame.draw.circle(s, color, (x, y), size, 2)
    pygame.draw.line(s, color, (x + size * .7, y + size * .7), (x + size * 1.5, y + size * 1.5), 3)


class GameUI:
    def init_ui(self):
        self.f_s = font(14)
        self.f_m = font(17)
        self.f_b = font(18, bold=True)
        self.f_l = font(30, display=True)
        self.f_xl = font(58, display=True)
        self.f_hero = font(106, display=True)
        self.ui_buttons = []
        self.aria_scroll = 0
        self.journal_scroll = 0
        self.ui_scroll_rect = None
        self.aria_scroll_max = 0
        self.journal_scroll_max = 0
        self.aria_scroll_rect = None
        self.background = pygame.Surface((W, H))
        for y in range(H):
            k = y / H
            pygame.draw.line(self.background, (int(17 - 7 * k), int(25 - 8 * k), int(32 - 9 * k)), (0, y), (W, y))
        for x in range(24, W, 32):
            for y in range(24, H, 32):
                pygame.draw.circle(self.background, (33, 44, 52), (x, y), 1)

    def button(self, s, rect, title, key, primary=False, enabled=True, hint=None):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(pygame.mouse.get_pos()) and enabled
        fill = ACCENT if primary and enabled else (37, 53, 62) if hover else CARD
        border = ACCENT if primary or hover else LINE
        color = BG if primary and enabled else TEXT if enabled else DIM
        card(s, rect, fill, border, 8)
        if hint:
            label(s, self.f_s, hint, color, rect.x + 12, rect.centery, "midleft")
            offset = max(42, self.f_s.size(hint)[0] + 25)
            label(s, self.f_b, title, color, rect.x + offset, rect.centery, "midleft")
        else:
            label(s, self.f_b, title, color, *rect.center, "center")
        if enabled:
            self.ui_buttons.append((rect, key))

    def ui_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, key in reversed(self.ui_buttons):
                if rect.collidepoint(event.pos):
                    if isinstance(key, tuple):
                        self.activate_ui_selection(key)
                    else:
                        self.handle(pygame.event.Event(pygame.KEYDOWN, key=key))
                    return True
        if event.type == pygame.MOUSEWHEEL:
            pos = pygame.mouse.get_pos()
            if self.state == "play" and self.aria_scroll_rect and self.aria_scroll_rect.collidepoint(pos):
                self.aria_scroll = max(0, min(self.aria_scroll_max, self.aria_scroll - event.y * 36))
                return True
            if self.state == "journal" and self.ui_scroll_rect and self.ui_scroll_rect.collidepoint(pos):
                self.journal_scroll = max(0, min(self.journal_scroll_max, self.journal_scroll - event.y * 40))
                return True
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            direction = -1 if event.key == pygame.K_PAGEUP else 1
            if self.state == "journal":
                self.journal_scroll = max(0, min(self.journal_scroll_max, self.journal_scroll + direction * 180))
                return True
            if self.state == "play" and not self.dialog:
                self.aria_scroll = max(0, min(self.aria_scroll_max, self.aria_scroll + direction * 63))
                return True
        return False

    def draw_menu(self, s):
        s.blit(self.background, (0, 0))
        rule(s, 64, 78, W - 128)
        magnifier(s, 76, 43, ARIA_C, 10)
        label(s, self.f_b, "CASE UNKNOWN", TEXT, 101, 43, "midleft")
        label(s, self.f_s, "SEBUAH PERMAINAN INVESTIGASI", DIM, W - 64, 43, "midright")

        card(s, (64, 114, 256, 28), (41, 37, 30), (88, 72, 49), 4)
        label(s, self.f_s, "BERKAS 001  /  MUSEUM NUSANTARA", ACCENT, 76, 128, "midleft")
        label(s, self.f_hero, "CASE", TEXT, 60, 150)
        label(s, self.f_hero, "UNKNOWN", TEXT, 60, 236)
        rule(s, 64, 352, 40, ACCENT)
        label(s, self.f_l, "THE LAST CLUE", ACCENT, 118, 352, "midleft")
        prose(s, self.f_m, "Satu artefak hilang. Tiga orang menyimpan cerita.\nTemukan bukti, uji kecurigaan, dan ungkap kebenaran\nbersama ARIA, asisten AI detektifmu.", DIM, (64, 393, 560, 88), 26)

        self.button(s, (64, 508, 298, 58), "Mulai penyelidikan   >", pygame.K_RETURN, True)
        label(s, self.f_s, "ENTER / SPASI", DIM, 382, 537, "midleft")
        card(s, (64, 598, 556, 95), PANEL, LINE, 10)
        label(s, self.f_s, "PERLENGKAPAN DETEKTIF", ACCENT, 82, 612)
        controls = [("WASD", "Jelajahi"), ("E", "Periksa"), ("J", "Jurnal"), ("H", "ARIA")]
        for i, (key, desc) in enumerate(controls):
            x = 82 + i * 133
            width = keycap(s, self.f_s, key, x, 646)
            label(s, self.f_s, desc, TEXT, x + width + 8, 658, "midleft")

        self.draw_case_art(s)
        rule(s, 64, 736, W - 128)
        pygame.draw.circle(s, ARIA_C, (70, 765), 3)
        label(s, self.f_s, "OBSERVASI. ANALISIS. KESIMPULAN.", DIM, 84, 765, "midleft")
        label(s, self.f_s, "Cerita & data fiksi  /  Simulasi probabilitas Bayes", DIM, W - 64, 765, "midright")

    def draw_case_art(self, s):
        r = card(s, (692, 114, 524, 580), (18, 26, 33), LINE, 16)
        # An evidence board built from native shapes: no external image assets.
        for x in range(r.x + 24, r.right - 8, 24):
            for y in range(r.y + 24, r.bottom - 8, 24):
                pygame.draw.circle(s, (37, 49, 57), (x, y), 1)
        label(s, self.f_s, "PAPAN INVESTIGASI", DIM, r.x + 24, r.y + 20)
        card(s, (r.right - 133, r.y + 16, 110, 26), (45, 35, 29), (87, 60, 42), 4)
        label(s, self.f_s, "KASUS TERBUKA", ACCENT, r.right - 78, r.y + 29, "center")
        center = (r.centerx, r.y + 230)
        pygame.draw.circle(s, (29, 43, 49), center, 156, 1)
        pygame.draw.circle(s, (29, 43, 49), center, 135, 1)
        for a in (0.5, 2.6, 4.7):
            p = (center[0] + math.cos(a) * 147, center[1] + math.sin(a) * 147)
            pygame.draw.circle(s, ARIA_C, p, 3)
        photo = pygame.Rect(r.x + 111, r.y + 90, 302, 286)
        card(s, photo.move(6, 8), (9, 14, 19), None, 3)
        card(s, photo, (210, 204, 185), None, 3)
        inner = pygame.Rect(photo.x + 12, photo.y + 12, photo.w - 24, 214)
        card(s, inner, (29, 40, 46), None, 2)
        # Museum display case and the missing crown.
        pygame.draw.polygon(s, (38, 56, 62), [(inner.x + 28, inner.bottom - 30), (inner.centerx, inner.y + 22), (inner.right - 28, inner.bottom - 30)])
        stand = pygame.Rect(inner.centerx - 71, inner.bottom - 40, 142, 12)
        card(s, stand, (69, 85, 86), None, 2)
        pygame.draw.polygon(s, (39, 53, 60), [(stand.x + 10, stand.bottom), (stand.right - 10, stand.bottom), (stand.right - 20, stand.bottom + 25), (stand.x + 20, stand.bottom + 25)])
        cx, cy = inner.centerx, inner.centery + 10
        crown = [(cx - 58, cy - 34), (cx - 34, cy - 15), (cx - 24, cy - 51), (cx, cy - 24),
                 (cx + 24, cy - 51), (cx + 34, cy - 15), (cx + 58, cy - 34), (cx + 44, cy + 20), (cx - 44, cy + 20)]
        pygame.draw.polygon(s, (78, 77, 58), crown)
        pygame.draw.polygon(s, ACCENT, crown, 2)
        pygame.draw.line(s, ACCENT, (cx - 44, cy + 9), (cx + 44, cy + 9), 2)
        pygame.draw.polygon(s, ARIA_C, [(cx, cy - 8), (cx + 6, cy), (cx, cy + 8), (cx - 6, cy)], 1)
        label(s, self.f_l, "?", ARIA_C, cx, inner.y + 35, "center")
        label(s, font(21, display=True), "MAHKOTA BATARA GURU", (40, 47, 47), photo.centerx, photo.bottom - 38, "center")
        label(s, self.f_s, "OBJEK HILANG  /  20:00 WIB", (82, 86, 78), photo.centerx, photo.bottom - 17, "center")
        pygame.draw.circle(s, BAD, (photo.centerx, photo.y + 6), 5)
        # Red threads lead to each suspect's file.
        for i, suspect in enumerate(self.k.tersangka):
            x = r.x + 24 + i * 161
            y = r.y + 435
            pygame.draw.line(s, (112, 69, 63), (photo.centerx, photo.bottom), (x + 76, y), 1)
            card(s, (x, y, 153, 112), (28, 38, 46), LINE, 6)
            pygame.draw.circle(s, suspect.warna, (x + 27, y + 29), 15, 1)
            label(s, self.f_b, suspect.nama[0], suspect.warna, x + 27, y + 29, "center")
            label(s, self.f_s, "0" + str(i + 1), DIM, x + 135, y + 29, "midright")
            label(s, self.f_b, suspect.nama, TEXT, x + 14, y + 55)
            label(s, self.f_s, suspect.peran, DIM, x + 14, y + 80)
            pygame.draw.circle(s, BAD, (x + 76, y), 3)

    def draw_bars(self, s):
        card(s, (0, 0, W, 76), (16, 23, 30), None, 0)
        rule(s, 24, 75, W - 48)
        magnifier(s, 39, 32, ACCENT, 10)
        label(s, self.f_l, "CASE UNKNOWN", TEXT, 63, 15)
        label(s, self.f_s, "THE LAST CLUE", DIM, 65, 47)
        pygame.draw.line(s, LINE, (309, 20), (309, 56))
        label(s, self.f_s, "BERKAS 001", ACCENT, 332, 17)
        label(s, self.f_m, "Hilangnya Mahkota Batara Guru", TEXT, 332, 37)
        mm, ss = divmod(int(self.elapsed), 60)
        for x, title, value, color in [(754, "BUKTI TERKUMPUL", f"{len(self.found):02d} / {len(self.k.bukti):02d}", ACCENT),
                                        (932, "DURASI INVESTIGASI", f"{mm:02d}:{ss:02d}", TEXT)]:
            label(s, self.f_s, title, DIM, x, 15)
            label(s, self.f_l, value, color, x, 32)
        card(s, (1124, 24, 132, 28), (26, 47, 44), (45, 76, 68), 14)
        pygame.draw.circle(s, GOOD, (1139, 38), 3)
        label(s, self.f_s, "KASUS AKTIF", GOOD, 1150, 38, "midleft")
        room = next((l.nama for l in self.k.lokasi if pygame.Rect(l.x, l.y, l.w, l.h).collidepoint(self.px, self.py)), "Museum")
        label(s, self.f_s, "MUSEUM NUSANTARA", DIM, 25, 87, "midleft")
        label(s, self.f_s, room.upper(), ARIA_C, 824, 87, "midright")
        card(s, (23, 103, 802, 602), BG, LINE, 2)
        # The map was drawn first; this border never covers its contents.
        s.blit(self.world_surface, (MAP_OX, MAP_OY))
        if self.dialog and self.state == "play":
            self.draw_dialog(s)
        label(s, self.f_s, "WASD / PANAH", TEXT, 26, 732)
        label(s, self.f_s, "untuk menjelajahi museum", DIM, 26, 752)
        interactive = self.dialog is None
        self.button(s, (233, 728, 151, 46), "Periksa", pygame.K_e, enabled=interactive, hint="E")
        self.button(s, (396, 728, 174, 46), "Jurnal bukti", pygame.K_j, enabled=interactive, hint="J")
        self.button(s, (582, 728, 242, 46), "Buat kesimpulan", pygame.K_k, True, interactive, hint="K")

    def draw_panel(self, s):
        x, width = PANEL_X, W - PANEL_X - 24
        label(s, self.f_s, "RUANG ANALISIS", DIM, x, 87, "midleft")
        card(s, (x, 104, width, 247))
        label(s, self.f_b, "Probabilitas tersangka", TEXT, x + 18, 118)
        label(s, self.f_s, "BAYES", ARIA_C, x + width - 18, 122, "topright")
        ranking = be.peringkat(self.post)
        for i, (rank, tid, p) in enumerate(ranking):
            suspect = self.k.tersangka_by_id(tid)
            y = 157 + i * 61
            pygame.draw.circle(s, suspect.warna, (x + 33, y + 13), 15, 1)
            tied = sum(r[0] == rank for r in ranking) > 1
            label(s, self.f_s, ("=" if tied else "") + str(rank), suspect.warna, x + 33, y + 13, "center")
            label(s, self.f_b, suspect.nama, TEXT, x + 59, y - 5)
            label(s, self.f_s, suspect.peran, DIM, x + 143, y)
            label(s, self.f_b, f"{p:.0%}", TEXT, x + width - 19, y - 5, "topright")
            progress(s, (x + 59, y + 24, width - 126, 5), self.disp[tid], suspect.warna)
            delta = p - self.prev[tid]
            if abs(delta) >= .005:
                label(s, self.f_s, f"{delta * 100:+.0f}", GOOD if delta > 0 else BAD, x + width - 19, y + 19, "topright")

        card(s, (x, 363, width, 113))
        label(s, self.f_s, "JEJAK PROBABILITAS", DIM, x + 18, 375)
        label(s, self.f_s, f"{len(self.found)} bukti dianalisis", DIM, x + width - 18, 375, "topright")
        graph = pygame.Rect(x + 42, 407, width - 62, 51)
        for value in (0, .5, 1):
            y = graph.bottom - graph.h * value
            rule(s, graph.x, y, graph.w, (37, 49, 59))
        label(s, self.f_s, "100", DIM, x + 10, graph.y - 6)
        label(s, self.f_s, "0", DIM, x + 24, graph.bottom - 10)
        for suspect in self.k.tersangka:
            pts = [(graph.x + graph.w * i / max(1, len(self.k.bukti)), graph.bottom - graph.h * h[suspect.id])
                   for i, h in enumerate(self.history)]
            if len(pts) > 1:
                pygame.draw.lines(s, suspect.warna, False, pts, 2)
            for p in pts:
                pygame.draw.circle(s, suspect.warna, p, 3)

        r = card(s, (x, 490, width, 214), (18, 34, 39), (49, 91, 91))
        self.draw_aria_face(s, x + 17, r.y + 14)
        label(s, self.f_b, "ARIA", ARIA_C, x + 84, r.y + 15)
        label(s, self.f_s, "Asisten investigasi", DIM, x + 84, r.y + 37)
        label(s, self.f_s, f"{self.hints} petunjuk", DIM, r.right - 17, r.y + 21, "topright")
        viewport = pygame.Rect(x + 18, r.y + 74, width - 40, 90)
        self.aria_scroll_rect = viewport
        content = lines(self.f_m, self.aria_text[:int(self.aria_shown)], viewport.w - 9)
        self.aria_scroll_max = max(0, len(content) * 21 - viewport.h)
        self.aria_scroll = min(self.aria_scroll, self.aria_scroll_max)
        old = s.get_clip()
        s.set_clip(viewport)
        for i, line in enumerate(content):
            label(s, self.f_m, line, TEXT, viewport.x, viewport.y + i * 21 - self.aria_scroll)
        s.set_clip(old)
        if self.aria_scroll_max:
            track = pygame.Rect(r.right - 12, viewport.y, 3, viewport.h)
            card(s, track, LINE, None, 1)
            thumb_h = max(18, int(viewport.h * viewport.h / (len(content) * 21)))
            thumb_y = viewport.y + (viewport.h - thumb_h) * self.aria_scroll / self.aria_scroll_max
            card(s, (track.x, thumb_y, 3, thumb_h), ARIA_C, None, 1)
        interactive = self.dialog is None
        self.button(s, (x + 16, r.bottom - 37, 157, 26), "Petunjuk", pygame.K_h, enabled=interactive, hint="H")
        self.button(s, (x + 185, r.bottom - 37, width - 201, 26), "Berhenti" if self.auto else "Ikuti ARIA", pygame.K_g, enabled=interactive, hint="G")
        label(s, self.f_s, "Analisis berubah seiring bukti yang kamu temukan.", DIM, x, 731)
        label(s, self.f_s, "PGUP / PGDN  Baca ARIA     ESC  Menu", DIM, x, 753)

    def draw_dialog(self, s):
        d = self.dialog
        full_lines = lines(self.f_m, d["text"], 698)
        body_h = len(full_lines) * 23
        height = 76 + body_h + (57 if d["bukti"] else 0)
        r = pygame.Rect(MAP_OX + 20, MAP_OY + 600 - height - 18, 760, height)
        card(s, r.move(0, 5), (6, 10, 14), None)
        card(s, r, (22, 31, 39), d["col"])
        label(s, self.f_s, "WAWANCARA SAKSI" if d["who"] in {w.nama for w in self.k.saksi} else "PEMERIKSAAN OBJEK", DIM, r.x + 22, r.y + 12)
        label(s, self.f_b, d["who"], d["col"], r.x + 22, r.y + 31)
        prose(s, self.f_m, d["text"][:int(d["shown"])], TEXT, (r.x + 22, r.y + 59, r.w - 62, body_h), 23)
        if d["bukti"]:
            b = d["bukti"]
            rule(s, r.x + 22, r.y + 63 + body_h, r.w - 44)
            label(s, self.f_s, fit(self.f_s, "BUKTI BARU  /  " + b.nama, r.w - 180), GOOD, r.x + 22, r.y + 73 + body_h)
            label(s, self.f_s, f"Keandalan {b.keandalan:.0%}", DIM, r.x + 22, r.y + 94 + body_h)
        self.button(s, (r.right - 120, r.bottom - 35, 102, 25), "Lanjut", pygame.K_e, hint="E")

    def overlay(self, s, rect, title, subtitle):
        self.ui_buttons = []
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((5, 10, 15, 225))
        s.blit(dim, (0, 0))
        card(s, rect.move(0, 8), (4, 8, 12), None, 16)
        card(s, rect, PANEL, LINE, 16)
        label(s, self.f_s, "CASE UNKNOWN  /  BERKAS 001", ACCENT, rect.x + 28, rect.y + 20)
        label(s, self.f_l, title, TEXT, rect.x + 28, rect.y + 40)
        label(s, self.f_s, subtitle, DIM, rect.x + 28, rect.y + 79)
        rule(s, rect.x + 28, rect.y + 109, rect.w - 56)

    def draw_journal(self, s):
        r = pygame.Rect(64, 36, 1152, 728)
        self.overlay(s, r, "Jurnal bukti", "Setiap petunjuk menyimpan cerita. Periksa sumber dan keandalannya.")
        self.button(s, (r.right - 151, r.y + 35, 122, 35), "Tutup", pygame.K_j, hint="J")
        x, y = r.x + 28, r.y + 129
        label(s, self.f_s, f"INDEKS BUKTI  /  {len(self.found):02d} DITEMUKAN", DIM, x, y)
        for i, b in enumerate(self.k.bukti):
            row = pygame.Rect(x, y + 29 + i * 51, 345, 45)
            found, on = b.id in self.found, self.sel == i
            card(s, row, (40, 48, 47) if on else CARD, ACCENT if on else LINE, 7)
            label(s, self.f_s, b.id, ACCENT if found else DIM, row.x + 12, row.centery, "midleft")
            label(s, self.f_m, fit(self.f_m, b.nama if found else "Bukti belum ditemukan", 276), TEXT if found else DIM, row.x + 49, row.centery, "midleft")
            # Selection uses the same navigation path as the keyboard.
            self.ui_buttons.append((row, ("journal", i)))
        label(s, self.f_s, "PANAH ATAS / BAWAH  Pilih bukti", DIM, x, r.bottom - 47)
        pygame.draw.line(s, LINE, (r.x + 397, y), (r.x + 397, r.bottom - 28))
        viewport = pygame.Rect(r.x + 425, y, r.w - 453, r.h - 167)
        self.ui_scroll_rect = viewport
        b = self.k.bukti[self.sel]
        # Render the detail on a taller surface, then clip and scroll as needed.
        content = pygame.Surface((viewport.w, 1100))
        content.fill(PANEL)
        cy = 0
        label(content, self.f_s, "DOSSIER " + b.id, ACCENT, 0, cy)
        cy += 29
        title = b.nama if b.id in self.found else "Petunjuk yang belum terungkap"
        title_lines = lines(self.f_l, title, viewport.w - 12)
        for line in title_lines:
            label(content, self.f_l, line, TEXT, 0, cy)
            cy += 34
        cy += 12
        if b.id not in self.found:
            card(content, (0, cy, viewport.w - 12, 168), CARD, LINE)
            magnifier(content, 33, cy + 35, DIM, 11)
            label(content, self.f_b, "Jelajahi " + b.lokasi, ARIA_C, 61, cy + 23)
            prose(content, self.f_m, "Periksa objek bercahaya dan ajak saksi berbicara. Bukti akan tercatat otomatis setelah ditemukan.", DIM, (22, cy + 68, viewport.w - 56, 79), 24)
            cy += 193
            cy = self.detail_paragraph(content, "Bukti yang belum ditemukan tidak dianggap sebagai bukti negatif dan tidak mengubah peringkat tersangka.", DIM, cy, viewport.w - 16)
        else:
            for title, value in [("LOKASI", b.lokasi), ("SUMBER", b.sumber), ("OBJEK", b.objek)]:
                label(content, self.f_s, title, DIM, 0, cy)
                label(content, self.f_m, value, TEXT, 90, cy - 2)
                cy += 28
            cy += 12
            cy = self.detail_paragraph(content, b.deskripsi, TEXT, cy, viewport.w - 16)
            cy += 24
            label(content, self.f_b, "Keandalan bukti", TEXT, 0, cy)
            reliability = GOOD if b.keandalan >= .7 else ACCENT if b.keandalan >= .5 else BAD
            label(content, self.f_b, f"{b.keandalan:.0%}", reliability, viewport.w - 18, cy, "topright")
            progress(content, (0, cy + 32, viewport.w - 18, 7), b.keandalan, reliability)
            cy += 68
            label(content, self.f_b, "Likelihood per tersangka  P(E|H)", TEXT, 0, cy)
            cy += 31
            label(content, self.f_s, "TERSANGKA", DIM, 0, cy)
            label(content, self.f_s, "ASLI  /  EFEKTIF", DIM, viewport.w - 18, cy, "topright")
            cy += 30
            for suspect in self.k.tersangka:
                label(content, self.f_m, suspect.nama, suspect.warna, 0, cy - 3)
                progress(content, (91, cy + 5, viewport.w - 278, 6), b.likelihood[suspect.id], suspect.warna)
                label(content, self.f_m, f"{b.likelihood[suspect.id]:.2f}  /  {be.likelihood_efektif(b, suspect.id):.2f}", TEXT, viewport.w - 18, cy - 3, "topright")
                cy += 34
            cy += 10
            cy = self.detail_paragraph(content, "Likelihood efektif = r x P(E|H) + (1 - r) x 0.5. Keandalan rendah menarik nilai ke 0.5, sehingga pengaruh buktinya lebih kecil.", DIM, cy, viewport.w - 18, small=True)
            cy += 24
            rule(content, 0, cy, viewport.w - 18)
            label(content, self.f_s, "CATATAN ARIA", ARIA_C, 0, cy + 17)
            cy = self.detail_paragraph(content, b.petunjuk, TEXT, cy + 44, viewport.w - 18)
        self.journal_scroll_max = max(0, cy + 16 - viewport.h)
        self.journal_scroll = min(self.journal_scroll, self.journal_scroll_max)
        s.blit(content, viewport.topleft, (0, self.journal_scroll, viewport.w, viewport.h))
        if self.journal_scroll_max:
            track_h = viewport.h
            thumb_h = max(30, track_h * viewport.h / (cy + 16))
            thumb_y = viewport.y + (track_h - thumb_h) * self.journal_scroll / self.journal_scroll_max
            card(s, (r.right - 16, viewport.y, 3, track_h), LINE, None, 1)
            card(s, (r.right - 16, thumb_y, 3, thumb_h), ARIA_C, None, 1)
            label(s, self.f_s, "SCROLL / PGUP / PGDN  Detail bukti", DIM, r.right - 28, r.y + 87, "topright")

    def detail_paragraph(self, s, value, color, y, width, small=False):
        f, step = (self.f_s, 20) if small else (self.f_m, 24)
        for line in lines(f, value, width):
            label(s, f, line, color, 0, y)
            y += step
        return y

    def draw_accuse(self, s):
        r = pygame.Rect(92, 42, 1096, 716)
        self.overlay(s, r, "Susun kesimpulan", "Pilih tersangka dan bukti pendukung untuk menutup penyelidikan.")
        self.button(s, (r.right - 151, r.y + 35, 122, 35), "Kembali", pygame.K_ESCAPE)
        left, top = r.x + 28, r.y + 132
        label(s, self.f_b, "01  Tentukan tersangka", ACCENT, left, top)
        for i, suspect in enumerate(self.k.tersangka):
            row = pygame.Rect(left, top + 39 + i * 112, 354, 98)
            on = self.acc_suspect == suspect.id
            card(s, row, (37, 49, 51) if on else CARD, ACCENT if on else LINE, 10)
            keycap(s, self.f_s, str(i + 1), row.x + 15, row.y + 17, ACCENT if on else DIM)
            label(s, self.f_b, suspect.nama, TEXT, row.x + 56, row.y + 12)
            label(s, self.f_s, suspect.peran, DIM, row.x + 56, row.y + 38)
            label(s, self.f_s, f"Analisis ARIA  {self.post[suspect.id]:.0%}", ARIA_C, row.x + 56, row.y + 66)
            pygame.draw.circle(s, ACCENT if on else LINE, (row.right - 23, row.y + 24), 8, 2)
            if on:
                pygame.draw.circle(s, ACCENT, (row.right - 23, row.y + 24), 4)
            self.ui_buttons.append((row, pygame.K_1 + i))
        x = left + 390
        label(s, self.f_b, "02  Hubungkan bukti", ACCENT, x, top)
        label(s, self.f_s, f"{len(self.acc_picks)} DIPILIH", DIM, r.right - 28, top + 4, "topright")
        if not self.found:
            card(s, (x, top + 39, r.right - x - 28, 174), CARD, LINE)
            prose(s, self.f_m, "Jurnalmu masih kosong. Jelajahi museum dan periksa objek untuk mengumpulkan bukti pendukung.", DIM, (x + 23, top + 64, r.right - x - 74, 99), 25)
            self.button(s, (x, top + 232, 226, 42), "Lanjutkan penyelidikan", pygame.K_ESCAPE)
        for i, bid in enumerate(self.found):
            b = self.k.bukti_by_id(bid)
            row = pygame.Rect(x, top + 39 + i * 44, r.right - x - 28, 38)
            selected, focused = bid in self.acc_picks, i == self.acc_cur
            card(s, row, (31, 48, 46) if selected else CARD, ACCENT if focused else LINE, 6)
            cb = pygame.Rect(row.x + 12, row.y + 10, 18, 18)
            card(s, cb, GOOD if selected else PANEL, GOOD if selected else DIM, 4)
            if selected:
                pygame.draw.lines(s, BG, False, [(cb.x + 4, cb.y + 9), (cb.x + 8, cb.y + 13), (cb.x + 14, cb.y + 5)], 2)
            label(s, self.f_s, bid, ACCENT, row.x + 43, row.centery, "midleft")
            label(s, self.f_m, fit(self.f_m, b.nama, row.w - 94), TEXT, row.x + 77, row.centery, "midleft")
            self.ui_buttons.append((row, ("evidence", i)))
        rule(s, left, r.bottom - 99, r.w - 56)
        label(s, self.f_s, "1-3  Tersangka    PANAH  Bukti    SPASI  Pilih bukti", DIM, left, r.bottom - 68)
        label(s, self.f_s, "Kesimpulan akan mengakhiri investigasi ini.", DIM, left, r.bottom - 43)
        self.button(s, (r.right - 300, r.bottom - 77, 272, 49), "Kirim kesimpulan", pygame.K_RETURN, True, bool(self.acc_suspect), hint="ENTER")

    def draw_result(self, s):
        r = pygame.Rect(154, 40, 972, 720)
        res = self.result
        self.overlay(s, r, "Laporan akhir investigasi", "Museum Nusantara  /  Hilangnya Mahkota Batara Guru")
        col = GOOD if res["benar"] else BAD
        label(s, self.f_xl, "KASUS TERPECAHKAN" if res["benar"] else "KESIMPULAN KELIRU", col, r.x + 28, r.y + 126)
        label(s, self.f_m, f"Pelaku sebenarnya: {self.pelaku.nama}  /  {self.pelaku.peran}", TEXT, r.x + 30, r.y + 194)
        score = card(s, (r.x + 28, r.y + 245, 225, 183), (39, 38, 32), (83, 74, 52))
        label(s, self.f_s, "SKOR INVESTIGASI", ACCENT, score.centerx, score.y + 20, "midtop")
        label(s, self.f_hero, str(res["total"]), TEXT, score.centerx, score.y + 31, "midtop")
        label(s, self.f_s, "DARI 100 POIN", DIM, score.centerx, score.bottom - 22, "center")
        rows = [("Ketepatan tersangka", res["s_t"], int(self.k.param["skor_tersangka"])),
                (f"Bukti pendukung  ({res['ok']} relevan, {res['bad']} keliru)", res["s_b"], int(self.k.param["skor_bukti"])),
                ("Efisiensi investigasi", res["s_e"], int(self.k.param["skor_efisiensi"]))]
        x = r.x + 286
        for i, (title, value, maximum) in enumerate(rows):
            y = r.y + 254 + i * 57
            label(s, self.f_m, title, TEXT, x, y)
            label(s, self.f_b, f"{value} / {maximum}", ACCENT, r.right - 28, y, "topright")
            progress(s, (x, y + 30, r.right - x - 28, 6), value / max(1, maximum), col)
        label(s, self.f_l, res["grade"], ACCENT, r.x + 28, r.y + 449)
        note = card(s, (r.x + 28, r.y + 498, r.w - 56, 113), (18, 34, 39), (49, 91, 91))
        label(s, self.f_s, "CATATAN ARIA", ARIA_C, note.x + 18, note.y + 14)
        prose(s, self.f_m, res["debrief"], TEXT, (note.x + 18, note.y + 39, note.w - 36, 68), 23)
        self.button(s, (r.x + 28, r.bottom - 77, 283, 49), "Mulai investigasi baru", pygame.K_r, True, hint="R")
        self.button(s, (r.x + 326, r.bottom - 77, 196, 49), "Menu utama", pygame.K_ESCAPE, hint="ESC")

    def activate_ui_selection(self, selection):
        action, index = selection
        if action == "journal":
            self.sel, self.journal_scroll = index, 0
        elif action == "evidence":
            self.acc_cur = index
            self.acc_picks ^= {self.found[index]}
