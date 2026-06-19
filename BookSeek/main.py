#!/usr/bin/env python3
"""
BookSeek — 도서 추천 플랫폼 (실행 파일)

읽은 책에 0~10점을 매기면, 벡터 유사도로 좋아할 만한 책을 추천하고
AI 사서가 소개해준다. 책 정보는 오픈 라이브러리에서 가져온다.

실행:  python main.py
(처음 실행 시 인터넷에서 책을 받아온다. 표준 라이브러리만 필요.)

[팀 분업]
  팀원 A 데이터        : core/database.py, core/openlibrary.py
  팀원 B 추천 알고리즘 : core/recommender.py
  팀원 C UI/챗봇       : gui/*, core/chatbot.py
  공통                 : core/app_controller.py, main.py
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

# Make sure local packages import correctly regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow  # noqa: E402


def main():
    root = tk.Tk()

    # Improve scaling / appearance on high-DPI displays where supported.
    try:
        root.tk.call("tk", "scaling", 1.2)
    except tk.TclError:
        pass

    try:
        app = MainWindow(root)
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror(
            "Startup error",
            f"BookSeek failed to start:\n\n{exc}")
        raise

    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
