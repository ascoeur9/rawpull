import re

# 지원 확장자
RAW_EXTENSIONS = frozenset({
    ".arw", ".cr2", ".cr3", ".nef", ".orf",
    ".rw2", ".raf", ".dng", ".pef", ".srw", ".raw",
})

JPG_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".webp", ".heic", ".heif",
})

ALL_EXTENSIONS = RAW_EXTENSIONS | JPG_EXTENSIONS

# 매칭 모드
MATCH_CONTAINS = "contains"
MATCH_EXACT = "exact"

# 확장자 필터
FILTER_RAW = "raw"
FILTER_JPG = "jpg"
FILTER_ALL = "all"

# 입력 구분자 패턴
SEPARATORS_PATTERN = re.compile(r"[,\t;\n]+")

# 썸네일
THUMBNAIL_SIZE = (200, 200)
THUMBNAIL_EXTENSIONS = frozenset({".jpg", ".jpeg", ".webp", ".png", ".bmp", ".tiff", ".tif"})

# 앱 설정
APP_TITLE = "RawPull"
MIN_WIDTH = 900
MIN_HEIGHT = 700
DEFAULT_GEOMETRY = "1200x800"
CONFIG_FILENAME = "config.json"
