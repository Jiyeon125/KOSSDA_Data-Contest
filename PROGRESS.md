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
- [x] 청년삶 2022 분석 전처리 `build_youth_2022_analysis()` (2024와 동일 파생규칙, econ 1/2/3 코딩 대응) → `youth_life_2022_analysis` 적재
- [x] **팀원 레포(Inactive-Youth) 파생변수 이식** `_derive_team_risk_and_type6()` — risk_score(0–5)·risk_level·safety_net_type6 (2022·2024 공통, 재적재 완료)

## 2. 분석 / 통계검증
> 🔴 **실제 분석 서사·결정의 단일 출처 = [`docs/analysis_flow.md`](docs/analysis_flow.md)** (1~10단계 + 결정로그 D1~D16, **LOCKED**).
> 🟢 **PPT 초안 = [`발표_초안.md`](발표_초안.md)** (표지 제외 10장).

- [x] 집단비교 검정 헬퍼(Mann-Whitney/카이제곱/Fisher + 효과크기) `queries.py`
- [x] 가중 추정 헬퍼(가중 비율/평균 + 모집단 규모) `queries.py`
- [x] **단계별 확정 분석(iterative)** — `docs/analysis_flow.md`에 1~9단계 기록
  - 1 배경(EAPS 추이) · 2 실업률↓ vs 쉬었음↑ 사각지대 · 4 가족 중심 사적 안전망(fig04c)
  - 5 **'고립' 정조준**(fig21: 삶만족 r=-0.47, 도움없음 OR=5.77, Fisher) ← 핵심 축
  - 6 취약 '총량 스펙트럼' 폐기(fig22, rho=-0.09 비단조) · 8 2022→2024 재현성(fig16/17/17b)
- [~] ~~취약 하위유형 K-means 군집화~~ **폐기(D1)** — 자연 군집 없음·고립형만 웰빙 유의.
  코드(`src/clustering.py`)·그림(13~19)은 **방법론 이력**으로만 보존.
- [x] **공식 은둔변수 용량반응**(`scripts/rested_seclusion.py`, fig23) — 은둔 기간↑→삶만족↓(6.70→3.75), 외부 복지부 조사(3.7 vs 6.7) 수렴
- [x] 2022 vs 2024 재현성 (`scripts/compare_years.py`, 그림 16/17/17b)
  - 쉬었음 비중 5.2%→7.2%(가중), 내부 취약(지원망없음·부채·이자) 모두 2024↑·유의, 평균 웰빙 불변=내부격차 심화
  - 사적 안전망 약화(가족도움 95→85%, 도움없음 3.5→8.4%) / 고립은 척도차로 연도비교 제외(D9)
- [x] **외부 보강**(`docs/external_data_references.md`): OECD/고용정보원 NEET 배경(fig00), 복지부 2023 고립·은둔 실태조사(fig23 수렴)
- [x] **10단계 KGSS 전국 일반화(KOSSDA 기둥)** `scripts/kgss_isolation.py`, fig24 — 고립 격차 Δ0.317*** vs 취업 Δ0.023 n.s.(약 14배), 페널티 취업·미취업 일관. 부록 fig25(친구수 용량반응)·fig26(외로움→우울 2012). N=3,489(2021·23·25 통합)
- [x] **11단계 팀원 레포 머지(생활안전망 격차 H1~H4)** — H1 부모동거×부채(15.4 vs 30.2%, χ²=28.6, V=0.164), H2 가족지원×생활비(중앙값 200 vs 175, r=-0.17), H3 도달률(가족부재 156명 중 도움없음 57.1%·공공 14.1%), H4 위험군 23.0%·6유형. **재현가이드 §7 벤치마크 전 항목 일치 검증**. 헬퍼 `holding_rate/holder_median/holding_summary/coverage_rates` + Fisher 자동 전환(`queries.py`). 상세: `docs/merge_comparison.md`

## 3. 시각화 / 산출물
- [x] 인사이트용 경량 시각화 다수 `outputs/figures/` (fig00 NEET, 04c 생존, 21 고립, 23 은둔, 24~26 KGSS, 16/17/17b 재현성)
- [x] `docs/visualization_strategy.md` 시각화 전략(상단 최신기준 배너 부착)
- [x] **공모전 PPT 10장 초안 `발표_초안.md`** — 데이터·방법·인사이트·출처(링크/DOI)+그림 매핑 완료(1차 summary)
- [x] Streamlit 대시보드 `app.py` — **확정 서사(고립 핵심·KGSS 기둥)로 재정렬** (S4 고립·S5 은둔·S6 KGSS, 군집/스펙트럼 폐기)
- [x] **app.py S0~S9 머지 재구성(중간발표 디벨롭)** — S2 보유율 표·S3 H1/H2·S4 도달률·S5 위험 게이지/6유형 treemap/유형×삶만족 신규, 고립·KGSS·재현성은 S6~S8로 이동. `charts.gauge`·`charts.treemap` 추가
- [x] 각 화면 '집계·분석 방법/읽는 법' 설명 보강 + 축 0기준 고정
- [~] `발표_대본.md` — **STALE**: 옛 군집 S4 기준. 외부보강·은둔·KGSS 반영해 **재작성 필요**(`발표_초안.md` 기준으로)
- [ ] PPT 실제 디자인(요약문 양식) + Streamlit Community Cloud 배포

## 4. 운영 / 자동화
- [x] `.gitignore` 데이터·비밀정보 차단
- [x] `scripts/precommit_check.py` 깃 안전점검 (+ 코드 변경 시 발표대본·설명문서 동기화 경고)
- [x] `scripts/auto_commit.py` 안전점검 통과 시에만 커밋 + 로그 갱신
- [x] `PROGRESS.md` 체크리스트

## 5. 진행 중 / 향후 (백로그)

### 5-0. KOSSDA 데이터 강화 — **KGSS 본편 기둥 확정** (10단계)
- [x] **KGSS 도입(KOSSDA 기둥·KGSS상 트랙)** — 한국종합사회조사 2003–2025 누적(DOI `KOSSDA-A1-CUM-0074-V1`).
  - [x] pyreadstat 도입 + `.sav/.dta` 변수탐색기 `scripts/kgss_inspect.py`
  - [x] (사용자) 한국어 `.sav`+코드북 `data/raw/kgss/` 투입 확인
  - [x] 변수 확정(`HAPPINSS`·`BESTFRND`·`EMPLY`·`OTHREL4`·`FEELDOWN`) → `scripts/kgss_isolation.py`
  - [x] **고립>취업 전국 재현** 분석·시각화(fig24, 부록 25·26) — 청년삶 미시결과의 외적 타당도 + KGSS상 자격
  - [ ] (선택) `build_kgss` 전처리 → `kgss_*` 테이블로 DB 적재(현재는 스크립트가 `.sav` 직접 로드)
- [~] (백로그) **KLIPS 격상** — 현재 정직축소(fig09 가구부채)로 자격 충족. 추가로 가구 경제토대 분석은 시험 후 재검토.

> ⏭ **시험 후 다음 라운드**: 레포 새로 파서 KOSSDA 자료검색 추가 탐색(청년삶·EAPS 소장 확인, 다른 KOSSDA 소장 대체데이터), KGSS DB 적재, PPT 디자인·배포.

### 5-1. 기타 아이디어
- [ ] **지원하는 '가족'의 부담** — 쉬었음 청년을 떠받치는 가족이 (1) 지원에 얼마나 부담을 느끼는지,
  (2) 수입(가구소득)의 얼마를 지원에 지출하는지.
  ※ 데이터 한계 점검 필요: 청년삶은 *청년 응답자* 기준이라 '부양 가족의 주관적 부담' 직접 변수는 없을 가능성 큼.
- [ ] **(보류) 생활비 압박 시점비교** — 외부 물가(CPI)는 끌어오지 **않음**(아래 D10 근거).
  대안(방법 B): 내부 변수 `has_living_cost_debt`(생활비 때문에 진 빚)의 2022 vs 2024 변화를
  17b 옆 보조 패널로 추가 가능. microdata 내부라 검정 가능하고 서사와 일관.
  우선 `hh_income_year`(가구소득)·`transfer_private`(사적 이전소득 수령액) 기반 **간접 추정**(가구소득 대비 이전소득 비중 등) 가능성부터 확인.

---

## 커밋 로그
<!-- AUTO-LOG: 아래 표는 scripts/auto_commit.py 가 자동으로 추가합니다. 위 줄은 수정하지 마세요. -->

| 시각(KST) | 메시지 | 프롬프트 요약 |
| --- | --- | --- |
| 2026-06-05 00:33 | feat(1차 summary): 고립 핵심·KGSS 기둥으로 서사 LOCKED — 문서 최신화 + PPT 초안 + 대시보드 재정렬 + KGSS 하드코딩 제거 | 1차 summary: (1)모든 md 최신화(analysis_flow D14~D16 KGSS기둥·캥거루차별화, external_refs KGSS인용, research_design §9 확정, PROGRESS) (2)발표_초안.md PPT 10장 신설 (3)app.py를 군집폐기→고립핵심·KGSS기둥(S4~S6)으로 재정렬, st.image+plotly 혼합 (4)KGSS 수치 하드코딩 제거: kgss_isolation.py가 요약CSV 산출→앱이 읽어 표시. AppTest 9섹션 0예외 |
| 2026-06-04 22:26 | feat(KGSS 준비): pyreadstat 도입 + KGSS .sav/.dta 변수탐색기(kgss_inspect.py) + raw/kgss 폴더 | KGSS는 SPSS/Stata 포맷이라 pyreadstat로 코드없이 읽기. 변수설명·값레이블 자동추출해 고립·웰빙·고용·계층 변수 탐색하는 스캐폴드. 파일 받기 전 준비단계 |
| 2026-06-04 22:10 | feat(외부보강+KLIPS): NEET 배경(fig00)·공식 은둔 용량반응+복지부 수렴(fig23)·KLIPS 정직축소(fig09) + 외부데이터 출처문서 | KLIPS는 KOSSDA 필수데이터라 제외 대신 정직축소(가구부채만, 이상소득 제거). 5단계 seclusion_duration 용량반응+복지부 고립은둔 외부수렴(6.70~6.7,3.75~3.7). 1단계 OECD NEET 배경. external_data_references.md 신설, analysis_flow D11~D13 |
| 2026-06-04 21:38 | docs: 물가(CPI) 보류 결정 기록(D10) + 대안 방법B(has_living_cost_debt) 백로그 | 물가 인과 도입은 구조적 정책공백 주장 희석 우려로 보류, 안전망약화는 객관지표로만, 생활비압박은 내부변수 대안 명시. analysis_flow D10 + PROGRESS 백로그 |
| 2026-06-04 21:35 | analysis(8단계 보강): 사적 안전망 약화 그림(17b) - 가족/지인 도움↓·도움없음↑, 제도 공백 지속 | step8 보조: compare_years에 사적 안전망(부모동거/가족·지인도움/공공/도움없음) 2022vs2024 비교표+Fig17b 추가, analysis_flow 8단계에 반영 |
| 2026-06-04 20:49 | analysis(8단계): 2022 재현성 - 규모/취약 악화 일관, 평균불변=내부격차심화. 고립은 척도차로 연도비교 제외(D9) | step8 compare_years에서 isolation 연도비교 제거(2022 1-7점 vs 2024 1-8점, n=3), 폐기군집 Fig18 제거, Fig17 footnote, analysis_flow 8단계+D9 |
| 2026-06-04 20:44 | analysis(6단계): 연속 스펙트럼 폐기(fig22) - 취약총량은 웰빙 설명 못함 + D7/D8 | step6 vuln_score 그라데이션 음성결과(rho=-0.09 비단조), 스펙트럼 프레이밍 폐기, 7단계 생략 통합, 8단계로 |
| 2026-06-03 17:22 | analysis(5단계): 고립 정조준(fig21) 확정 - 웰빙·지원망 이중고 + Fisher 정확검정(D6) | step5 고립 단일축 확정(삶만족 r=-0.47, 도움없음 OR=5.77), 소표본 2x2 Fisher 채택, 의사결정 로그 D6 추가 |
| 2026-06-03 17:09 | analysis(4단계): 가족중심 생존(04c) 확정 + 안전망등급 보강실험(fig20) + 의사결정 근거 로그 | step4 재설계(버티는 법 먼저), 도움가능≠안전 보강실험, 결정·배제 근거(D1~D5) 문서화, 가족부담 백로그 추가 |
| 2026-06-03 16:34 | analysis(2단계): 실업률↓ vs 쉬었음↑ 사각지대 확정 + fig02 2단 패널 대비 | 2단계 확정 기록, fig02를 같은연령·2단패널 대비로 수정(정직한 제목) |
| 2026-06-03 16:12 | analysis(1단계): 배경 EAPS 청년 쉬었음 추이 확정 + fig01 청년밴드 중심 수정 | 단계별 분석 흐름 도입(analysis_flow.md), fig01 계 제외·청년밴드만, 군집 단정 폐기 방침 기록 |
| 2026-06-03 14:51 | feat: 군집 PCA 2D 투영 바이플롯 추가(fig19) + 설계문서 반영 | 군집화 시각자료(PCA 차원축소) 추가, 분석 figure 전체 재생성 |
| 2026-06-03 14:49 | docs: 분석 문서 최신화(군집·2022·KLIPS 반영) + 문서동기화 점검 docs/ 전체 확장 | docs 최신화 + precommit_check docs-sync 가 docs/*.md 전체를 커버하도록 확장 |
| 2026-06-03 14:33 | docs: 발표 대본 최신화 + 코드-문서 동기화 경고 자동화 | 발표_대본.md를 최신 대시보드(S1 2단분리, S4 데이터기반 군집, S7 재현성 신설, 결론 S8)에 맞게 갱신. precommit_check에 check_docs_sync 추가(app.py/src 변경 시 발표대본·설명문서 갱신 여부 경고, 차단X) |
| 2026-06-03 13:54 | fix: S1 추이 차트를 이중축에서 위·아래 2단 분리로 변경 | S1 실업률 vs 쉬었음 이중축이 어느 선이 어느 축인지 헷갈린다는 피드백 → line_stacked_trends(공유 x축, 패널별 독립 y축, 패널제목 색=선 색 매칭) 추가하여 분리, 설명도 보강 |
| 2026-06-03 13:45 | feat: 대시보드에 군집 하위유형(S4)·재현성 추세(S7) 반영 | 보강분석 대시보드 반영. S4를 데이터기반 K-means 3유형(안정/고립/부채압박)으로 전면 개정(휴리스틱 typology는 참고로 강등), S7 재현성·추세(2022↔2024) 섹션 신설, 결론 S8로 이동. AppTest 9개 섹션 0 예외 확인 |
| 2026-06-03 13:40 | feat: 청년삶 2022 전처리 + 2022 vs 2024 재현성 비교 | 2022 비교 분석. 파생로직 공통화(_derive_safety_and_vuln), build_youth_2022_analysis(econ 1/2/3 코딩 대응) 추가·DB적재, compare_years.py로 쉬었음 비중(5.2→7.2%)·내부취약지표(지원망없음/부채/이자/고립 모두 2024↑ 유의)·3하위유형 재현성 확인(그림16~18) |
| 2026-06-03 13:30 | feat: 군집 수 선택에 엘보우(WCSS) 추가 | k 선택 근거에 엘보우 기법 추가 요청 → inertia_by_k 추가, 그림13을 엘보우+실루엣 2분할로 갱신(엘보우 k=3 부근 꺾임 확인) |
| 2026-06-03 13:23 | feat: 쉬었음 취약 하위유형 군집화(임의 typology 대체) | safety_net_type 우선순위 배정의 통계적 약점 지적 → K-means 데이터기반 군집화로 대체. 안정형/사회적고립형/부채압박형 3유형 도출(고립형 웰빙 급락 KW p<0.0001 r=0.47), 군집모듈+그림13~15+research_design 개정 |
| 2026-06-03 13:10 | docs: 대시보드 설명 보강 + 축 0기준 수정 + 발표 대본 | 각 화면에 집계/분석 방법 설명(expander) 추가, S1 이중축 0기준 고정, 프로젝트 루트에 발표_대본.md(내레이션+Q&A) 작성 |
| 2026-06-03 12:52 | feat: 1차 Streamlit 대시보드(S0~S7) + 시각화 전략 + 차트 헬퍼 | 시각화 전략 확정 후 제안서 흐름 기반 대시보드 구축(배경EAPS→정체성→생계→내부 생활안전망 격차→취약 스펙트럼→KLIPS 보조검증→결론), 가중추정/검정배지 반영 |
| 2026-06-03 12:41 | feat: 쉬었음 내부 생활안전망 격차 심화분석(가중추정+유형화) | 생활안전망 유형(비공식/공식/없음) 파생, 가중 비율/평균/모집단추정 헬퍼, 유형별 격차·취약누적 스펙트럼 시각화(10~12) |
| 2026-06-03 12:24 | feat: EAPS/KLIPS 전처리 + 통계검정 헬퍼 + 인사이트 시각화 9종 | 쉬었음 집단 비교 시각화/검정, EAPS 추이 long변환, KLIPS 26차(2023) 변수매핑·청년 보조검증 추출 |
| 2026-06-03 01:44 | feat: 청년삶 2024 분석 전처리 + 설계문서 + 커밋 안전점검 자동화 | 문서 기반 청년삶2024 전처리(youth_life_2024_analysis) 작성, PROGRESS 체크리스트 및 GitHub 업로드 안전점검/자동커밋 스크립트 구축 |
