import io
import tkinter as tk
from pathlib import Path
from threading import Thread

from PIL import Image, ImageDraw, ImageFont, ImageTk

import customtkinter as ctk

from constants import RAW_EXTENSIONS, THUMBNAIL_EXTENSIONS, THUMBNAIL_SIZE

ITEM_PAD = 6


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

    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize(THUMBNAIL_SIZE, Image.LANCZOS)
    return img


def _make_placeholder(ext: str) -> Image.Image:
    w, h = THUMBNAIL_SIZE
    img = Image.new("RGB", (w, h), "#2b2b2b")
    draw = ImageDraw.Draw(img)
    label = ext.upper().lstrip(".")
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((w - tw) / 2, (h - th) / 2), label, fill="#666666", font=font)
    return img


class PreviewItem(ctk.CTkFrame):
    def __init__(self, parent, file_path: Path, search_terms: list[str],
                 size: int, **kwargs):
        super().__init__(parent, width=size, height=size,
                         corner_radius=8, **kwargs)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self.file_path = file_path
        self.check_var = ctk.BooleanVar(value=True)
        self._photo_image = None
        self._on_toggle_callback = None
        self._size = size

        self._thumb_label = ctk.CTkLabel(self, text="")
        self._thumb_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.checkbox = ctk.CTkCheckBox(
            self, text="", variable=self.check_var,
            width=22, checkbox_width=22, checkbox_height=22,
            corner_radius=4, fg_color="#3b8ed0", hover_color="#2d7abf",
            border_width=2, command=self._on_toggle,
        )
        self.checkbox.place(x=6, y=6)

        info = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0)
        info.place(relx=0, rely=1.0, relwidth=1, anchor="sw")
        info.configure(fg_color=("#e0e0e0", "#1a1a1a"))

        ctk.CTkLabel(
            info, text=file_path.name,
            font=ctk.CTkFont(size=11, weight="bold"), anchor="w",
        ).pack(fill="x", padx=6, pady=(4, 0))

        ctk.CTkLabel(
            info, text=", ".join(search_terms),
            font=ctk.CTkFont(size=10), text_color=("gray40", "gray55"),
            anchor="w",
        ).pack(fill="x", padx=6, pady=(0, 4))

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

        self._items: list[PreviewItem] = []
        self._file_paths: dict[str, Path] = {}
        self._match_info: dict[str, list[str]] = {}
        self._photo_refs: list[ImageTk.PhotoImage] = []

        # 상단 바
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=5, pady=(5, 2))

        self.summary_label = ctk.CTkLabel(
            top_bar, text="", font=ctk.CTkFont(size=13), anchor="w",
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

        # 스크롤 영역
        self.scroll_frame = ctk.CTkScrollableFrame(self, orientation="vertical")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._warn_labels: list[ctk.CTkLabel] = []
        self._last_cols = 0
        self._canvas_width = 0
        self._resize_after_id = None

        # 캔버스의 Configure 이벤트로 정확한 너비를 직접 받음
        try:
            self.scroll_frame._parent_canvas.bind(
                "<Configure>", self._on_canvas_configure, add=True,
            )
        except Exception:
            self.bind("<Configure>", self._on_panel_resize)

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
            # 아이템은 아직 부모를 지정하지 않음 — _build_rows에서 배치
            self._items.append((p, self._match_info[key]))

        self._unmatched_terms = list(unmatched_terms)
        self._last_cols = 0
        # 레이아웃이 완료된 후 빌드
        self.after(50, self._build_grid)
        self._update_summary()

    def _on_canvas_configure(self, event):
        """캔버스 리사이즈 시 정확한 너비를 event.width에서 직접 받음."""
        self._canvas_width = event.width
        if not self._items:
            return
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(100, self._rebuild_if_cols_changed)

    def _on_panel_resize(self, event):
        """fallback: 캔버스 바인딩 실패 시 패널 리사이즈로 대체."""
        self._canvas_width = max(200, event.width - 40)
        if not self._items:
            return
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(100, self._rebuild_if_cols_changed)

    def _calc_cols(self) -> int:
        avail = self._canvas_width if self._canvas_width > 10 else max(200, self.winfo_width() - 40)
        # CTkFrame(width=200)은 내부적으로 200*scaling 픽셀을 차지하지만
        # canvas event.width는 tk 픽셀 단위이므로 스케일링을 반영해야 함
        try:
            scaling = self._get_widget_scaling()
        except Exception:
            scaling = 1.0
        cell = (THUMBNAIL_SIZE[0] + ITEM_PAD) * scaling
        return max(1, int(avail / cell))

    def _rebuild_if_cols_changed(self):
        self._resize_after_id = None
        cols = self._calc_cols()
        if cols != self._last_cols:
            self._build_grid()

    def _build_grid(self):
        """grid 레이아웃으로 아이템을 배치."""
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self._warn_labels.clear()
        self._built_items: list[PreviewItem] = []

        cols = self._calc_cols()
        self._last_cols = cols
        item_size = THUMBNAIL_SIZE[0]

        for idx, (p, terms) in enumerate(self._items):
            row = idx // cols
            col = idx % cols
            item = PreviewItem(
                self.scroll_frame, p, terms, size=item_size,
            )
            item.grid(row=row, column=col, padx=(0, ITEM_PAD), pady=(0, ITEM_PAD), sticky="nw")
            item.set_toggle_callback(self._update_summary)
            self._built_items.append(item)

        # 매칭 안 된 검색어
        warn_row = (len(self._items) - 1) // cols + 1 if self._items else 0
        for i, term in enumerate(self._unmatched_terms):
            lbl = ctk.CTkLabel(
                self.scroll_frame,
                text=f"⚠️  {term} → 일치하는 파일 없음",
                text_color="#d4a017", font=ctk.CTkFont(size=12), anchor="w",
            )
            lbl.grid(row=warn_row + i, column=0, columnspan=cols,
                     sticky="w", padx=8, pady=2)
            self._warn_labels.append(lbl)

        # 열 너비를 고정해서 오버플로우 방지
        for c in range(cols):
            self.scroll_frame.columnconfigure(c, weight=0, minsize=item_size)

        self._update_summary()
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
        if not hasattr(self, '_built_items'):
            return []
        return [item.file_path for item in self._built_items
                if item.check_var.get()]

    def select_all(self):
        if not hasattr(self, '_built_items'):
            return
        for item in self._built_items:
            item.check_var.set(True)
        self._update_summary()

    def deselect_all(self):
        if not hasattr(self, '_built_items'):
            return
        for item in self._built_items:
            item.check_var.set(False)
        self._update_summary()

    def _update_summary(self):
        total = len(self._items)
        selected = sum(1 for item in getattr(self, '_built_items', [])
                       if item.check_var.get())
        term_count = len(
            set(t for _, terms in self._items for t in terms)
        )
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
        self._warn_labels.clear()
        self._built_items = []
        self._unmatched_terms = []
        self._last_cols = 0
        self.summary_label.configure(text="")
