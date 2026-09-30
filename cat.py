import math
import os
import random
import subprocess
import tkinter as tk

# AYARLAR - Beğenmediğin davranışları buradan değiştirilebilir

WINDOW_W, WINDOW_H = 140, 120       # Kedi penceresinin boyutu
GROUND_OFFSET = 60                  # Ekranın altından kaç piksel yukarıda yürüsün
                                     # (Dock'a çarpmasın diye biraz yukarıda tutuyoruz)
GRAVITY = 0.9                       # Yerçekimi ivmesi
JUMP_SPEED = -14                    # Zıplama başlangıç hızı (negatif = yukarı)
WALK_SPEED = 2.2                    # Yürüme hızı (piksel/frame)
FRAME_MS = 16                       # 60 FPS (16 ms'de bir güncelle)

# Duygu durumları için renkler
BODY_COLOR = "#555555"
BODY_OUTLINE = "#222222"
EAR_INNER = "#e8a0a0"

# Sentezlenmiş ses dosyalarının bulunduğu klasör (cat.py ile aynı yerde)
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
MEOW_HAPPY_WAV = os.path.join(ASSETS_DIR, "meow_happy.wav")
HISS_ANGRY_WAV = os.path.join(ASSETS_DIR, "hiss_angry.wav")
# İndirilen gerçek kayıtlar farklı uzantıda olabilir; hepsini kontrol 
SOUND_EXTENSIONS = (".wav", ".mp3", ".m4a", ".aiff", ".caf")



class DesktopCat:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._setup_window()

        #  Konum ve fizik değişkenleri 
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.ground_y = self.screen_h - WINDOW_H - GROUND_OFFSET

        self.x = self.screen_w // 2
        self.y = self.ground_y
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.direction = 1  # 1 = sağa bakıyor, -1 = sola bakıyor

        # Davranış / durum makinesi 
        self.state = "idle"          # idle, walk, jump, fall
        self.mood = None              # None, "happy", "angry", "surprised"
        self.mood_until = 0           # bu "tick" sayısına kadar mood geçerli
        self.behavior_timer = 0
        self.walk_phase = 0.0
        self.tail_phase = 0.0
        self.tick = 0

        # Hızlı tıklama takibi (art arda tıklayınca kızsın diye)
        self.click_times = []

        # Fareyle sürükleme (tutup taşıma) durumu
        self.is_dragging = False
        self._drag_start = {"x": 0, "y": 0}

        # O an çalmakta olan sesi takip et (üst üste binmesin diye)
        self._sound_proc = None

        self._move_window(int(self.x), int(self.y))
        self._pick_new_behavior()
        self._update()

    # PENCERE KURULUMU
    def _setup_window(self):
        root = self.root
        root.overrideredirect(True)          # Başlık çubuğu / kenarlık yok
        root.wm_attributes("-topmost", True)  # Her zaman en üstte
        try:
            # macOS'a özel: pencere arka planını şeffaf yap
            root.wm_attributes("-transparent", True)
            bg = "systemTransparent"
        except tk.TclError:
            # macOS dışında (Windows/Linux) şeffaflık farklı çalışır,
            # burada en azından programın açılmasını garantiliyoruz.
            bg = "black"
            try:
                root.wm_attributes("-transparentcolor", "black")
            except tk.TclError:
                pass

        root.config(bg=bg)
        root.geometry(f"{WINDOW_W}x{WINDOW_H}+0+0")

        self.canvas = tk.Canvas(
            root, width=WINDOW_W, height=WINDOW_H,
            bg=bg, highlightthickness=0, bd=0
        )
        self.canvas.pack()

        # Tıklama / sürükleme olayları
        # (Tek tık = sevin/kız, basılı tutup hareket ettirme = sürükleme)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        # Sağ tıkla programı kapatma imkanı (tepsi ikonu olmadığı için pratik)
        self.canvas.bind("<Button-2>", self.show_context_menu)
        self.canvas.bind("<Button-3>", self.show_context_menu)

    def _move_window(self, x, y):
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")

    # SES EFEKTLERİ (macOS 'say' ve sistem sesleri, ekstra kurulum gerekmez)
    def _play(self, cmd):
        # Önceki ses hâlâ çalıyorsa kes, yeni ses üst üste binip
        # anlaşılmaz olmasın (özellikle hızlı tıklamalarda önemli)
        try:
            if self._sound_proc is not None and self._sound_proc.poll() is None:
                self._sound_proc.terminate()
        except Exception:
            pass

        try:
            self._sound_proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass  # Ses çalmazsa bile program çökmesin

    def _find_sound(self, base_name):
        """assets/ içinde base_name.wav / .mp3 / .m4a / .aiff / .caf ara,
        ilk bulduğunu döndür. Hiçbiri yoksa None döner."""
        for ext in SOUND_EXTENSIONS:
            candidate = os.path.join(ASSETS_DIR, base_name + ext)
            if os.path.exists(candidate):
                return candidate
        return None

    def meow_happy(self):
        path = self._find_sound("meow_happy")
        if path:
            self._play(["afplay", path])
        else:
            self._play(["say", "-v", "Samantha", "miyav miyav"])

    def meow_angry(self):
        path = self._find_sound("hiss_angry")
        if path:
            self._play(["afplay", path])
        else:
            self._play([
                "bash", "-c",
                "afplay /System/Library/Sounds/Sosumi.aiff; say -r 300 'hışşşt'"
            ])

    def sound_surprised(self):
        self._play(["afplay", "/System/Library/Sounds/Pop.aiff"])

    # DAVRANIŞ SEÇİMİ (yapay "kedi beyni")

    def _pick_new_behavior(self):
        choice = random.choices(
            ["idle", "walk_left", "walk_right", "jump"],
            weights=[3, 3, 3, 1],
            k=1,
        )[0]

        if choice == "idle":
            self.state = "idle"
            self.vx = 0
            self.behavior_timer = random.randint(60, 180)  # ~1-3 sn
        elif choice == "walk_left":
            self.state = "walk"
            self.direction = -1
            self.vx = -WALK_SPEED
            self.behavior_timer = random.randint(90, 220)
        elif choice == "walk_right":
            self.state = "walk"
            self.direction = 1
            self.vx = WALK_SPEED
            self.behavior_timer = random.randint(90, 220)
        elif choice == "jump":
            self._start_jump()

    def _start_jump(self):
        if self.on_ground:
            self.state = "jump"
            self.on_ground = False
            self.vy = JUMP_SPEED
            self.behavior_timer = 999  # düşene kadar bu davranışta kal

    # SÜRÜKLEME (fareyle tutup taşıma)

    def on_press(self, event):
        # Farenin canvas üzerindeki (pencereye göre) konumunu kaydet
        self._drag_start = {"x": event.x, "y": event.y, "moved": False}
        self.is_dragging = True
        # Sürüklerken otonom hareketi/fiziği durdur
        self.vx = 0
        self.vy = 0
        self.on_ground = True
        self.state = "held"

    def on_drag(self, event):
        dx = event.x - self._drag_start["x"]
        dy = event.y - self._drag_start["y"]

        if abs(dx) > 3 or abs(dy) > 3:
            self._drag_start["moved"] = True

        new_x = self.x + dx
        new_y = self.y + dy
        # Ekran dışına çıkmasın
        new_x = max(0, min(new_x, self.screen_w - WINDOW_W))
        new_y = max(0, min(new_y, self.screen_h - WINDOW_H))

        self.x = new_x
        self.y = new_y
        self._move_window(int(self.x), int(self.y))

    def on_release(self, event):
        self.is_dragging = False

        if not self._drag_start.get("moved", False):
            # Fare hiç hareket etmedi -> bu bir sürükleme değil, düz tıklamaydı
            self.on_click(event)
            return

        # Sürüklenip bırakıldı: havadaysa yere düşsün (yerçekimi devam etsin)
        if self.y < self.ground_y:
            self.on_ground = False
            self.vy = 0
            self.state = "fall"
        else:
            self.y = self.ground_y
            self.on_ground = True
            self._land_reaction()  # elden bırakılınca da şaşkın tepki versin
            self._pick_new_behavior()

    # SAĞ TIK MENÜSÜ (sevimli / kızgın modunu elle seç)

    def show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="😊 Sevimli yap", command=self.force_happy)
        menu.add_command(label="😾 Kızgın yap", command=self.force_angry)
        menu.add_separator()
        menu.add_command(label="❌ Kediyi Kapat", command=self.root.destroy)
        menu.tk_popup(event.x_root, event.y_root)

    def force_happy(self):
        self.mood = "happy"
        self.mood_until = self.tick + 90  # ~1.5 sn
        self.meow_happy()

    def force_angry(self):
        self.mood = "angry"
        self.mood_until = self.tick + 90
        self.meow_angry()

    # TIKLAMA TEPKİLERİ

    def on_click(self, event):
        now = self.tick
        self.click_times.append(now)
        # Son 40 tick (~0.6 sn) içindeki tıklamaları say
        self.click_times = [t for t in self.click_times if now - t < 40]

        if len(self.click_times) >= 3:
            # Art arda hızlı tıklandı -> kızdı
            self.mood = "angry"
            self.mood_until = now + 70
            self.meow_angry()
        else:
            # Tek tık -> mutlu oldu
            self.mood = "happy"
            self.mood_until = now + 70
            self.meow_happy()

    def _land_reaction(self):
        """Yere her düştüğünde çağrılır: şaşkın tepki + ses."""
        self.mood = "surprised"
        self.mood_until = self.tick + 25
        self.sound_surprised()

    # ANA DÖNGÜ: fizik + durum + çizim
    def _update(self):
        self.tick += 1

        # Sürüklenirken otonom fizik/davranış tamamen devre dışı
        # (konumu zaten on_drag ayarlıyor)
        if self.is_dragging:
            self.tail_phase += 0.08
            self._draw()
            self.root.after(FRAME_MS, self._update)
            return

        # Fizik: yerçekimi 
        if not self.on_ground:
            self.vy += GRAVITY
            self.y += self.vy
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self.vy = 0
                self.on_ground = True
                self._land_reaction()
                self._pick_new_behavior()

        # Yatay hareket 
        if self.state == "walk" and self.on_ground:
            self.x += self.vx
            self.walk_phase += 0.35
            # Ekran kenarına çarparsa yön değiştir / yeni davranış seç
            if self.x <= 0 or self.x >= self.screen_w - WINDOW_W:
                self.x = max(0, min(self.x, self.screen_w - WINDOW_W))
                self._pick_new_behavior()

        self.tail_phase += 0.08

        # Davranış zamanlayıcısı 
        if self.on_ground:
            self.behavior_timer -= 1
            if self.behavior_timer <= 0:
                self._pick_new_behavior()

        # Mood süresi doldu mu?
        if self.mood is not None and self.tick > self.mood_until:
            self.mood = None

        self._move_window(int(self.x), int(self.y))
        self._draw()

        self.root.after(FRAME_MS, self._update)


    # KIZGINKEN KABARAN TÜY EFEKTİ
    def _draw_fur_spikes(self, cx, cy, radius, count=16, length=9):
        """cx,cy merkezli bir dairenin etrafına küçük dikenler (kabarık tüy) çizer."""
        c = self.canvas
        for i in range(count):
            angle = (2 * math.pi * i) / count
            base_x = cx + radius * math.cos(angle)
            base_y = cy + radius * math.sin(angle)
            tip_x = cx + (radius + length) * math.cos(angle)
            tip_y = cy + (radius + length) * math.sin(angle)

            perp = angle + math.pi / 2
            half_w = 2.5
            b1x = base_x + half_w * math.cos(perp)
            b1y = base_y + half_w * math.sin(perp)
            b2x = base_x - half_w * math.cos(perp)
            b2y = base_y - half_w * math.sin(perp)

            c.create_polygon(
                b1x, b1y, b2x, b2y, tip_x, tip_y,
                fill=BODY_COLOR, outline="",
            )

    def _draw(self):
        c = self.canvas
        c.delete("all")

        cx, cy = WINDOW_W // 2, WINDOW_H - 35  # gövde merkezi
        d = self.direction

        # Ayakta değilse (zıplama/düşme) hafif eğim/gerilme efekti
        squash = 1.0
        if not self.on_ground:
            squash = 0.85

        # Kuyruk (gövdenin arkasında sallanır) 
        tail_wave = math.sin(self.tail_phase) * 12
        tail_base_x = cx - d * 22
        c.create_line(
            tail_base_x, cy,
            tail_base_x - d * 15, cy - 20 + tail_wave,
            tail_base_x - d * 10, cy - 35 + tail_wave * 0.6,
            smooth=True, width=6, fill=BODY_COLOR, capstyle=tk.ROUND,
        )

        #  Bacaklar (yürürken zıt fazda hareket eder) 
        leg_offset = math.sin(self.walk_phase) * 6 if self.state == "walk" else 0
        for i, lx in enumerate([-14, -4, 4, 14]):
            phase = leg_offset if i % 2 == 0 else -leg_offset
            c.create_rectangle(
                cx + lx - 4, cy + 10,
                cx + lx + 4, cy + 20 + phase * 0.3,
                fill="#333333", outline="",
            )

        #  Kızgınken tüyler kabarsın (gövde/kafanın etrafına diken) 
        if self.mood == "angry":
            self._draw_fur_spikes(cx, cy - 4, 30)

        #  Gövde 
        body_rx, body_ry = 32, int(20 * squash)
        c.create_oval(
            cx - body_rx, cy - body_ry,
            cx + body_rx, cy + body_ry,
            fill=BODY_COLOR, outline=BODY_OUTLINE, width=2,
        )

        # Kafa 
        head_cx = cx + d * 20
        head_cy = cy - 26
        head_r = 22

        if self.mood == "angry":
            self._draw_fur_spikes(head_cx, head_cy, head_r + 2)

        c.create_oval(
            head_cx - head_r, head_cy - head_r,
            head_cx + head_r, head_cy + head_r,
            fill=BODY_COLOR, outline=BODY_OUTLINE, width=2,
        )

        # --- Kulaklar ---
        for ex in (-14, 14):
            bx = head_cx + ex
            c.create_polygon(
                bx - 10, head_cy - 14,
                bx + 10, head_cy - 14,
                bx, head_cy - 34,
                fill=BODY_COLOR, outline=BODY_OUTLINE,
            )
            c.create_polygon(
                bx - 5, head_cy - 17,
                bx + 5, head_cy - 17,
                bx, head_cy - 28,
                fill=EAR_INNER, outline="",
            )

        # --- Yüz ifadesi (mood'a göre değişir) ---
        self._draw_face(head_cx, head_cy)

        # --- Mutluysa kalp, kızgınsa öfke çizgisi ---
        if self.mood == "happy":
            c.create_text(head_cx, head_cy - 42, text="❤", fill="#ff4d6d",
                           font=("Helvetica", 14, "bold"))
        elif self.mood == "angry":
            c.create_line(head_cx - 10, head_cy - 40, head_cx, head_cy - 34,
                           fill="red", width=3)
            c.create_line(head_cx + 10, head_cy - 40, head_cx, head_cy - 34,
                           fill="red", width=3)
        elif self.mood == "surprised":
            c.create_text(head_cx, head_cy - 42, text="!", fill="#ffcc00",
                           font=("Helvetica", 16, "bold"))

    def _draw_face(self, hx, hy):
        c = self.canvas
        # Elde tutulurken sese gerek yok ama yüz şaşkın görünsün
        mood = "surprised" if (self.state == "held" and self.mood is None) else self.mood

        if mood == "happy":
            # ^  ^  mutlu gözler (kavisli çizgi)
            for ex in (-8, 8):
                c.create_arc(hx + ex - 6, hy - 4, hx + ex + 6, hy + 6,
                             start=0, extent=180, style=tk.ARC, width=2)
            # gülümseme
            c.create_arc(hx - 8, hy + 2, hx + 8, hy + 14,
                         start=200, extent=140, style=tk.ARC, width=2)

        elif mood == "angry":
            # eğik kızgın kaşlar + gözler
            for ex, sign in ((-8, 1), (8, -1)):
                c.create_line(hx + ex - 6, hy - 8 + (2 if sign > 0 else -2),
                              hx + ex + 6, hy - 8 - (2 if sign > 0 else -2),
                              width=2)
                c.create_oval(hx + ex - 3, hy - 2, hx + ex + 3, hy + 4,
                              fill="black")
            # dişli ağız
            c.create_line(hx - 8, hy + 12, hx + 8, hy + 12, width=2)

        elif mood == "surprised":
            # kocaman şaşkın gözler
            for ex in (-8, 8):
                c.create_oval(hx + ex - 6, hy - 6, hx + ex + 6, hy + 6,
                              fill="white", outline="black")
                c.create_oval(hx + ex - 2, hy - 2, hx + ex + 2, hy + 2,
                              fill="black")
            c.create_oval(hx - 3, hy + 8, hx + 3, hy + 14, outline="black", width=2)

        else:
            # normal / yürürken sakin gözler
            for ex in (-8, 8):
                c.create_oval(hx + ex - 3, hy - 2, hx + ex + 3, hy + 4,
                              fill="black")
            # burun
            c.create_polygon(hx - 2, hy + 6, hx + 2, hy + 6, hx, hy + 9,
                             fill="#ff9aa2")