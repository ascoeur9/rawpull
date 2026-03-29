import shutil
from dataclasses import dataclass, field
from pathlib import Path

from constants import (
    ALL_EXTENSIONS,
    FILTER_ALL,
    FILTER_JPG,
    FILTER_RAW,
    JPG_EXTENSIONS,
    MATCH_EXACT,
    RAW_EXTENSIONS,
    SEPARATORS_PATTERN,
)


@dataclass
class MatchResult:
    matched_files: dict[str, list[Path]] = field(default_factory=dict)
    unmatched_terms: list[str] = field(default_factory=list)


def parse_input(text: str) -> list[str]:
    parts = SEPARATORS_PATTERN.split(text)
    seen = set()
    result = []
    for p in parts:
        p = p.strip()
        if p and p not in seen:
            seen.add(p)
            result.append(p)
    return result


def scan_files(
    source_folder: Path, include_subfolders: bool, extension_filter: str
) -> list[Path]:
    if extension_filter == FILTER_RAW:
        valid_ext = RAW_EXTENSIONS
    elif extension_filter == FILTER_JPG:
        valid_ext = JPG_EXTENSIONS
    else:
        valid_ext = ALL_EXTENSIONS

    if include_subfolders:
        candidates = source_folder.rglob("*")
    else:
        candidates = source_folder.iterdir()

    return [p for p in candidates if p.is_file() and p.suffix.lower() in valid_ext]


def match_files(
    file_list: list[Path], search_terms: list[str], match_mode: str
) -> MatchResult:
    matched: dict[str, list[Path]] = {}
    unmatched: list[str] = []

    for term in search_terms:
        term_lower = term.lower()
        hits = []
        for fp in file_list:
            stem_lower = fp.stem.lower()
            if match_mode == MATCH_EXACT:
                if stem_lower == term_lower:
                    hits.append(fp)
            else:
                if term_lower in stem_lower:
                    hits.append(fp)
        if hits:
            matched[term] = hits
        else:
            unmatched.append(term)

    return MatchResult(matched_files=matched, unmatched_terms=unmatched)


def search(
    source_folder: str,
    search_terms: list[str],
    include_subfolders: bool,
    match_mode: str,
    extension_filter: str,
) -> MatchResult:
    src = Path(source_folder)
    if not src.is_dir():
        raise FileNotFoundError(f"원본 폴더를 찾을 수 없습니다: {source_folder}")

    file_list = scan_files(src, include_subfolders, extension_filter)
    return match_files(file_list, search_terms, match_mode)


def copy_files(
    files: list[Path],
    destination: str,
    progress_callback=None,
    log_callback=None,
) -> dict:
    dest = Path(destination)
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"대상 폴더를 생성할 수 없습니다: {e}")

    copied = 0
    failed = 0
    errors = []
    total = len(files)

    for i, src_path in enumerate(files, 1):
        try:
            shutil.copy2(src_path, dest / src_path.name)
            copied += 1
            if log_callback:
                log_callback(f"✅ {src_path.name} → 복사 완료", "info")
        except OSError as e:
            failed += 1
            msg = f"❌ {src_path.name} → 복사 실패: {e}"
            errors.append(msg)
            if log_callback:
                log_callback(msg, "error")

        if progress_callback:
            progress_callback(i, total)

    return {"copied": copied, "failed": failed, "errors": errors}
