# 청년 '쉬었음' 집단의 내부 취약성 분석

2026 경영정보처리론 · KOSSDA 대학생 데이터 시각화 공모전 참여 프로젝트

> 📊 현재 **실데이터 분석 진행 단계**입니다(청년삶 2022·2024, EAPS, KLIPS 적재·분석 완료).
> 분석 서사·결정의 단일 출처는 [`docs/analysis_flow.md`](docs/analysis_flow.md)(1~9단계 + 결정로그),
> 진행상황은 [`PROGRESS.md`](PROGRESS.md). 원본 데이터는 GitHub에 올리지 않습니다.

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

1. '쉬었음' 청년이 **무엇으로 버티는가** — 사적 안전망(가족 중심) 구조 확인
2. 그 안에서 **취약을 가르는 핵심 축 = '사회적 고립'** 정조준(웰빙↓·도움없음↑, 공식 은둔변수 용량반응)
3. 2022→2024 **재현성·악화 추세** 확인(규모↑, 사적 안전망 약화, 평균 불변=내부격차 심화)
4. 정책적 **우선 개입 대상**(고립·도움없음) 식별

> 초기엔 '하위 유형 군집화'를 시도했으나 자연 군집이 없어 **폐기**하고(결정로그 D1·D7),
> 내부 위험을 **'고립' 단일 축**으로 재정의했습니다. 자세한 경위는 `docs/analysis_flow.md` 참조.

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
│  ├─ raw/                # 원본 데이터 (출처별 하위 폴더로 정리)
│  │  ├─ youth_life/      # 청년삶실태조사 2022, 2024 (메인)
│  │  ├─ klips/           # KLIPS p/h 파일 (KOSSDA 보조)
│  │  └─ eaps/            # 경제활동인구조사/청년부가조사 (배경)
│  ├─ processed/          # 전처리 데이터
│  ├─ db/                 # SQLite DB (youth_analysis.sqlite3)
│  └─ codebook/           # 코드북 (변수 해석용 참고자료, DB 적재 X)
│
├─ src/
│  ├─ inspect_data.py     # 원본 데이터 구조 점검 (하위 폴더 재귀 탐색)
│  ├─ preprocess.py       # 원본 → 전처리 (범용 함수)
│  ├─ build_db.py         # processed CSV → SQLite 적재 (코드북 제외)
│  ├─ queries.py          # SQL 조회 → DataFrame
│  └─ charts.py           # Plotly 차트 함수 (막대/히스토그램)
│
├─ notebooks/
│  └─ 01_data_check.ipynb # 데이터 점검용 노트북
│
├─ docs/
│  ├─ project_context.md            # 프로젝트 배경지식 (작업 전 필독)
│  ├─ analysis_flow.md              # ⭐ 분석 서사·결정로그 (단일 출처, 최신 기준)
│  ├─ research_design.md            # 연구 설계(제안서 통합) + KOSSDA/KGSS 전략
│  ├─ external_data_references.md   # 외부 데이터 출처·인용서식
│  ├─ variable_candidates.md / analysis_question_variable_map.md  # 변수·질문 매핑
│  ├─ table_design.md / preprocessing_plan.md / visualization_strategy.md
│  └─ proposal.md / analysis_plan.md / prompt_log.md  # 초기 기획·로그(이력)
│
└─ assets/
   └─ images/             # 이미지 자료
```

> 원본 데이터는 출처별 하위 폴더(`youth_life/`, `klips/`, `eaps/`)로 정리한다.
> 코드북 파일은 `data/codebook/` 에 따로 두며, DB 에는 적재하지 않는다.
> 데이터 파일(`*.csv`, `*.xlsx`, `*.sav`, `*.dta`, `*.sqlite3`, `*.db`)은 GitHub 에 올리지 않는다.

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
# 1) 원본 데이터를 data/raw/<출처>/ 에 넣기 (csv 또는 xlsx)
#    예) data/raw/youth_life/, data/raw/klips/, data/raw/eaps/
#    코드북은 data/codebook/ 에 따로 둔다.

# 2) 데이터 구조 확인 (행/열 수, 컬럼명, 결측치, dtype 등) — 하위 폴더까지 재귀 탐색
python src/inspect_data.py
#   → 특정 파일만: python src/inspect_data.py youth_life/youth_2024.csv

# 3) 전처리 수행 (data/processed 에 정제 CSV 저장)
python src/preprocess.py

# 4) SQLite DB 생성 (data/db/youth_analysis.sqlite3) — 코드북 자동 제외
python src/build_db.py
#   → 특정 파일만: python src/build_db.py youth_life/youth_2024_clean.csv

# 5) Streamlit 실행
streamlit run app.py
```

> 참고: DB 파일이 아직 없어도 Streamlit 앱은 정상 실행되며, 화면에서 다음 단계 안내를 보여줍니다.

## 데이터 출처

| 데이터 | 출처/소장 | 역할 |
| --- | --- | --- |
| 청년삶실태조사 2022·2024 | 국무조정실/한국보건사회연구원 (MDIS) | **메인 미시분석** |
| 경제활동인구조사·청년부가(EAPS) | 통계청 (KOSIS/MDIS) | 배경(쉬었음 추이) |
| 한국노동패널조사(KLIPS) 26차 | 한국노동연구원 / **KOSSDA 소장** | KOSSDA 보조(가구부채) |
| 한국종합사회조사(KGSS) 2003–2025 | 성균관대 SRC / **KOSSDA 소장** | KOSSDA 메인 축(고립↔웰빙 재현, **도입 예정**) |
| (외부 검증) 복지부 2023 고립·은둔 청년 실태조사, OECD/고용정보원 NEET | — | 결과 외적 타당도 |

> 상세 출처·인용서식은 [`docs/external_data_references.md`](docs/external_data_references.md) 참조.

---

© 2026 경영정보처리론 · KOSSDA 대학생 공모전 프로젝트
