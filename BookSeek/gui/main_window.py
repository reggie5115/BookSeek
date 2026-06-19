"""
main_window.py  [UI/챗봇: 팀원 C]
Tkinter 메인 화면. 사이드바로 4개 화면을 전환한다.
- 서재: 책 검색 / 평점 매기기
- 내 평점: 매긴 점수 보기
- 추천: 추천 받기 + AI 사서 소개
- 책 추가: 없는 책을 웹에서 찾아 추가
인터넷/계산 작업은 백그라운드 스레드로 처리해 화면이 안 멈추게 했다.
"""

import threading
import queue
import tkinter as tk
from tkinter import messagebox
from typing import List, Dict, Any, Optional

from core.app_controller import AppController
from gui.theme import Theme, HoverButton, make_scrollable
from gui.widgets import BookCard, StarRating


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.controller = AppController()
        self.fonts = Theme.fonts(self.root)

        # A queue lets background threads ask the UI thread to run callbacks.
        self._ui_queue: "queue.Queue" = queue.Queue()
        self.root.after(80, self._drain_queue)

        self.current_view = None
        self.nav_buttons: Dict[str, HoverButton] = {}

        self._setup_window()
        self._build_layout()

        # Decide whether we need to populate the library on first launch.
        if self.controller.needs_seeding():
            self._show_view("library")
            self.root.after(300, self._seed_first_run)
        else:
            self._show_view("library")

    # ------------------------------------------------------------------ #
    # Window chrome
    # ------------------------------------------------------------------ #
    def _setup_window(self):
        self.root.title("BookSeek — 도서 추천")
        self.root.configure(bg=Theme.BG)
        self.root.geometry("1080x720")
        self.root.minsize(940, 620)

    def _build_layout(self):
        # Sidebar -------------------------------------------------------#
        self.sidebar = tk.Frame(self.root, bg=Theme.SIDEBAR, width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=Theme.SIDEBAR)
        brand.pack(fill="x", pady=(26, 30), padx=20)
        tk.Label(brand, text="\U0001F4D6", bg=Theme.SIDEBAR,
                 fg=Theme.TEXT_ON_DARK, font=("Helvetica", 26)).pack(anchor="w")
        tk.Label(brand, text="BookSeek", bg=Theme.SIDEBAR,
                 fg=Theme.TEXT_ON_DARK, font=self.fonts["title"]).pack(
            anchor="w")
        tk.Label(brand, text="나만의 도서 동반자", bg=Theme.SIDEBAR,
                 fg=Theme.PRIMARY_LIGHT, font=self.fonts["tiny"]).pack(
            anchor="w")

        nav_items = [
            ("library", "\U0001F4DA  서재"),
            ("ratings", "\u2B50  내 평점"),
            ("recommend", "\u2728  추천"),
            ("add", "\u2795  책 추가"),
        ]
        for key, label in nav_items:
            btn = HoverButton(
                self.sidebar, text=label,
                command=lambda k=key: self._show_view(k),
                bg=Theme.SIDEBAR, hover_bg=Theme.SIDEBAR_HOVER,
                fg=Theme.TEXT_ON_DARK, font=self.fonts["sidebar"],
                padx=20, pady=12, anchor="w",
            )
            btn.config(anchor="w")
            btn.pack(fill="x")
            self.nav_buttons[key] = btn

        # Status area at the bottom of the sidebar.
        self.status_frame = tk.Frame(self.sidebar, bg=Theme.SIDEBAR)
        self.status_frame.pack(side="bottom", fill="x", padx=20, pady=18)
        self.status_label = tk.Label(
            self.status_frame, text="", bg=Theme.SIDEBAR,
            fg=Theme.PRIMARY_LIGHT, font=self.fonts["tiny"],
            anchor="w", justify="left", wraplength=170,
        )
        self.status_label.pack(anchor="w")
        self._update_status()

        # Main content area --------------------------------------------#
        self.content = tk.Frame(self.root, bg=Theme.BG)
        self.content.pack(side="left", fill="both", expand=True)

    def _update_status(self):
        mode = ("AI: Claude 연결됨" if self.controller.chatbot_mode == "online"
                else "AI: 오프라인 사서")
        self.status_label.config(
            text=f"서재에 {self.controller.library_size()}권\n{mode}"
        )

    # ------------------------------------------------------------------ #
    # Threading helpers
    # ------------------------------------------------------------------ #
    def _run_bg(self, fn, on_done=None, on_error=None):
        def worker():
            try:
                result = fn()
                if on_done:
                    self._ui_queue.put(lambda: on_done(result))
            except Exception as exc:  # noqa: BLE001
                if on_error:
                    self._ui_queue.put(lambda: on_error(exc))
                else:
                    self._ui_queue.put(
                        lambda: messagebox.showerror("Error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _drain_queue(self):
        try:
            while True:
                cb = self._ui_queue.get_nowait()
                cb()
        except queue.Empty:
            pass
        self.root.after(80, self._drain_queue)

    # ------------------------------------------------------------------ #
    # View switching
    # ------------------------------------------------------------------ #
    def _clear_content(self):
        for child in self.content.winfo_children():
            child.destroy()

    def _show_view(self, key: str):
        self.current_view = key
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.set_colors(Theme.SIDEBAR_ACTIVE, Theme.SIDEBAR_ACTIVE)
            else:
                btn.set_colors(Theme.SIDEBAR, Theme.SIDEBAR_HOVER)

        self._clear_content()
        if key == "library":
            self._build_library_view()
        elif key == "ratings":
            self._build_ratings_view()
        elif key == "recommend":
            self._build_recommend_view()
        elif key == "add":
            self._build_add_view()
        self._update_status()

    def _view_header(self, title: str, subtitle: str) -> tk.Frame:
        header = tk.Frame(self.content, bg=Theme.BG)
        header.pack(fill="x", padx=32, pady=(28, 8))
        tk.Label(header, text=title, bg=Theme.BG, fg=Theme.TEXT,
                 font=self.fonts["title"]).pack(anchor="w")
        tk.Label(header, text=subtitle, bg=Theme.BG, fg=Theme.TEXT_MUTED,
                 font=self.fonts["body"]).pack(anchor="w", pady=(2, 0))
        return header

    # ================================================================== #
    # LIBRARY VIEW
    # ================================================================== #
    def _build_library_view(self):
        self._view_header("서재",
                          "장서를 둘러보고 읽은 책에 평점을 매겨보세요.")

        bar = tk.Frame(self.content, bg=Theme.BG)
        bar.pack(fill="x", padx=32, pady=(8, 12))

        self.lib_search_var = tk.StringVar()
        entry = tk.Entry(bar, textvariable=self.lib_search_var,
                         font=self.fonts["body"], bg=Theme.SURFACE,
                         fg=Theme.TEXT, relief="flat",
                         highlightthickness=1,
                         highlightbackground=Theme.BORDER,
                         highlightcolor=Theme.PRIMARY)
        entry.pack(side="left", fill="x", expand=True, ipady=8, ipadx=8)
        entry.bind("<Return>", lambda e: self._do_library_search())

        HoverButton(bar, text="검색", command=self._do_library_search,
                    font=self.fonts["body"], padx=20, pady=9).pack(
            side="left", padx=(10, 0))

        # Scrollable results region.
        self.lib_outer, self.lib_inner = make_scrollable(self.content)
        self.lib_outer.pack(fill="both", expand=True, padx=24, pady=(4, 20))

        self._do_library_search()

    def _do_library_search(self):
        query = self.lib_search_var.get() if hasattr(self, "lib_search_var") else ""
        for c in self.lib_inner.winfo_children():
            c.destroy()
        loading = tk.Label(self.lib_inner, text="불러오는 중…",
                           bg=Theme.BG, fg=Theme.TEXT_MUTED,
                           font=self.fonts["body"])
        loading.pack(pady=20)

        def work():
            return self.controller.search_local(query)

        def done(books):
            loading.destroy()
            self._render_book_list(self.lib_inner, books, mode="library",
                                   on_action=self._open_rating_dialog,
                                   empty_msg="검색 결과가 없습니다.")

        self._run_bg(work, on_done=done)

    # ================================================================== #
    # RATINGS VIEW
    # ================================================================== #
    def _build_ratings_view(self):
        self._view_header("내 평점",
                          "평점을 매긴 책들입니다. 이 평점이 추천의 바탕이 됩니다.")

        bar = tk.Frame(self.content, bg=Theme.BG)
        bar.pack(fill="x", padx=32, pady=(4, 8))
        HoverButton(bar, text="평점 전체 삭제",
                    command=self._clear_all_ratings,
                    bg=Theme.DANGER, hover_bg="#9B453E",
                    font=self.fonts["small"], padx=14, pady=7).pack(
            side="right")

        self.rate_outer, self.rate_inner = make_scrollable(self.content)
        self.rate_outer.pack(fill="both", expand=True, padx=24, pady=(4, 20))
        self._refresh_ratings_list()

    def _refresh_ratings_list(self):
        for c in self.rate_inner.winfo_children():
            c.destroy()
        rated = self.controller.rated_books()
        if not rated:
            self._empty_state(
                self.rate_inner,
                "아직 평점을 매긴 책이 없습니다.",
                "서재에서 읽은 책의 “평가” 버튼을 눌러보세요.")
            return
        for b in rated:
            self._rated_row(self.rate_inner, b)

    def _rated_row(self, parent, book):
        card = tk.Frame(parent, bg=Theme.SURFACE,
                        highlightbackground=Theme.BORDER, highlightthickness=1)
        card.pack(fill="x", pady=6, padx=4)
        inner = tk.Frame(card, bg=Theme.SURFACE)
        inner.pack(fill="x", padx=14, pady=12)

        left = tk.Frame(inner, bg=Theme.SURFACE)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=book["title"], bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=self.fonts["body_bold"], anchor="w",
                 wraplength=420, justify="left").pack(anchor="w")
        tk.Label(left, text=book.get("author") or "작자 미상",
                 bg=Theme.SURFACE, fg=Theme.TEXT_MUTED,
                 font=self.fonts["small"], anchor="w").pack(anchor="w")

        score = int(book.get("user_score", 0))
        stars = "\u2605" * (score // 2) + "\u2606" * (5 - score // 2)
        score_box = tk.Frame(inner, bg=Theme.SURFACE)
        score_box.pack(side="left", padx=16)
        tk.Label(score_box, text=f"{score}/10", bg=Theme.SURFACE,
                 fg=Theme.PRIMARY_DARK, font=self.fonts["h2"]).pack()
        tk.Label(score_box, text=stars, bg=Theme.SURFACE, fg=Theme.STAR,
                 font=self.fonts["small"]).pack()

        HoverButton(inner, text="수정",
                    command=lambda b=book: self._open_rating_dialog(b),
                    bg=Theme.PRIMARY, hover_bg=Theme.PRIMARY_DARK,
                    font=self.fonts["tiny"], padx=12, pady=5).pack(
            side="left", padx=(0, 6))
        HoverButton(inner, text="삭제",
                    command=lambda b=book: self._remove_rating(b),
                    bg=Theme.SURFACE_ALT, hover_bg="#EFE7D6",
                    fg=Theme.DANGER,
                    font=self.fonts["tiny"], padx=12, pady=5).pack(side="left")

    def _remove_rating(self, book):
        self.controller.unrate_book(book["id"])
        self._refresh_ratings_list()
        self._update_status()

    def _clear_all_ratings(self):
        if messagebox.askyesno("평점 삭제",
                               "모든 평점을 삭제할까요? 되돌릴 수 없습니다."):
            self.controller.clear_ratings()
            self._refresh_ratings_list()

    # ================================================================== #
    # RECOMMEND VIEW  (+ chatbot)
    # ================================================================== #
    def _build_recommend_view(self):
        self._view_header(
            "추천",
            "당신의 평점을 바탕으로 한 맞춤 추천을 AI 사서가 소개합니다.")

        bar = tk.Frame(self.content, bg=Theme.BG)
        bar.pack(fill="x", padx=32, pady=(4, 10))
        HoverButton(bar, text="\u2728  추천 받기",
                    command=self._generate_recommendations,
                    bg=Theme.ACCENT, hover_bg="#336657",
                    font=self.fonts["body_bold"], padx=20, pady=10).pack(
            side="left")

        # Split: left = chatbot, right = recommendation cards.
        split = tk.Frame(self.content, bg=Theme.BG)
        split.pack(fill="both", expand=True, padx=24, pady=(6, 18))

        # --- Chatbot panel (left) ------------------------------------- #
        chat_panel = tk.Frame(split, bg=Theme.SURFACE,
                              highlightbackground=Theme.BORDER,
                              highlightthickness=1, width=420)
        chat_panel.pack(side="left", fill="both", padx=(0, 12))
        chat_panel.pack_propagate(False)

        chat_head = tk.Frame(chat_panel, bg=Theme.PRIMARY)
        chat_head.pack(fill="x")
        tk.Label(chat_head, text="\U0001F916  AI 사서", bg=Theme.PRIMARY,
                 fg="white", font=self.fonts["h2"], pady=12, padx=14).pack(
            anchor="w")

        self.chat_log = tk.Text(
            chat_panel, bg=Theme.SURFACE, fg=Theme.TEXT,
            font=self.fonts["chat"], wrap="word", bd=0,
            highlightthickness=0, padx=14, pady=14, state="disabled",
            spacing1=2, spacing3=8,
        )
        self.chat_log.pack(fill="both", expand=True)
        self.chat_log.tag_configure("bot", foreground=Theme.TEXT,
                                    lmargin1=4, lmargin2=4)
        self.chat_log.tag_configure("user", foreground=Theme.PRIMARY_DARK,
                                    font=self.fonts["body_bold"],
                                    lmargin1=4, lmargin2=4)
        self.chat_log.tag_configure("system", foreground=Theme.TEXT_MUTED,
                                    font=self.fonts["small"])

        chat_input_row = tk.Frame(chat_panel, bg=Theme.SURFACE_ALT)
        chat_input_row.pack(fill="x")
        self.chat_entry = tk.Entry(
            chat_input_row, font=self.fonts["body"], bg=Theme.SURFACE,
            fg=Theme.TEXT, relief="flat", highlightthickness=1,
            highlightbackground=Theme.BORDER, highlightcolor=Theme.PRIMARY)
        self.chat_entry.pack(side="left", fill="x", expand=True,
                             padx=(10, 6), pady=10, ipady=7, ipadx=6)
        self.chat_entry.bind("<Return>", lambda e: self._send_chat())
        HoverButton(chat_input_row, text="전송", command=self._send_chat,
                    font=self.fonts["small"], padx=16, pady=8).pack(
            side="left", padx=(0, 10), pady=10)

        self._chat_system("“추천 받기”를 누르면 당신을 위해 고른 책들을 소개해 드릴게요.")

        # --- Recommendation cards (right) ----------------------------- #
        self.rec_outer, self.rec_inner = make_scrollable(split)
        self.rec_outer.pack(side="left", fill="both", expand=True)
        self._empty_state(
            self.rec_inner,
            "아직 추천이 없습니다.",
            "책 몇 권에 평점을 매긴 뒤 추천 받기를 눌러주세요.")

    def _chat_system(self, text):
        self.chat_log.config(state="normal")
        self.chat_log.insert("end", text + "\n\n", "system")
        self.chat_log.config(state="disabled")
        self.chat_log.see("end")

    def _chat_bot(self, text):
        self.chat_log.config(state="normal")
        self.chat_log.insert("end", "사서\n", "user")
        self.chat_log.insert("end", text + "\n\n", "bot")
        self.chat_log.config(state="disabled")
        self.chat_log.see("end")

    def _chat_user(self, text):
        self.chat_log.config(state="normal")
        self.chat_log.insert("end", "나\n", "user")
        self.chat_log.insert("end", text + "\n\n", "bot")
        self.chat_log.config(state="disabled")
        self.chat_log.see("end")

    def _generate_recommendations(self):
        rated = self.controller.rated_books()
        if not rated:
            messagebox.showinfo(
                "먼저 평점을 매겨주세요",
                "서재에서 읽은 책 한두 권에 평점을 매긴 뒤 다시 와주세요.")
            return

        for c in self.rec_inner.winfo_children():
            c.destroy()
        tk.Label(self.rec_inner, text="책을 찾고 있습니다…",
                 bg=Theme.BG, fg=Theme.TEXT_MUTED,
                 font=self.fonts["body"]).pack(pady=20)
        self._chat_system("Thinking about what you'd enjoy\u2026")

        def work():
            recs = self.controller.get_recommendations(top_n=8)
            intro = self.controller.chatbot_introduce() if recs else ""
            return recs, intro

        def done(result):
            recs, intro = result
            for c in self.rec_inner.winfo_children():
                c.destroy()
            if not recs:
                self._empty_state(
                    self.rec_inner, "추천할 후보가 없습니다.",
                    "서재가 너무 작을 수 있어요 — 책을 더 추가해 보세요.")
                self._chat_bot("아직 추천할 책이 충분하지 않아요. “책 추가”에서 몇 권 더 넣어보세요.")
                return
            self._render_book_list(self.rec_inner, recs, mode="recommend")
            if intro:
                self._chat_bot(intro)

        self._run_bg(work, on_done=done)

    def _send_chat(self):
        text = self.chat_entry.get().strip()
        if not text:
            return
        self.chat_entry.delete(0, "end")
        self._chat_user(text)

        if not self.controller.last_recommendations:
            self._chat_bot("먼저 추천을 받으면 그 책들에 대해 자세히 알려드릴게요!")
            return

        def work():
            return self.controller.chatbot_answer(text)

        def done(answer):
            self._chat_bot(answer)

        self._run_bg(work, on_done=done)

    # ================================================================== #
    # ADD-A-BOOK VIEW
    # ================================================================== #
    def _build_add_view(self):
        self._view_header(
            "책 추가",
            "서재에 없는 책인가요? 오픈 라이브러리에서 검색해 정보를 가져옵니다.")

        form = tk.Frame(self.content, bg=Theme.SURFACE,
                        highlightbackground=Theme.BORDER, highlightthickness=1)
        form.pack(fill="x", padx=32, pady=(8, 12))
        inner = tk.Frame(form, bg=Theme.SURFACE)
        inner.pack(fill="x", padx=18, pady=18)

        tk.Label(inner, text="제목", bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=self.fonts["body_bold"]).grid(row=0, column=0,
                                                    sticky="w")
        self.add_title_var = tk.StringVar()
        title_entry = tk.Entry(inner, textvariable=self.add_title_var,
                               font=self.fonts["body"], bg=Theme.SURFACE_ALT,
                               relief="flat", highlightthickness=1,
                               highlightbackground=Theme.BORDER,
                               highlightcolor=Theme.PRIMARY, width=44)
        title_entry.grid(row=1, column=0, sticky="we", ipady=7, ipadx=6,
                         pady=(2, 10))

        tk.Label(inner, text="저자 (선택)", bg=Theme.SURFACE,
                 fg=Theme.TEXT, font=self.fonts["body_bold"]).grid(
            row=2, column=0, sticky="w")
        self.add_author_var = tk.StringVar()
        tk.Entry(inner, textvariable=self.add_author_var,
                 font=self.fonts["body"], bg=Theme.SURFACE_ALT,
                 relief="flat", highlightthickness=1,
                 highlightbackground=Theme.BORDER,
                 highlightcolor=Theme.PRIMARY, width=44).grid(
            row=3, column=0, sticky="we", ipady=7, ipadx=6, pady=(2, 12))

        inner.columnconfigure(0, weight=1)

        HoverButton(inner, text="오픈 라이브러리 검색",
                    command=self._do_online_search,
                    bg=Theme.ACCENT, hover_bg="#336657",
                    font=self.fonts["body_bold"], padx=18, pady=9).grid(
            row=4, column=0, sticky="w")
        title_entry.bind("<Return>", lambda e: self._do_online_search())

        # Results region.
        self.add_outer, self.add_inner = make_scrollable(self.content)
        self.add_outer.pack(fill="both", expand=True, padx=24, pady=(6, 18))
        self._empty_state(self.add_inner,
                          "검색 결과가 여기에 표시됩니다.",
                          "위에 제목을 입력하고 검색을 눌러주세요.")

    def _do_online_search(self):
        title = self.add_title_var.get().strip()
        if not title:
            messagebox.showinfo("제목 입력", "책 제목을 입력해주세요.")
            return
        author = self.add_author_var.get().strip() or None

        for c in self.add_inner.winfo_children():
            c.destroy()
        tk.Label(self.add_inner, text="오픈 라이브러리에서 검색 중…",
                 bg=Theme.BG, fg=Theme.TEXT_MUTED,
                 font=self.fonts["body"]).pack(pady=20)

        def work():
            return self.controller.search_online_candidates(title)

        def done(results):
            for c in self.add_inner.winfo_children():
                c.destroy()
            if not results:
                self._empty_state(
                    self.add_inner, "검색 결과가 없습니다.",
                    "철자를 확인하거나 저자 없이 다시 검색해보세요.")
                return
            tk.Label(self.add_inner,
                     text="서재에 추가할 판본을 선택하세요:",
                     bg=Theme.BG, fg=Theme.TEXT_MUTED,
                     font=self.fonts["small"]).pack(anchor="w", pady=(0, 6),
                                                    padx=4)
            for r in results:
                self._online_result_row(r)

        def err(exc):
            for c in self.add_inner.winfo_children():
                c.destroy()
            self._empty_state(
                self.add_inner, "오픈 라이브러리에 연결하지 못했습니다.",
                "인터넷 연결을 확인하고 다시 시도해주세요.")

        self._run_bg(work, on_done=done, on_error=err)

    def _online_result_row(self, result):
        card = tk.Frame(self.add_inner, bg=Theme.SURFACE,
                        highlightbackground=Theme.BORDER, highlightthickness=1)
        card.pack(fill="x", pady=6, padx=4)
        inner = tk.Frame(card, bg=Theme.SURFACE)
        inner.pack(fill="x", padx=14, pady=12)

        left = tk.Frame(inner, bg=Theme.SURFACE)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=result.get("title", "제목 없음"),
                 bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=self.fonts["body_bold"], anchor="w",
                 wraplength=420, justify="left").pack(anchor="w")
        meta = result.get("author") or "작자 미상"
        if result.get("publish_year"):
            meta += f"  \u00b7  {result['publish_year']}"
        tk.Label(left, text=meta, bg=Theme.SURFACE, fg=Theme.TEXT_MUTED,
                 font=self.fonts["small"], anchor="w").pack(anchor="w")

        HoverButton(inner, text="추가 후 평가",
                    command=lambda r=result: self._add_online_book(r),
                    bg=Theme.PRIMARY, hover_bg=Theme.PRIMARY_DARK,
                    font=self.fonts["small"], padx=14, pady=7).pack(
            side="left")

    def _add_online_book(self, result):
        title = result.get("title", "")
        author = result.get("author")

        def work():
            # fetch_book does a richer lookup (description, subjects, moods).
            full = self.controller.fetch_and_add_book(title, author)
            return full

        def done(book):
            if not book:
                messagebox.showerror(
                    "추가 실패",
                    "죄송해요, 그 책의 상세 정보를 가져오지 못했습니다.")
                return
            self._update_status()
            messagebox.showinfo(
                "추가됨",
                f"“{book['title']}”을(를) 서재에 추가했습니다.")
            self._open_rating_dialog(book)

        self._run_bg(work, on_done=done)

    # ================================================================== #
    # Shared rendering helpers
    # ================================================================== #
    def _render_book_list(self, parent, books: List[Dict[str, Any]],
                          mode="library", on_action=None,
                          empty_msg="아직 아무것도 없습니다."):
        if not books:
            self._empty_state(parent, empty_msg, "")
            return
        for b in books:
            card = BookCard(parent, b, self.fonts, mode=mode,
                            on_action=on_action)
            card.pack(fill="x", pady=7, padx=4)

    def _empty_state(self, parent, title, subtitle):
        wrap = tk.Frame(parent, bg=Theme.BG)
        wrap.pack(fill="both", expand=True, pady=50)
        tk.Label(wrap, text="\U0001F4DA", bg=Theme.BG, fg=Theme.TEXT_MUTED,
                 font=("Helvetica", 40)).pack()
        tk.Label(wrap, text=title, bg=Theme.BG, fg=Theme.TEXT,
                 font=self.fonts["h2"]).pack(pady=(8, 2))
        if subtitle:
            tk.Label(wrap, text=subtitle, bg=Theme.BG, fg=Theme.TEXT_MUTED,
                     font=self.fonts["small"]).pack()

    # ------------------------------------------------------------------ #
    # Rating dialog
    # ------------------------------------------------------------------ #
    def _open_rating_dialog(self, book: Dict[str, Any]):
        dlg = tk.Toplevel(self.root)
        dlg.title("책 평가하기")
        dlg.configure(bg=Theme.SURFACE)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)

        # Center over the main window.
        self.root.update_idletasks()
        w, h = 440, 300
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        pad = tk.Frame(dlg, bg=Theme.SURFACE)
        pad.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(pad, text=book.get("title", "Untitled"), bg=Theme.SURFACE,
                 fg=Theme.TEXT, font=self.fonts["h1"], wraplength=380,
                 justify="left").pack(anchor="w")
        tk.Label(pad, text=book.get("author") or "작자 미상",
                 bg=Theme.SURFACE, fg=Theme.TEXT_MUTED,
                 font=self.fonts["body"]).pack(anchor="w", pady=(2, 16))

        tk.Label(pad, text="얼마나 재미있게 읽으셨나요? (0~10)",
                 bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=self.fonts["body_bold"]).pack(anchor="w", pady=(0, 6))

        # Pre-fill with an existing score if present.
        existing = book.get("user_score")
        rating = StarRating(pad, self.fonts,
                            initial=existing if existing is not None else 5.0)
        rating.pack(anchor="w", pady=(0, 18))

        btn_row = tk.Frame(pad, bg=Theme.SURFACE)
        btn_row.pack(fill="x")

        def save():
            self.controller.rate_book(book["id"], rating.value())
            self._update_status()
            dlg.destroy()
            # Refresh whichever list is visible.
            if self.current_view == "ratings":
                self._refresh_ratings_list()
            elif self.current_view == "library":
                self._do_library_search()

        HoverButton(btn_row, text="평점 저장", command=save,
                    bg=Theme.ACCENT, hover_bg="#336657",
                    font=self.fonts["body_bold"], padx=18, pady=9).pack(
            side="left")
        HoverButton(btn_row, text="취소", command=dlg.destroy,
                    bg=Theme.SURFACE_ALT, hover_bg="#EFE7D6",
                    fg=Theme.TEXT, font=self.fonts["body"],
                    padx=18, pady=9).pack(side="left", padx=(10, 0))

    # ------------------------------------------------------------------ #
    # First-run seeding
    # ------------------------------------------------------------------ #
    def _seed_first_run(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("서재 준비 중")
        dlg.configure(bg=Theme.SURFACE)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)
        w, h = 460, 200
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(dlg, text="\U0001F4DA  서재를 만드는 중",
                 bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=self.fonts["h1"]).pack(pady=(24, 6))
        msg = tk.Label(dlg, text="오픈 라이브러리에서 책을 가져오는 중…",
                       bg=Theme.SURFACE, fg=Theme.TEXT_MUTED,
                       font=self.fonts["body"], wraplength=400)
        msg.pack(pady=(0, 14))

        bar_bg = tk.Frame(dlg, bg=Theme.SURFACE_ALT, height=10, width=380)
        bar_bg.pack()
        bar_bg.pack_propagate(False)
        bar_fill = tk.Frame(bar_bg, bg=Theme.ACCENT, height=10, width=0)
        bar_fill.place(x=0, y=0)

        def progress(done_n, total, label):
            frac = done_n / max(total, 1)
            self._ui_queue.put(
                lambda: bar_fill.config(width=int(380 * frac)))
            self._ui_queue.put(
                lambda: msg.config(text=f"“{label}” 불러오는 중… "
                                        f"({done_n}/{total})"))

        def work():
            return self.controller.seed_library(progress_cb=progress,
                                                per_subject=60)

        def done(count):
            dlg.destroy()
            self._update_status()
            if count == 0:
                messagebox.showwarning(
                    "오프라인",
                    "오픈 라이브러리에 연결하지 못해 서재가 비어 있습니다.\n\n"
                    "인터넷 연결을 확인한 뒤 앱을 다시 실행하거나, "
                    "온라인 상태에서 “책 추가”를 이용해주세요.")
            else:
                self._do_library_search()

        def err(exc):
            dlg.destroy()
            messagebox.showwarning(
                "준비 중 문제",
                f"서재를 자동으로 만들지 못했습니다.\n{exc}\n\n"
                "온라인 상태가 되면 직접 책을 추가할 수 있어요.")

        self._run_bg(work, on_done=done, on_error=err)

    # ------------------------------------------------------------------ #
    def on_close(self):
        try:
            self.controller.close()
        finally:
            self.root.destroy()
