import io
from pathlib import Path
from threading import Thread

from PIL import Image, ImageDraw, ImageFont, ImageTk

import customtkinter as ctk

from constants import (
    FONT_FAMILY,
    RAW_EXTENSIONS,
    THUMBNAIL_EXTENSIONS,
    THUMBNAIL_SIZE,
)


def _load_thumbnail(file_path: Path) -> Image.Image:
    ext = file_path.suffix.lower()
    img = None

    if ext in THUMBNAIL_EXTENSIONS:
        try:
            img = Image.open(file_path)
        except Exception:
            pass

    if img is None and ext in RAW_EXTENSIONS:
        try:
            import rawpy
            with rawpy.imread(str(file_path)) as raw:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    img = Image.open(io.BytesIO(thumb.data))
                else:
                    img = Image.fromarray(thumb.data)
        except Exception:
            pass

    if img is None:
        return _make_placeholder(ext)

    img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
    return img


def _make_placeholder(ext: str) -> Image.Image:
    w, h = THUMBNAIL_SIZE
    img = Image.new("RGB", (w, h), "#2b2b2b")
    draw = ImageDraw.Draw(img)
    label = ext.upper().lstrip(".")
    try:
        font = ImageFont.truetype("yugothib.ttc", 22)
    except OSError:
        try:
            font = ImageFont.truetype("arial.ttf", 22)
        except OSError:
            font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((w - tw) / 2, (h - th) / 2), label, fill="#666666", font=font)
    return img


# 짝수/홀수 행 배경색 (light, dark)
_ROW_COLORS = (
    ("#f0f0f0", "#2a2d2e"),  # 짝수 (0, 2, 4, ...)
    ("#e2e2e2", "#232627"),  # 홀수 (1, 3, 5, ...)
)


class PreviewItem(ctk.CTkFrame):
    """가로형 리스트 아이템: [체크박스 | 썸네일 | 정보]"""

    def __init__(self, parent, file_path: Path, search_terms: list[str],
                 row_index: int = 0, **kwargs):
        bg = _ROW_COLORS[row_index % 2]
        super().__init__(parent, corner_radius=0, fg_color=bg, **kwargs)
        self.file_path = file_path
        self.check_var = ctk.BooleanVar(value=True)
        self._photo_image = None
        self._on_toggle_callback = None

        thumb_w, thumb_h = THUMBNAIL_SIZE

        # 체크박스 (맨 왼쪽)
        self.checkbox = ctk.CTkCheckBox(
            self, text="", variable=self.check_var,
            width=22, checkbox_width=22, checkbox_height=22,
            corner_radius=4, fg_color="#3b8ed0", hover_color="#2d7abf",
            border_width=2, command=self._on_toggle,
        )
        self.checkbox.pack(side="left", padx=(10, 6))

        # 썸네일
        thumb_frame = ctk.CTkFrame(
            self, width=thumb_w, height=thumb_h,
            corner_radius=6, fg_color=("#d0d0d0", "#2b2b2b"),
        )
        thumb_frame.pack(side="left", padx=(0, 0), pady=6)
        thumb_frame.pack_propagate(False)

        self._thumb_label = ctk.CTkLabel(thumb_frame, text="")
        self._thumb_label.pack(expand=True)

        # 정보 (오른쪽)
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=(12, 8), pady=8)

        ctk.CTkLabel(
            info, text=file_path.name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x")

        # 검색어
        ctk.CTkLabel(
            info, text="검색어: " + ", ".join(search_terms),
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=("gray40", "gray55"), anchor="w",
        ).pack(fill="x", pady=(4, 0))

        # 파일 경로
        ctk.CTkLabel(
            info, text=str(file_path.parent),
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=("gray50", "gray45"), anchor="w",
        ).pack(fill="x", pady=(2, 0))

    def set_toggle_callback(self, cb):
        self._on_toggle_callback = cb

    def _on_toggle(self):
        if self._on_toggle_callback:
            self._on_toggle_callback()

    def set_thumbnail(self, photo_image: ImageTk.PhotoImage):
        self._photo_image = photo_image
        self._thumb_label.configure(image=photo_image)


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")

        self._items: list[tuple] = []
        self._file_paths: dict[str, Path] = {}
        self._match_info: dict[str, list[str]] = {}
        self._photo_refs: list[ImageTk.PhotoImage] = []
        self._built_items: list[PreviewItem] = []
        self._unmatched_terms: list[str] = []

        # 상단 바
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=5, pady=(5, 2))

        self.summary_label = ctk.CTkLabel(
            top_bar, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13), anchor="w",
        )
        self.summary_label.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            top_bar, text="전체 선택", width=72, height=26,
            command=self.select_all,
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            top_bar, text="전체 해제", width=72, height=26,
            fg_color="gray40", hover_color="gray50",
            command=self.deselect_all,
        ).pack(side="right")

        # 스크롤 리스트
        self.scroll_frame = ctk.CTkScrollableFrame(self, orientation="vertical")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def set_results(
        self, matched_files: dict[str, list[Path]], unmatched_terms: list[str],
    ):
        self.clear()

        for term, paths in matched_files.items():
            for p in paths:
                key = str(p)
                if key not in self._file_paths:
                    self._file_paths[key] = p
                    self._match_info[key] = []
                self._match_info[key].append(term)

        for key in self._file_paths:
            p = self._file_paths[key]
            self._items.append((p, self._match_info[key]))

        self._unmatched_terms = list(unmatched_terms)
        self._build_list()
        self._update_summary()

    def _build_list(self):
        """리스트 레이아웃으로 아이템 배치."""
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self._built_items.clear()

        for idx, (p, terms) in enumerate(self._items):
            item = PreviewItem(self.scroll_frame, p, terms, row_index=idx)
            item.pack(fill="x")
            item.set_toggle_callback(self._update_summary)
            self._built_items.append(item)

        # 매칭 안 된 검색어
        for term in self._unmatched_terms:
            ctk.CTkLabel(
                self.scroll_frame,
                text=f"⚠️  {term} → 일치하는 파일 없음",
                text_color="#d4a017",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                anchor="w",
            ).pack(fill="x", padx=8, pady=2)

        self._load_thumbnails_async()

    def _load_thumbnails_async(self):
        items_copy = list(self._built_items)

        def worker():
            for item in items_copy:
                try:
                    img = _load_thumbnail(item.file_path)
                except Exception:
                    img = _make_placeholder(item.file_path.suffix.lower())
                photo = ImageTk.PhotoImage(img)
                self._photo_refs.append(photo)
                item.after(0, item.set_thumbnail, photo)

        Thread(target=worker, daemon=True).start()

    def get_selected_files(self) -> list[Path]:
        return [item.file_path for item in self._built_items
                if item.check_var.get()]

    def select_all(self):
        for item in self._built_items:
            item.check_var.set(True)
        self._update_summary()

    def deselect_all(self):
        for item in self._built_items:
            item.check_var.set(False)
        self._update_summary()

    def _update_summary(self):
        total = len(self._items)
        selected = sum(1 for item in self._built_items if item.check_var.get())
        term_count = len(set(t for _, terms in self._items for t in terms))
        if total > 0:
            self.summary_label.configure(
                text=f"검색어 {term_count}개 → 파일 {total}개 매칭 ({selected}개 선택)"
            )
        else:
            self.summary_label.configure(text="")

    def clear(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self._items.clear()
        self._file_paths.clear()
        self._match_info.clear()
        self._photo_refs.clear()
        self._built_items.clear()
        self._unmatched_terms.clear()
        self.summary_label.configure(text="")
