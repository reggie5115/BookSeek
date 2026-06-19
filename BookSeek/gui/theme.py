"""
theme.py  [UI/챗봇: 팀원 C] — 색상, 폰트, 공용 위젯 스타일.
"""

import tkinter as tk
from tkinter import font as tkfont


class Theme:
    # Palette ---------------------------------------------------------- #
    BG = "#F5F1E8"            # warm paper background
    SURFACE = "#FFFFFF"       # cards / panels
    SURFACE_ALT = "#FAF6EC"   # subtle alternate surface
    SIDEBAR = "#2C2A28"       # deep charcoal-brown sidebar
    SIDEBAR_HOVER = "#3D3A36"
    SIDEBAR_ACTIVE = "#8C6A4A"

    PRIMARY = "#8C6A4A"       # leather brown accent
    PRIMARY_DARK = "#6E5238"
    PRIMARY_LIGHT = "#B7916B"
    ACCENT = "#3E7C6A"        # muted green for positive actions

    TEXT = "#2C2A28"          # near-black warm
    TEXT_MUTED = "#7A746B"
    TEXT_ON_DARK = "#F5F1E8"
    TEXT_ON_PRIMARY = "#FFFFFF"

    BORDER = "#E3DCCD"
    DANGER = "#B5524A"
    STAR = "#D9A441"

    # Fonts ------------------------------------------------------------ #
    @staticmethod
    def _pick_family(tk_root, candidates, fallback="TkDefaultFont"):
        """Return the first installed font family from `candidates`."""
        try:
            available = set(tkfont.families(tk_root))
        except Exception:
            available = set()
        for fam in candidates:
            if fam in available:
                return fam
        return fallback

    @staticmethod
    def fonts(tk_root=None):
        """
        Build the app's font set, choosing a clean Korean-capable font family
        based on what's installed. Pass the Tk root so we can query the list
        of available families; if omitted we fall back to common names.
        """
        # Clean sans-serif families that include Hangul glyphs, in order of
        # preference per platform. Tk falls back gracefully if a name is wrong,
        # but we try to pick a known-good installed one first.
        sans_candidates = [
            "Malgun Gothic",        # Windows (맑은 고딕)
            "Apple SD Gothic Neo",  # macOS
            "AppleGothic",          # older macOS
            "Noto Sans CJK KR",     # Linux (Noto)
            "Noto Sans KR",
            "NanumGothic",          # Linux (나눔고딕)
            "Nanum Gothic",
            "Source Han Sans KR",
            "Helvetica",            # last-resort latin fallback
        ]
        # A slightly softer family for big headings if available, else reuse sans.
        serif_candidates = [
            "Malgun Gothic",
            "Apple SD Gothic Neo",
            "Noto Serif CJK KR",
            "Noto Serif KR",
            "NanumMyeongjo",
            "Nanum Myeongjo",
            "Georgia",
        ]

        if tk_root is not None:
            sans = Theme._pick_family(tk_root, sans_candidates)
            heading = Theme._pick_family(tk_root, serif_candidates, fallback=sans)
        else:
            sans = sans_candidates[0]
            heading = serif_candidates[0]

        return {
            "title": tkfont.Font(family=heading, size=22, weight="bold"),
            "h1": tkfont.Font(family=heading, size=17, weight="bold"),
            "h2": tkfont.Font(family=sans, size=13, weight="bold"),
            "body": tkfont.Font(family=sans, size=11),
            "body_bold": tkfont.Font(family=sans, size=11, weight="bold"),
            "small": tkfont.Font(family=sans, size=10),
            "tiny": tkfont.Font(family=sans, size=9),
            "chat": tkfont.Font(family=sans, size=11),
            "sidebar": tkfont.Font(family=sans, size=12, weight="bold"),
        }


class HoverButton(tk.Label):
    """A flat, rounded-feel button built on a Label for full color control."""

    def __init__(self, master, text, command=None,
                 bg=Theme.PRIMARY, fg=Theme.TEXT_ON_PRIMARY,
                 hover_bg=Theme.PRIMARY_DARK, font=None, padx=16, pady=8,
                 **kw):
        super().__init__(master, text=text, bg=bg, fg=fg, font=font,
                         padx=padx, pady=pady, cursor="hand2", **kw)
        self._bg = bg
        self._hover_bg = hover_bg
        self._command = command
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self.config(bg=self._hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))

    def _on_click(self, _event):
        if self._command:
            self._command()

    def set_command(self, command):
        self._command = command

    def set_colors(self, bg, hover_bg):
        self._bg = bg
        self._hover_bg = hover_bg
        self.config(bg=bg)


def make_scrollable(parent, bg=Theme.BG):
    """
    Create a vertically scrollable frame. Returns (outer_frame, inner_frame).
    Put content into inner_frame; outer_frame is what you pack/grid.
    """
    outer = tk.Frame(parent, bg=bg)
    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=bg)

    inner.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    window = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _resize(event):
        canvas.itemconfig(window, width=event.width)
    canvas.bind("<Configure>", _resize)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Mousewheel support (cross-platform).
    def _on_mousewheel(event):
        if event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")
        else:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_wheel(_):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

    def _unbind_wheel(_):
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    inner.bind("<Enter>", _bind_wheel)
    inner.bind("<Leave>", _unbind_wheel)

    return outer, inner
