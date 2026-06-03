# 진행사항 체크리스트 (PROGRESS)

> KOSSDA 청년 '쉬었음' 분석 프로젝트의 진행 상황을 기록한다.
> 프롬프트 작성 + 코드 수정 시마다 `python scripts/auto_commit.py` 로 안전점검 → 커밋 → 이 파일 로그가 자동 갱신된다.

## 0. 문서 (설계/기획)
- [x] `docs/project_context.md` — 프로젝트 배경/원칙
- [x] `docs/research_design.md` — 제안서 통합(실험·통계검증)
- [x] `docs/data_inventory.md` — 데이터 인벤토리
- [x] `docs/variable_candidates.md` — 변수 후보
- [x] `docs/analysis_question_variable_map.md` — 질문별 변수 매핑
- [x] `docs/table_design.md` — SQLite 테이블 설계
- [x] `docs/preprocessing_plan.md` — 전처리 계획

## 1. 전처리 / 데이터셋
- [x] 청년삶 2024 분석용 전처리 `build_youth_2024_analysis()` (변수선별·청년필터·노동상태/쉬었음/취업/구직·파생·결측)
- [x] `data/processed/youth_life_2024_analysis.csv` 생성 (15,098행)
- [x] SQLite `youth_life_2024_analysis` 테이블 적재
- [ ] 청년삶 2024 취약점수 가중치/임계값 분포 검토 후 확정
- [x] EAPS 집계표 wide→long (`eaps_labor_status_summary`, 2,570행, 2000~2025)
- [x] KLIPS 코드북 변수 매핑 확정(`scripts/klips_map.py`, 연령/성별/경활/소득/부채)
- [x] KLIPS 26p/26h 전처리 + `hhid26` 조인 (`klips_youth_2023`, 청년 3,818명)
- [ ] (선택) 청년삶 2022 비교 테이블

## 2. 분석 / 통계검증
- [x] 집단비교 검정 헬퍼(Mann-Whitney/카이제곱 + 효과크기) `queries.py`
- [x] 가중 추정 헬퍼(가중 비율/평균 + 모집단 규모) `queries.py`
- [x] 쉬었음 내부 비교(부모동거/도움유무) 유의성·효과크기 보고 (`scripts/insights.py`)
- [x] 생활안전망 유형화(비공식/공식/없음) + 취약 누적 스펙트럼 (`scripts/rested_gap.py`)
- [x] 취약 하위유형 군집화(K-means, 임의 typology 대체) (`src/clustering.py`, `scripts/cluster_rested.py`)
  - k=3: 안정형 83% / 사회적 고립형 4% / 부채압박형 13%, 군집 간 웰빙차 KW p<0.0001

## 3. 시각화 / 산출물
- [x] 인사이트용 경량 시각화 9종 + 내부격차 3종 `outputs/figures/`
- [x] `docs/visualization_strategy.md` 시각화 전략 확정
- [x] Streamlit 1차 대시보드 S0~S7 (`app.py`, 배경→정체성→생계→내부격차→스펙트럼→보조검증→결론)
- [x] 각 화면 '집계·분석 방법/읽는 법' 설명 보강 + 이중축 0기준 고정
- [x] `발표_대본.md` 공모전 발표 대본(Q&A 포함)
- [ ] 분석보강(2022 비교, 군집화) 후 대시보드 반영
- [ ] 공모전 PPT 10장 구성

## 4. 운영 / 자동화
- [x] `.gitignore` 데이터·비밀정보 차단
- [x] `scripts/precommit_check.py` 깃 안전점검
- [x] `scripts/auto_commit.py` 안전점검 통과 시에만 커밋 + 로그 갱신
- [x] `PROGRESS.md` 체크리스트

---

## 커밋 로그
<!-- AUTO-LOG: 아래 표는 scripts/auto_commit.py 가 자동으로 추가합니다. 위 줄은 수정하지 마세요. -->

| 시각(KST) | 메시지 | 프롬프트 요약 |
| --- | --- | --- |
| 2026-06-03 13:30 | feat: 군집 수 선택에 엘보우(WCSS) 추가 | k 선택 근거에 엘보우 기법 추가 요청 → inertia_by_k 추가, 그림13을 엘보우+실루엣 2분할로 갱신(엘보우 k=3 부근 꺾임 확인) |
| 2026-06-03 13:23 | feat: 쉬었음 취약 하위유형 군집화(임의 typology 대체) | safety_net_type 우선순위 배정의 통계적 약점 지적 → K-means 데이터기반 군집화로 대체. 안정형/사회적고립형/부채압박형 3유형 도출(고립형 웰빙 급락 KW p<0.0001 r=0.47), 군집모듈+그림13~15+research_design 개정 |
| 2026-06-03 13:10 | docs: 대시보드 설명 보강 + 축 0기준 수정 + 발표 대본 | 각 화면에 집계/분석 방법 설명(expander) 추가, S1 이중축 0기준 고정, 프로젝트 루트에 발표_대본.md(내레이션+Q&A) 작성 |
| 2026-06-03 12:52 | feat: 1차 Streamlit 대시보드(S0~S7) + 시각화 전략 + 차트 헬퍼 | 시각화 전략 확정 후 제안서 흐름 기반 대시보드 구축(배경EAPS→정체성→생계→내부 생활안전망 격차→취약 스펙트럼→KLIPS 보조검증→결론), 가중추정/검정배지 반영 |
| 2026-06-03 12:41 | feat: 쉬었음 내부 생활안전망 격차 심화분석(가중추정+유형화) | 생활안전망 유형(비공식/공식/없음) 파생, 가중 비율/평균/모집단추정 헬퍼, 유형별 격차·취약누적 스펙트럼 시각화(10~12) |
| 2026-06-03 12:24 | feat: EAPS/KLIPS 전처리 + 통계검정 헬퍼 + 인사이트 시각화 9종 | 쉬었음 집단 비교 시각화/검정, EAPS 추이 long변환, KLIPS 26차(2023) 변수매핑·청년 보조검증 추출 |
| 2026-06-03 01:44 | feat: 청년삶 2024 분석 전처리 + 설계문서 + 커밋 안전점검 자동화 | 문서 기반 청년삶2024 전처리(youth_life_2024_analysis) 작성, PROGRESS 체크리스트 및 GitHub 업로드 안전점검/자동커밋 스크립트 구축 |
