#!/usr/bin/env python3
"""
Pixel Art Animated Companion — Princess Mia
Interactive animated pixel art with live breathing, blinking, reactions,
and an animated speech cloud replying when you say "hello".

Supports:
  - Tkinter Desktop GUI Popup (Default if display available)
  - Interactive Animated ANSI Terminal Mode (--terminal)
"""

import sys
import os
import time
import math
import select
import threading

PALETTE = {
    " ": None,                  # Transparent / background

    # Sparkles & Floating Hearts
    "*": (255, 230, 120),       # Gold sparkle
    "+": (255, 245, 180),       # Light sparkle
    "~": (255, 185, 230),       # Soft pink sparkle
    "v": (255, 100, 175),       # Heart vibrant pink
    "V": (210, 40, 120),        # Heart dark outline

    # Hair (Rich Auburn / Caramel Chestnut)
    "H": (65, 30, 18),          # Hair deep outline / shadow
    "h": (120, 58, 32),         # Hair main base
    "L": (180, 98, 55),         # Hair mid-tone
    "l": (230, 155, 95),        # Hair bright highlight
    "j": (255, 205, 155),       # Hair glossy shine

    # Hair Ribbon / Big Head Bow
    "R": (145, 18, 75),         # Bow deep outline
    "r": (215, 40, 120),        # Bow shadow
    "Q": (255, 95, 165),        # Bow main pink
    "q": (255, 170, 215),       # Bow highlight pink
    "W": (255, 255, 255),       # White lace & highlight

    # Skin & Face
    "O": (195, 120, 90),        # Skin shadow contour
    "o": (240, 170, 140),       # Skin soft shade
    "S": (255, 222, 200),       # Skin main base
    "s": (255, 240, 228),       # Skin bright highlight
    "b": (255, 140, 160),       # Soft blush
    "B": (255, 85, 115),        # Deep rosy blush

    # Eyes & Mouth
    "E": (25, 20, 45),          # Eye lash & pupil
    "e": (45, 115, 210),        # Eye sapphire blue iris
    "i": (120, 205, 255),       # Eye bright cyan highlight
    "m": (230, 70, 95),         # Sweet smiling mouth

    # Pink Princess Dress
    "D": (135, 15, 70),         # Dress dark outline
    "d": (195, 30, 105),        # Dress shadow folds
    "P": (255, 85, 155),        # Dress vibrant rose pink
    "p": (255, 135, 188),       # Dress bright pink body
    "X": (255, 185, 220),       # Dress soft pastel highlight
    "x": (255, 225, 242),       # Dress pale pink glow
    "w": (255, 250, 253),       # Frilly white lace / petticoat

    # Waist Sash / Belt Bow
    "Z": (120, 12, 60),         # Sash deep fold
    "z": (180, 25, 95),         # Sash shadow
    "A": (245, 55, 135),        # Sash main pink
    "a": (255, 130, 185),       # Sash highlight

    # Flowers Bouquet held in hands
    "G": (35, 125, 45),         # Foliage dark green
    "g": (75, 195, 75),         # Foliage bright leaf
    "F": (255, 215, 0),         # Flower golden yellow
    "f": (255, 248, 140),       # Flower light petals
    "C": (255, 75, 80),         # Red mini rose blossom

    # Legs, Socks & Shoes
    "k": (248, 248, 255),       # White frilly socks
    "K": (205, 205, 225),       # Socks shadow fold
    "U": (150, 18, 70),         # Mary Jane shoes ruby pink
    "u": (235, 50, 120),        # Mary Jane shoes bright pink
    "M": (95, 12, 45),          # Shoe sole

    # Ground
    ".": (225, 185, 205),       # Ground shadow

    # Speech Cloud (Terminal)
    "Y": (255, 255, 255),       # Cloud white body
    "y": (210, 225, 245),       # Cloud soft shaded edge
    "T": (255, 40, 120),        # Cloud animated text
}

BASE_ART = [
    # 0..1: Floating heart & sparkles
    "                  ~*~                   ",
    "       *~        vVVv         ~*        ",
    # 2..5: Big cute hair ribbon & head crown
    "        ~       vQQQv        +          ",
    "      RqQR       vVVv        RQqR       ",
    "     RQQQQr  HHHHHHHHHHHH    rQQQQR     ",
    "     rQQQQQRHhhLLllllLLhhHR RQQQQQr     ",
    # 6..9: Glossy hair & forehead bangs
    "      RqqQR HhLljjjjjjllLhH RqqQr       ",
    "       rQr  HhLljjHHHHjjjlLhH rQr       ",
    "        R   HhLjjHssssssHjjjlLhHR   ~   ",
    "   *         HhLljHssssssssHjllLhH  *   ",
    # 10..13: Eyes, lashes, blushing cheeks
    "        HhLLhHssSssssSssHhLLLhH         ",
    "        HhLLhHssSssssSssHhLLLhH         ",
    "        HhLLhHsSEEESSSSEEESHhLLh        ",
    "        HhLLhHSWEeESSSSEeWSHhLLh        ",
    # 14..17: Eye iris, sweet smile, chin contour
    "   ~    HhLLhHSEiEESSSSEEiESHhLLh  +    ",
    "        HHhhHOsbBBsSSsBBbsOHhhhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSssSmmSssSOHHHH          ",
    # 18..20: Neck, white lace collar & tiny neck ribbon
    "              OSsSSsSO                  ",
    "             wWddPPddWw                 ",
    "            wWwPaAAaPwWw     ~          ",
    # 21..24: Bodice of pink dress, puffed sleeves, flower bouquet in hands
    "          dPPPwPaAAaPwPPPd              ",
    "         dPPXPdPaAAaPdPXPPd   *         ",
    "        DPPXXPdzZAAAAZzdPXXPPD          ",
    "        DPPXXSOFffFCCFOOSXXPPD          ",
    # 25..28: Hands, flower bouquet, sash bow
    "        HPXSSgffCCFFffgSSXPH            ",
    "   *     HSsOGGCFffCGGOsSH              ",
    "          HHOdZzAAAAAAzDOHH             ",
    "            dZzAAAAAAzZD                ",
    # 29..32: Flared skirt upper tiers
    "           DPpPzAAAAzPpPD               ",
    "          DPPPpAAAAAApPPPD              ",
    "         DPpPXpPAAAAPpXPpPD             ",
    "        DPpPXxxPpPPxxXPpPD      ~       ",
    # 33..36: Flowing ruffled skirt pleats
    "       DPpPXXxxPpPPxxXXPpPD             ",
    "      DPpPXXxxxxPpPxxxxXXPpPD           ",
    "     DPpPXXxxxxwPpPxxxxXXPpPD           ",
    "    DPpPXXxxxwwDPpPDwwxxxXXPpPD   *     ",
    # 37..39: Frilly white lace hemline of dress
    "   DPpPXXxxwwDDwPpPwDDwwxxXXPpPD        ",
    "   dwwwwwwwwwwDdwwdDwwwwwwwwwwd         ",
    "    DDDDDDDDDDDDDDDDDDDDDDDDDD          ",
    # 40..42: Legs, frilly white ankle socks
    "              OSSSO  OSSSO              ",
    "              OSSSO  OSSSO              ",
    "              OwkwO  OwkwO       ~      ",
    # 43..45: Mary Jane pink shoes & ground shadow
    "             uUKKuO  uUKKuO             ",
    "             uUUUUu  uUUUUu             ",
    "             MMMMMM  MMMMMM             ",
    # 46: Ground sparkles
    "       .   ......  ......  .      *     ",
]

# Facial variation layers (Rows 12..17)
FACE_OPEN = [
    "        HhLLhHsSEEESSSSEEESHhLLh        ",
    "        HhLLhHSWEeESSSSEeWSHhLLh        ",
    "   ~    HhLLhHSEiEESSSSEEiESHhLLh  +    ",
    "        HHhhHOsbBBsSSsBBbsOHhhhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSssSmmSssSOHHHH          ",
]

FACE_HALF_BLINK = [
    "        HhLLhHssEEssSSSSssEEsHhLh       ",
    "        HhLLhHsSEEEsSSSSsEEEsHhLh       ",
    "   ~    HhLLhHssSssssSSssssSHhLLh  +    ",
    "        HHhhHOsbBBsSSsBBbsOHhhhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSssSmmSssSOHHHH          ",
]

FACE_BLINK = [
    "        HhLLhHssssssssssssssHhLLh       ",
    "        HhLLhHsSEEEESSSSEEEEsHhLh       ",
    "   ~    HhLLhHssssssssssssssHhLLh  +    ",
    "        HHhhHOsbBBsSSsBBbsOHhhhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSssSmmSssSOHHHH          ",
]

# Happy smiling eyes and rosy blush when greeting
FACE_HAPPY = [
    "        HhLLhHsSssEESSSSEEssSHhLh       ",
    "        HhLLhHsEEEEsSSSsEEEEsHhLh       ",
    "   ~    HhLLhHsSssssSSSSssssSHhLLh  +    ",
    "        HHhhHObBBBBsSSsBBBBbOHhh        ",
    "         HHhHOssSSSSSSSSssOHhHH         ",
    "          HHHHOSsSmmmmSssSOHHHH         ",
]

# Sparkle patterns for idle animation (Rows 0, 1, 9, 26, 41, 46)
SPARKLE_FRAMES = [
    {
        0: "                  ~*~                   ",
        1: "       *~        vVVv         ~*        ",
        9: "   *         HhLljHssssssssHjllLhH  *   ",
       26: "   *     HSsOGGCFffCGGOsSH              ",
       41: "              OwkwO  OwkwO       ~      ",
       46: "       .   ......  ......  .      *     ",
    },
    {
        0: "                  *~+                   ",
        1: "       +*        vVVv         *~        ",
        9: "   ~         HhLljHssssssssHjllLhH  +   ",
       26: "   +     HSsOGGCFffCGGOsSH              ",
       41: "              OwkwO  OwkwO       *      ",
       46: "       *   ......  ......  *      .     ",
    },
    {
        0: "                  +*~                   ",
        1: "       ~+        vVVv         +*        ",
        9: "   +         HhLljHssssssssHjllLhH  ~   ",
       26: "   ~     HSsOGGCFffCGGOsSH              ",
       41: "              OwkwO  OwkwO       +      ",
       46: "       ~   ......  ......  .      +     ",
    },
]

def build_frame(face_type="OPEN", sparkle_idx=0):
    """Assembles a 47-row character grid with the given face and sparkle frame."""
    frame = list(BASE_ART)
    
    # Choose face
    if face_type == "BLINK":
        face_rows = FACE_BLINK
    elif face_type == "HALF":
        face_rows = FACE_HALF_BLINK
    elif face_type == "HAPPY":
        face_rows = FACE_HAPPY
    else:
        face_rows = FACE_OPEN
        
    for idx, row in enumerate(face_rows):
        frame[12 + idx] = row
        
    # Apply sparkle frame
    sparkle_map = SPARKLE_FRAMES[sparkle_idx % len(SPARKLE_FRAMES)]
    for row_idx, content in sparkle_map.items():
        frame[row_idx] = content
        
    return frame

def render_ansi_grid(lines):
    """Renders pixel art lines using unicode half-blocks and 24-bit ANSI colors."""
    num_rows = len(lines)
    num_cols = len(lines[0])
    output = []
    
    for row_idx in range(0, num_rows, 2):
        top_row = lines[row_idx]
        bot_row = lines[row_idx + 1] if row_idx + 1 < num_rows else " " * num_cols
        
        line_chars = []
        for col_idx in range(num_cols):
            top_char = top_row[col_idx] if col_idx < len(top_row) else " "
            bot_char = bot_row[col_idx] if col_idx < len(bot_row) else " "
            
            top_color = PALETTE.get(top_char)
            bot_color = PALETTE.get(bot_char)
            
            if top_color is None and bot_color is None:
                line_chars.append(" ")
            elif top_color is not None and bot_color is None:
                r, g, b = top_color
                line_chars.append(f"\033[38;2;{r};{g};{b}m▀\033[0m")
            elif top_color is None and bot_color is not None:
                r, g, b = bot_color
                line_chars.append(f"\033[38;2;{r};{g};{b}m▄\033[0m")
            else:
                tr, tg, tb = top_color
                br, bg, bb = bot_color
                line_chars.append(f"\033[38;2;{tr};{tg};{tb}m\033[48;2;{br};{bg};{bb}m▀\033[0m")
        
        output.append("".join(line_chars))
    return "\n".join(output)

# ---------------------------------------------------------------------------
# Terminal Mode Animation
# ---------------------------------------------------------------------------

def run_terminal_app(initial_greeting=False):
    """Runs interactive animated companion inside the terminal."""
    print("\033[2J\033[H\033[?25l", end="", flush=True)  # Clear screen, hide cursor
    
    speech_active = initial_greeting
    speech_end_time = time.time() + 5.0 if initial_greeting else 0.0
    speech_text = "H E L L O !"
    
    frame_count = 0
    running = True
    input_buffer = ""
    
    print("\033[38;2;255;105;180m  ✨ ✿ Princess Mia ✿ ✨ — Terminal Companion\033[0m")
    print("\033[38;2;200;180;220m  Type 'hello' and hit Enter! (or 'q' to exit)\033[0m\n")

    try:
        while running:
            now = time.time()
            frame_count += 1
            
            # Check speech cloud active duration
            if speech_active and now > speech_end_time:
                speech_active = False
                
            # Determine face expression
            if speech_active:
                face = "HAPPY"
            else:
                # Idle blinking cycle: blink every ~3.5 seconds (35 frames at 10fps)
                blink_phase = frame_count % 36
                if blink_phase == 32:
                    face = "HALF"
                elif blink_phase in (33, 34):
                    face = "BLINK"
                elif blink_phase == 35:
                    face = "HALF"
                else:
                    face = "OPEN"
                    
            sparkle_idx = (frame_count // 3) % len(SPARKLE_FRAMES)
            grid = build_frame(face, sparkle_idx)
            
            # If speech cloud is active, render cloud lines above her head
            cloud_lines = []
            if speech_active:
                # Animated cloud text shimmer
                bounce = " " if (frame_count % 4 < 2) else "  "
                cloud_top = "          ╭────────────────────────╮    "
                cloud_mid = f"       (  ✨   {speech_text}   ✨ )  "
                cloud_bot = "          ╰───────╮  ──────────────╯    "
                cloud_pt1 = "                  ╰─╮                   "
                cloud_pt2 = "                     o                  "
                cloud_lines = [
                    f"\033[1;38;2;255;182;193m{cloud_top}\033[0m",
                    f"\033[1;38;2;255;255;255m\033[48;2;215;40;120m{cloud_mid}\033[0m",
                    f"\033[1;38;2;255;182;193m{cloud_bot}\033[0m",
                    f"\033[38;2;255;200;220m{cloud_pt1}\033[0m",
                    f"\033[38;2;255;200;220m{cloud_pt2}\033[0m",
                ]
            else:
                cloud_lines = ["\033[K" for _ in range(5)]
                
            # Reposition cursor home (flicker-free redraw)
            sys.stdout.write("\033[3;1H")
            for c_line in cloud_lines:
                sys.stdout.write(f"{c_line}\033[K\n")
                
            rendered_art = render_ansi_grid(grid)
            sys.stdout.write(rendered_art + "\n")
            
            # Interactive prompt line at the bottom
            sys.stdout.write(f"\033[K\n\033[1;38;2;255;105;180mSay something (e.g. 'hello'):\033[0m {input_buffer}")
            sys.stdout.flush()
            
            # Non-blocking stdin check
            rlist, _, _ = select.select([sys.stdin], [], [], 0.08)
            if rlist:
                ch = sys.stdin.read(1)
                if ch in ("\n", "\r"):
                    cmd = input_buffer.strip().lower()
                    input_buffer = ""
                    if cmd in ("q", "quit", "exit"):
                        running = False
                        break
                    elif "hello" in cmd or "hi" in cmd or "hey" in cmd:
                        speech_active = True
                        speech_text = "H E L L O !"
                        speech_end_time = now + 4.5
                    elif "love" in cmd or "cute" in cmd or "pretty" in cmd:
                        speech_active = True
                        speech_text = "THANK YOU! ♥"
                        speech_end_time = now + 4.5
                    elif cmd:
                        speech_active = True
                        speech_text = "HELLO THERE! 💖"
                        speech_end_time = now + 4.5
                elif ch in ("\x7f", "\x08"):  # Backspace
                    input_buffer = input_buffer[:-1]
                elif ch == "\x1b":  # Escape
                    running = False
                    break
                elif ch.isprintable():
                    input_buffer += ch
                    
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\033[0m\n")  # Restore cursor
        print("Goodbye! ✨\n")

# ---------------------------------------------------------------------------
# Tkinter GUI Desktop Popup Mode
# ---------------------------------------------------------------------------

class PixelGirlPopup:
    def __init__(self, pixel_size=10, initial_greeting=False):
        import tkinter as tk
        self.tk = tk
        
        self.root = tk.Tk()
        self.root.title("✨ ✿ Princess Mia ✿ ✨ (Interactive Companion)")
        self.root.configure(bg="#14111d")
        
        self.pixel_size = pixel_size
        self.num_cols = len(BASE_ART[0])
        self.num_rows = len(BASE_ART)
        
        # Dimensions
        self.cloud_height = 110
        self.canvas_w = (self.num_cols * self.pixel_size) + 40
        self.canvas_h = (self.num_rows * self.pixel_size) + self.cloud_height + 20
        self.girl_y_offset = self.cloud_height + 10
        
        # Animation State
        self.frame_count = 0
        self.start_time = time.time()
        self.speech_active = initial_greeting
        self.speech_text = "HELLO! ♥"
        self.speech_start_time = time.time() if initial_greeting else 0.0
        self.speech_scale = 1.0 if initial_greeting else 0.0
        self.expression = "HAPPY" if initial_greeting else "NORMAL"
        self.last_girl_shift_y = 0.0
        
        self.build_ui()
        self.init_grid_cells()
        
        # Start animation loop (~30 fps)
        self.root.after(30, self.update_animation)
        
    def build_ui(self):
        tk = self.tk
        
        # Header title
        header_frame = tk.Frame(self.root, bg="#14111d")
        header_frame.pack(fill="x", pady=(10, 0))
        
        title = tk.Label(
            header_frame,
            text="✨ ✿ Princess Mia ✿ ✨",
            font=("DejaVu Sans", 14, "bold"),
            fg="#ff69b4",
            bg="#14111d"
        )
        title.pack()
        
        subtitle = tk.Label(
            header_frame,
            text="Your Interactive Pixel Companion",
            font=("DejaVu Sans", 9),
            fg="#b09fc0",
            bg="#14111d"
        )
        subtitle.pack()
        
        # Pixel Art Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=self.canvas_w,
            height=self.canvas_h,
            bg="#14111d",
            highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=5)
        
        # Interactive Control Panel
        panel = tk.Frame(self.root, bg="#1a1626", padx=14, pady=10)
        panel.pack(fill="x", padx=16, pady=(0, 10))
        
        # Quick action greeting buttons
        btn_frame = tk.Frame(panel, bg="#1a1626")
        btn_frame.pack(fill="x", pady=(0, 8))
        
        btn_style = {
            "bg": "#2c1e38",
            "fg": "#ffb6d9",
            "activebackground": "#ff69b4",
            "activeforeground": "#ffffff",
            "relief": "flat",
            "font": ("DejaVu Sans", 9, "bold"),
            "padx": 10,
            "pady": 4,
            "cursor": "hand2"
        }
        
        say_hello_btn = tk.Button(
            btn_frame,
            text="💬 Say 'Hello!'",
            command=lambda: self.trigger_speech("HELLO! ♥"),
            **btn_style
        )
        say_hello_btn.pack(side="left", padx=4)
        
        wave_btn = tk.Button(
            btn_frame,
            text="👋 Wave",
            command=lambda: self.trigger_speech("HI THERE! ✨"),
            **btn_style
        )
        wave_btn.pack(side="left", padx=4)
        
        love_btn = tk.Button(
            btn_frame,
            text="💖 Love You",
            command=lambda: self.trigger_speech("AWH, LOVE! ♥"),
            **btn_style
        )
        love_btn.pack(side="left", padx=4)
        
        # Text input row
        input_frame = tk.Frame(panel, bg="#1a1626")
        input_frame.pack(fill="x")
        
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            input_frame,
            textvariable=self.entry_var,
            font=("DejaVu Sans", 11),
            bg="#2a233b",
            fg="#ffffff",
            insertbackground="#ff69b4",
            relief="flat",
            bd=6
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self.on_send())
        
        send_btn = tk.Button(
            input_frame,
            text="Send 🌸",
            command=self.on_send,
            bg="#d81b60",
            fg="#ffffff",
            activebackground="#ff4081",
            activeforeground="#ffffff",
            relief="flat",
            font=("DejaVu Sans", 10, "bold"),
            padx=14,
            pady=4,
            cursor="hand2"
        )
        send_btn.pack(side="right")
        
        # Footer hints
        footer = tk.Label(
            self.root,
            text="Type 'hello' and hit Enter!  •  Press Esc to close",
            font=("DejaVu Sans", 8),
            fg="#7c6b90",
            bg="#14111d",
            pady=6
        )
        footer.pack()
        
        # Hotkeys
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<q>", lambda e: self.root.destroy() if not self.entry.focus_get() == self.entry else None)
        
        # Center window on screen
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2) - 20
        self.root.geometry(f"+{x}+{y}")

    def init_grid_cells(self):
        """Creates the pixel rectangle items on the canvas once."""
        self.cell_items = {}
        start_x = 20
        start_y = self.girl_y_offset
        
        for r_idx in range(self.num_rows):
            for c_idx in range(self.num_cols):
                x1 = start_x + (c_idx * self.pixel_size)
                y1 = start_y + (r_idx * self.pixel_size)
                x2 = x1 + self.pixel_size
                y2 = y1 + self.pixel_size
                item = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill="",
                    outline="",
                    tags=("girl", "pixel")
                )
                self.cell_items[(r_idx, c_idx)] = item
                
        # Draw initial character frame
        self.render_girl_frame(build_frame("OPEN", 0))

    def render_girl_frame(self, grid_lines):
        """Updates cell fills for characters that changed."""
        for r_idx, line in enumerate(grid_lines):
            for c_idx, char in enumerate(line):
                color = PALETTE.get(char)
                hex_col = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}" if color else ""
                item = self.cell_items.get((r_idx, c_idx))
                if item:
                    current_fill = self.canvas.itemcget(item, "fill")
                    if current_fill != hex_col:
                        self.canvas.itemconfig(item, fill=hex_col)

    def trigger_speech(self, text):
        """Triggers the animated speech cloud reaction."""
        self.speech_active = True
        self.speech_text = text
        self.speech_start_time = time.time()
        self.speech_scale = 0.05
        self.expression = "HAPPY"

    def on_send(self):
        user_text = self.entry_var.get().strip()
        self.entry_var.set("")
        if not user_text:
            return
            
        lower_txt = user_text.lower()
        if "hello" in lower_txt or "hi" in lower_txt or "hey" in lower_txt:
            self.trigger_speech("HELLO! ♥")
        elif "how are you" in lower_txt:
            self.trigger_speech("FEELING GREAT! ✨")
        elif "name" in lower_txt or "who are you" in lower_txt:
            self.trigger_speech("I'M MIA! 🌸")
        elif "love" in lower_txt or "cute" in lower_txt or "pretty" in lower_txt:
            self.trigger_speech("THANK YOU! ♥")
        elif "bye" in lower_txt:
            self.trigger_speech("GOODBYE! 👋💖")
        else:
            self.trigger_speech("HELLO THERE! 💖")

    def draw_speech_cloud(self, cx, cy, scale, t):
        """Draws the animated fluffy speech cloud and bouncing letters."""
        self.canvas.delete("cloud")
        if scale <= 0.02:
            return
            
        # Cloud puff circles (relative dx, dy, radius)
        puffs = [
            (-65, 8, 32), (-45, -16, 36), (-12, -22, 42),
            (25, -20, 38), (62, -6, 34), (68, 14, 28),
            (35, 24, 34), (-5, 26, 38), (-40, 22, 34)
        ]
        
        outline_col = "#e88bb7"
        fill_col = "#ffffff"
        
        # 1. Outer outline puffs
        for dx, dy, r in puffs:
            r_s = r * scale
            x, y = cx + dx * scale, cy + dy * scale
            self.canvas.create_oval(
                x - r_s - 3, y - r_s - 3, x + r_s + 3, y + r_s + 3,
                fill=outline_col, outline="", tags="cloud"
            )
            
        # 2. Cloud tail puffs pointing to her head
        tail_puffs = [
            (-20 * scale, 40 * scale, 10 * scale),
            (-32 * scale, 58 * scale, 6 * scale)
        ]
        for tx, ty, tr in tail_puffs:
            self.canvas.create_oval(
                cx + tx - tr - 2, cy + ty - tr - 2, cx + tx + tr + 2, cy + ty + tr + 2,
                fill=outline_col, outline="", tags="cloud"
            )
            self.canvas.create_oval(
                cx + tx - tr, cy + ty - tr, cx + tx + tr, cy + ty + tr,
                fill=fill_col, outline="", tags="cloud"
            )
            
        # 3. Inner fill puffs
        for dx, dy, r in puffs:
            r_s = r * scale
            x, y = cx + dx * scale, cy + dy * scale
            self.canvas.create_oval(
                x - r_s, y - r_s, x + r_s, y + r_s,
                fill=fill_col, outline="", tags="cloud"
            )
            
        # 4. Animated wave text inside cloud
        if scale > 0.6:
            text = self.speech_text
            text_len = len(text)
            spacing = 16 * scale
            total_w = text_len * spacing
            start_x = cx - (total_w / 2.0) + (spacing / 2.0)
            
            letter_colors = ["#ff007f", "#e91e63", "#d81b60", "#ff4081", "#c2185b", "#9c27b0"]
            font_size = max(8, int(15 * scale))
            
            for idx, ch in enumerate(text):
                # Letter wave bounce
                wave_offset = math.sin(t * 6.0 + idx * 0.7) * (4.0 * scale)
                lx = start_x + (idx * spacing)
                ly = cy + wave_offset + (2 * scale)
                col = letter_colors[(int(t * 4) + idx) % len(letter_colors)]
                
                self.canvas.create_text(
                    lx, ly,
                    text=ch,
                    font=("DejaVu Sans", font_size, "bold"),
                    fill=col,
                    tags="cloud"
                )
                
            # Floating sparkles around cloud
            sparkle_angles = [0.2, 1.8, 3.4, 4.9]
            sparkle_chars = ["✦", "✧", "♥", "★"]
            for s_idx, angle in enumerate(sparkle_angles):
                s_dist = (88 + math.sin(t * 4 + s_idx) * 8) * scale
                sx = cx + math.cos(angle + t * 0.8) * s_dist
                sy = cy + math.sin(angle + t * 0.8) * s_dist * 0.6
                s_col = letter_colors[(s_idx + int(t * 3)) % len(letter_colors)]
                self.canvas.create_text(
                    sx, sy,
                    text=sparkle_chars[s_idx % len(sparkle_chars)],
                    font=("DejaVu Sans", max(7, int(11 * scale))),
                    fill=s_col,
                    tags="cloud"
                )

    def update_animation(self):
        """Main 30 FPS animation update cycle."""
        self.frame_count += 1
        now = time.time()
        t = now - self.start_time
        
        # 1. Speech cloud state machine & scale interpolation
        if self.speech_active:
            speech_elapsed = now - self.speech_start_time
            if speech_elapsed < 4.5:
                # Pop up with elastic bounce
                target_scale = 1.0
                self.speech_scale += (target_scale - self.speech_scale) * 0.35
            elif speech_elapsed < 5.2:
                # Fade / shrink out
                self.speech_scale *= 0.72
            else:
                self.speech_active = False
                self.speech_scale = 0.0
                self.expression = "NORMAL"
                self.canvas.delete("cloud")
        else:
            self.speech_scale = 0.0
            
        # 2. Girl face expression state machine
        if self.expression == "HAPPY":
            face = "HAPPY"
        else:
            # Idle blinking (blink every 3.5 seconds)
            cycle = self.frame_count % 90
            if cycle == 80:
                face = "HALF"
            elif cycle in (81, 82, 83):
                face = "BLINK"
            elif cycle == 84:
                face = "HALF"
            else:
                face = "OPEN"
                
        # 3. Sparkle frame cycle
        sparkle_idx = (self.frame_count // 5) % len(SPARKLE_FRAMES)
        grid = build_frame(face, sparkle_idx)
        self.render_girl_frame(grid)
        
        # 4. Gentle idle breathing / floating movement
        breath_y = math.sin(t * 2.2) * 2.0
        dy = breath_y - self.last_girl_shift_y
        self.canvas.move("girl", 0, dy)
        self.last_girl_shift_y = breath_y
        
        # 5. Render speech cloud if active
        if self.speech_active and self.speech_scale > 0.02:
            cloud_bob = math.sin(t * 3.5) * 3.5
            cloud_cx = (self.canvas_w / 2.0) + 10
            cloud_cy = 58 + cloud_bob
            self.draw_speech_cloud(cloud_cx, cloud_cy, self.speech_scale, t)
            
        self.root.after(33, self.update_animation)
        
    def run(self):
        self.root.mainloop()

# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    
    # Check flags
    if "--help" in args or "-h" in args:
        print("""
✨ ✿ Princess Mia ✿ ✨ — Interactive Pixel Art Companion

Usage:
  python3 pixel_girl.py           Launch desktop animated GUI popup
  python3 pixel_girl.py --popup   Launch desktop animated GUI popup
  python3 pixel_girl.py --terminal Launch interactive animated terminal mode
  python3 pixel_girl.py --static   Print one-time static terminal ANSI art
  python3 pixel_girl.py --say "hi" Start with greeting cloud active
""")
        return
        
    if "--static" in args:
        banner = "\n\033[1;38;2;255;105;180m  ✨ ✿ Princess Mia ✿ ✨ \033[0m\n"
        print(banner)
        print(render_ansi_grid(BASE_ART))
        print("\n\033[38;2;255;160;200m     ♥ Pixel Art for Terminal ♥\033[0m\n")
        return

    initial_say = ("--say" in args) or any("hello" in a.lower() for a in args)

    if "--terminal" in args or "-t" in args or "--cli" in args:
        run_terminal_app(initial_greeting=initial_say)
        return

    # Check for GUI display
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if has_display:
        try:
            app = PixelGirlPopup(pixel_size=10, initial_greeting=initial_say)
            app.run()
            return
        except Exception as e:
            print(f"Notice: Could not launch GUI ({e}). Falling back to Terminal mode...\n")
            run_terminal_app(initial_greeting=initial_say)
    else:
        run_terminal_app(initial_greeting=initial_say)

if __name__ == "__main__":
    main()
