# RawPull

파일번호로 RAW/JPG 사진을 빠르게 검색하고 복사하는 데스크톱 앱

## 다운로드

| 플랫폼 | 다운로드 |
|--------|----------|
| Windows | **[RawPull.exe](https://github.com/ascoeur9/rawpull/releases/latest/download/RawPull.exe)** |
| macOS | **[RawPull-mac.zip](https://github.com/ascoeur9/rawpull/releases/latest/download/RawPull-mac.zip)** |

설치 불필요 - 다운로드 후 바로 실행 (macOS는 압축 해제 후 RawPull.app 실행)

## 주요 기능

- **파일번호 검색** - 파일번호를 입력하면 원본 폴더에서 해당 파일을 자동 검색
- **썸네일 미리보기** - RAW(RW2, ARW, CR2, NEF 등) 파일의 내장 썸네일을 추출하여 미리보기 표시
- **선택 복사** - 체크박스로 원하는 파일만 골라서 대상 폴더로 일괄 복사
- **매칭 모드** - 포함 매칭(부분 일치) / 정확히 일치 선택 가능
- **확장자 필터** - RAW, JPG/이미지, 전체 중 선택
- **하위 폴더 포함** - 원본 폴더의 하위 폴더까지 재귀 검색

## 사용법

1. 원본 폴더 (사진이 있는 폴더) 지정
2. 대상 폴더 (복사할 위치) 지정
3. 파일번호 입력 (줄바꿈, 쉼표, 탭으로 구분)
4. 검색 버튼 클릭
5. 썸네일에서 복사할 파일 선택/해제
6. 복사 실행

## 지원 파일 형식

| 구분 | 확장자 |
|------|--------|
| RAW | `.arw` `.cr2` `.cr3` `.nef` `.orf` `.rw2` `.raf` `.dng` `.pef` `.srw` `.raw` |
| JPG/이미지 | `.jpg` `.jpeg` `.webp` `.heic` `.heif` |

## 개발 환경에서 실행

```bash
pip install -r requirements.txt
python main.py
```

## 빌드

```bash
pip install pyinstaller
pyinstaller RawPull.spec --noconfirm
```

`dist/RawPull.exe`에 단일 실행 파일이 생성됩니다.
