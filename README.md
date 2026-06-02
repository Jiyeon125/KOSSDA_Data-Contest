# 청년 '쉬었음' 집단의 내부 취약성 분석

2026 경영정보처리론 · KOSSDA 대학생 데이터 시각화 공모전 참여 프로젝트

> ⚠️ 현재 저장소는 **실행 가능한 최소 구조(skeleton)** 단계입니다.
> 화면에 보이는 모든 수치는 **SAMPLE(예시) 데이터**이며 실제 분석 결과가 아닙니다.

---

## 프로젝트 개요

KOSSDA(한국사회과학자료원) 데이터를 활용하여 노동시장에서 **'쉬었음'** 으로 분류되는
청년 집단을 분석하는 Streamlit 기반 데이터 시각화 프로젝트입니다.
'쉬었음' 청년을 하나의 단일 집단이 아니라 **내부 구조를 가진 이질적 집단**으로 보고,
그 안의 취약성 차이를 데이터로 드러내는 것을 목표로 합니다.

## 문제의식

- '쉬었음' 청년 인구가 꾸준히 증가하고 있으나, 실업자도 다른 비경제활동 범주도 아닌
  **모호한 위치**에 있어 정책 사각지대에 놓이기 쉽다.
- '쉬었음' 집단은 단일 집단이 아니라 서로 다른 취약성을 가진 **하위 집단**으로 구성되어 있을 가능성이 크다.
- 따라서 집단 내부의 취약성 차이를 구분해 분석할 필요가 있다.

## 분석 목표

1. 청년 '쉬었음' 집단의 **하위 유형 구분**
2. 하위 유형별 **취약성(건강·경제·사회적 고립 등)** 수준 비교
3. **장기 쉬었음** 상태로 이어지는 특성 탐색
4. 정책적 **우선 개입 대상** 집단 식별

## 폴더 구조

```
KOSSDA_Data-Contest/
│
├─ app.py                 # Streamlit 앱 (메인 대시보드)
├─ requirements.txt       # 의존 라이브러리
├─ README.md
├─ .gitignore
│
├─ data/                  # (git 추적 제외)
│  ├─ raw/                # 원본 데이터
│  ├─ processed/          # 전처리 데이터
│  └─ db/                 # SQLite DB (youth_analysis.sqlite3)
│
├─ src/
│  ├─ inspect_data.py     # 원본 데이터 구조 점검
│  ├─ preprocess.py       # 원본 → 전처리 (범용 함수)
│  ├─ build_db.py         # processed CSV → SQLite 적재
│  ├─ queries.py          # SQL 조회 → DataFrame
│  └─ charts.py           # Plotly 차트 함수
│
├─ notebooks/
│  └─ 01_data_check.ipynb # 데이터 점검용 노트북
│
├─ docs/
│  ├─ proposal.md         # 기획서
│  ├─ analysis_plan.md    # 분석 계획
│  └─ prompt_log.md       # 프롬프트/작업 로그
│
└─ assets/
   └─ images/             # 이미지 자료
```

## 실행 방법

### 1) 가상환경 생성 및 활성화 (선택, 권장)

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

### 2) 의존성 설치

```bash
pip install -r requirements.txt
```

### 3) 실데이터 파이프라인 실행 순서

원본 데이터는 GitHub에 올리지 않습니다. (`data/raw`, `data/processed`, `data/db` 및 `*.csv/*.xlsx/*.sav/*.dta/*.sqlite3/*.db` 는 `.gitignore` 처리됨)

```bash
# 1) 원본 데이터를 data/raw/ 에 넣기 (csv 또는 xlsx)

# 2) 데이터 구조 확인 (행/열 수, 컬럼명, 결측치, dtype 등)
python src/inspect_data.py
#   → 특정 파일만 보려면: python src/inspect_data.py 파일명.csv

# 3) 전처리 수행 (data/processed 에 정제 CSV 저장)
python src/preprocess.py

# 4) SQLite DB 생성 (data/db/youth_analysis.sqlite3)
python src/build_db.py

# 5) Streamlit 실행
streamlit run app.py
```

> 참고: DB 파일이 아직 없어도 Streamlit 앱은 정상 실행되며, 화면에서 다음 단계 안내를 보여줍니다.

## 데이터 출처

> **추후 작성 예정**입니다. (KOSSDA 제공 데이터 명칭 및 출처는 데이터 확정 후 기재)

---

© 2026 경영정보처리론 · KOSSDA 대학생 공모전 프로젝트
