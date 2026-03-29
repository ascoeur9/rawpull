import threading
import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk

import config
import copier
from constants import (
    APP_TITLE,
    DEFAULT_GEOMETRY,
    FILTER_ALL,
    FILTER_JPG,
    FILTER_RAW,
    FONT_FAMILY,
    MATCH_CONTAINS,
    MATCH_EXACT,
    MIN_HEIGHT,
    MIN_WIDTH,
    SEPARATORS_PATTERN,
)
from preview import PreviewPanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 매칭 모드 / 확장자 필터 매핑 (표시명 ↔ 내부값)
_MATCH_LABELS = {"포함 매칭": MATCH_CONTAINS, "정확히 일치": MATCH_EXACT}
_MATCH_LABELS_R = {v: k for k, v in _MATCH_LABELS.items()}

_EXT_LABELS = {"RAW": FILTER_RAW, "JPG/이미지": FILTER_JPG, "전체": FILTER_ALL}
_EXT_LABELS_R = {v: k for k, v in _EXT_LABELS.items()}


class PhotoCopierApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = config.load_config()

        # CJK 폰트 설정 (일본어/한국어/중국어 지원)
        for fn in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkFixedFont"):
            try:
                tkfont.nametofont(fn).configure(family=FONT_FAMILY)
            except Exception:
                pass

        self.title(APP_TITLE)
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.geometry(self.cfg.get("window_geometry", DEFAULT_GEOMETRY))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # body 영역 확장

        # ══════════════════════════════════════════
        # row 0 ─ 폴더 설정 (전체 폭)
        # ══════════════════════════════════════════
        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        folder_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_frame, text="📂 원본 폴더", anchor="w").grid(
            row=0, column=0, sticky="w", padx=10, pady=(8, 0),
        )
        self.source_var = ctk.StringVar(value=self.cfg.get("source_folder", ""))
        ctk.CTkEntry(folder_frame, textvariable=self.source_var).grid(
            row=0, column=1, sticky="ew", padx=5, pady=(8, 0),
        )
        ctk.CTkButton(
            folder_frame, text="찾아보기", width=80, command=self._browse_source,
        ).grid(row=0, column=2, padx=(0, 10), pady=(8, 0))

        ctk.CTkLabel(folder_frame, text="📁 대상 폴더", anchor="w").grid(
            row=1, column=0, sticky="w", padx=10, pady=(4, 0),
        )
        self.dest_var = ctk.StringVar(value=self.cfg.get("destination_folder", ""))
        ctk.CTkEntry(folder_frame, textvariable=self.dest_var).grid(
            row=1, column=1, sticky="ew", padx=5, pady=(4, 0),
        )
        ctk.CTkButton(
            folder_frame, text="찾아보기", width=80, command=self._browse_dest,
        ).grid(row=1, column=2, padx=(0, 10), pady=(4, 0))

        self.subfolders_var = ctk.BooleanVar(
            value=self.cfg.get("include_subfolders", False),
        )
        ctk.CTkCheckBox(
            folder_frame, text="하위 폴더 포함", variable=self.subfolders_var,
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(4, 8))

        # ══════════════════════════════════════════
        # row 1 ─ 좌우 분할
        # ══════════════════════════════════════════
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        body.columnconfigure(0, weight=1, uniform="half")
        body.columnconfigure(1, weight=1, uniform="half")
        body.rowconfigure(0, weight=1)

        # ────────────────────────────────────────
        # 왼쪽: 입력 + 옵션(한 줄) + 검색
        # ────────────────────────────────────────
        left = ctk.CTkFrame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)  # 텍스트 입력이 늘어남

        # 라벨
        ctk.CTkLabel(left, text="🔢 파일번호 입력", anchor="w").grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 2),
        )

        # 텍스트 입력 (세로로 최대한 확장)
        self.input_text = ctk.CTkTextbox(left)
        self.input_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 4))
        self._placeholder_active = True
        self.input_text.insert("1.0", "파일번호를 입력 (줄바꿈 또는 쉼표로 구분)")
        self.input_text.configure(text_color="gray50")
        self.input_text.bind("<FocusIn>", self._on_input_focus_in)
        self.input_text.bind("<FocusOut>", self._on_input_focus_out)
        self.input_text.bind("<<Paste>>", self._override_paste)

        # 붙여넣기 / 지우기 버튼
        input_btns = ctk.CTkFrame(left, fg_color="transparent")
        input_btns.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        ctk.CTkButton(
            input_btns, text="📋 붙여넣기", width=100,
            command=self._paste_clipboard,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            input_btns, text="지우기", width=55,
            fg_color="gray40", hover_color="gray50",
            command=self._clear_input,
        ).pack(side="left")

        # 옵션: 매칭 모드 + 확장자 필터 (한 줄, 각각 1/2)
        opt_row = ctk.CTkFrame(left, fg_color="transparent")
        opt_row.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 6))
        opt_row.columnconfigure(0, weight=1, uniform="opt")
        opt_row.columnconfigure(1, weight=1, uniform="opt")

        # 매칭 모드 세그먼트
        match_wrap = ctk.CTkFrame(opt_row, fg_color="transparent")
        match_wrap.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkLabel(
            match_wrap, text="매칭", font=ctk.CTkFont(size=11),
        ).pack(anchor="w")
        saved_match = self.cfg.get("match_mode", MATCH_CONTAINS)
        self.match_seg = ctk.CTkSegmentedButton(
            match_wrap, values=list(_MATCH_LABELS.keys()),
        )
        self.match_seg.set(_MATCH_LABELS_R.get(saved_match, "포함 매칭"))
        self.match_seg.pack(fill="x", pady=(2, 0))

        # 확장자 필터 세그먼트
        ext_wrap = ctk.CTkFrame(opt_row, fg_color="transparent")
        ext_wrap.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ctk.CTkLabel(
            ext_wrap, text="확장자", font=ctk.CTkFont(size=11),
        ).pack(anchor="w")
        saved_ext = self.cfg.get("extension_filter", FILTER_RAW)
        self.ext_seg = ctk.CTkSegmentedButton(
            ext_wrap, values=list(_EXT_LABELS.keys()),
        )
        self.ext_seg.set(_EXT_LABELS_R.get(saved_ext, "RAW"))
        self.ext_seg.pack(fill="x", pady=(2, 0))

        # 검색 버튼
        self.search_btn = ctk.CTkButton(
            left, text="🔍 검색", height=36, command=self._on_search,
        )
        self.search_btn.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

        # ────────────────────────────────────────
        # 오른쪽: 미리보기 + 복사
        # ────────────────────────────────────────
        right = ctk.CTkFrame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.preview = PreviewPanel(right)
        self.preview.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 2))

        # 복사 바
        copy_bar = ctk.CTkFrame(right, fg_color="transparent")
        copy_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 8))
        copy_bar.columnconfigure(1, weight=1)

        self.copy_btn = ctk.CTkButton(
            copy_bar, text="📑 복사 실행", width=110, height=34,
            fg_color="#2d8a4e", hover_color="#236b3c",
            command=self._on_copy, state="disabled",
        )
        self.copy_btn.grid(row=0, column=0, padx=(0, 8))

        self.progress = ctk.CTkProgressBar(copy_bar, height=12)
        self.progress.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(copy_bar, text="", width=60)
        self.status_label.grid(row=0, column=2)

        # ══════════════════════════════════════════
        # row 2 ─ 로그 (전체 폭)
        # ══════════════════════════════════════════
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        log_frame.columnconfigure(0, weight=1)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 2))
        ctk.CTkLabel(
            log_header, text="로그", font=ctk.CTkFont(weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            log_header, text="지우기", width=55, height=22,
            fg_color="gray40", hover_color="gray50", command=self._clear_log,
        ).pack(side="right")

        self.log_text = ctk.CTkTextbox(log_frame, height=80, state="disabled")
        self.log_text.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

    # ── 헬퍼: 세그먼트 값 → 내부 값 ──

    def _get_match_mode(self) -> str:
        return _MATCH_LABELS.get(self.match_seg.get(), MATCH_CONTAINS)

    def _get_ext_filter(self) -> str:
        return _EXT_LABELS.get(self.ext_seg.get(), FILTER_RAW)

    # ── 폴더 찾아보기 ──

    def _browse_source(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="원본 폴더 선택")
        if path:
            self.source_var.set(path)

    def _browse_dest(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="대상 폴더 선택")
        if path:
            self.dest_var.set(path)

    # ── Placeholder ──

    def _on_input_focus_in(self, event):
        if self._placeholder_active:
            self.input_text.delete("1.0", "end")
            self.input_text.configure(text_color=("gray10", "gray90"))
            self._placeholder_active = False

    def _on_input_focus_out(self, event):
        if not self.input_text.get("1.0", "end").strip():
            self._placeholder_active = True
            self.input_text.insert("1.0", "파일번호를 입력 (줄바꿈 또는 쉼표로 구분)")
            self.input_text.configure(text_color="gray50")

    # ── 입력 ──

    def _get_input_text(self) -> str:
        if self._placeholder_active:
            return ""
        return self.input_text.get("1.0", "end").strip()

    def _paste_clipboard(self):
        try:
            clip = self.clipboard_get()
        except tk.TclError:
            return
        if self._placeholder_active:
            self.input_text.delete("1.0", "end")
            self.input_text.configure(text_color=("gray10", "gray90"))
            self._placeholder_active = False
        normalized = SEPARATORS_PATTERN.sub("\n", clip).strip()
        current = self.input_text.get("1.0", "end").strip()
        if current:
            self.input_text.insert("end", "\n" + normalized)
        else:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", normalized)

    def _override_paste(self, event):
        self._paste_clipboard()
        return "break"

    def _clear_input(self):
        self.input_text.delete("1.0", "end")
        self._placeholder_active = True
        self.input_text.insert("1.0", "파일번호를 입력 (줄바꿈 또는 쉼표로 구분)")
        self.input_text.configure(text_color="gray50")

    # ── 검색 ──

    def _on_search(self):
        from tkinter import messagebox

        source = self.source_var.get().strip()
        if not source:
            messagebox.showwarning("경고", "원본 폴더를 지정해주세요.")
            return

        text = self._get_input_text()
        if not text:
            messagebox.showwarning("경고", "파일번호를 입력해주세요.")
            return

        terms = copier.parse_input(text)
        if not terms:
            messagebox.showwarning("경고", "유효한 파일번호가 없습니다.")
            return

        try:
            result = copier.search(
                source_folder=source,
                search_terms=terms,
                include_subfolders=self.subfolders_var.get(),
                match_mode=self._get_match_mode(),
                extension_filter=self._get_ext_filter(),
            )
        except FileNotFoundError as e:
            messagebox.showerror("오류", str(e))
            return

        self.preview.set_results(result.matched_files, result.unmatched_terms)

        total_files = len(self.preview._items)
        unmatched = len(result.unmatched_terms)
        self._log(
            f"검색 완료: {len(terms)}개 검색어 → {total_files}개 파일 매칭, "
            f"{unmatched}개 미발견"
        )

        self.copy_btn.configure(state="normal" if total_files > 0 else "disabled")
        self.progress.set(0)
        self.status_label.configure(text="")

    # ── 복사 ──

    def _on_copy(self):
        from tkinter import messagebox

        dest = self.dest_var.get().strip()
        if not dest:
            messagebox.showwarning("경고", "대상 폴더를 지정해주세요.")
            return

        files = self.preview.get_selected_files()
        if not files:
            messagebox.showwarning("경고", "복사할 파일이 선택되지 않았습니다.")
            return

        self.copy_btn.configure(state="disabled", text="복사 중...")
        self.search_btn.configure(state="disabled")
        self.progress.set(0)

        def progress_cb(current, tot):
            self.after(0, self._update_progress, current, tot)

        def log_cb(msg, level):
            self.after(0, self._log, msg)

        def worker():
            try:
                result = copier.copy_files(files, dest, progress_cb, log_cb)
                self.after(0, self._copy_complete, result)
            except OSError as e:
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
                self.after(0, self._copy_reset)

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, current, total):
        self.progress.set(current / total)
        self.status_label.configure(text=f"{current}/{total}")

    def _copy_complete(self, result):
        self._log(
            f"--- 완료: {result['copied']}개 복사, {result['failed']}개 실패 ---"
        )
        self._copy_reset()
        self._save_config()

    def _copy_reset(self):
        self.copy_btn.configure(state="normal", text="📑 복사 실행")
        self.search_btn.configure(state="normal")

    # ── 로그 ──

    def _log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ── 설정 ──

    def _save_config(self):
        data = {
            "source_folder": self.source_var.get(),
            "destination_folder": self.dest_var.get(),
            "match_mode": self._get_match_mode(),
            "extension_filter": self._get_ext_filter(),
            "include_subfolders": self.subfolders_var.get(),
            "window_geometry": self.geometry(),
        }
        config.save_config(data)

    def _on_close(self):
        try:
            self._save_config()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = PhotoCopierApp()
    app.mainloop()
