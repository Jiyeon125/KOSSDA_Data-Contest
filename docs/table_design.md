# 분석용 테이블 설계 (SQLite Table Design)

> `data/db/youth_analysis.sqlite3` 에 적재된 분석용 테이블 현황.
> 코드북은 적재하지 않는다. 원본 전체 컬럼이 아니라 **분석 변수만 선별**해 넣는다.
> **현재 4개 테이블 모두 구현·적재 완료.** 쉬었음은 별도 테이블이 아니라 `is_rested==1` 필터로 사용한다.

## 1. `youth_life_2024_analysis` (메인) ✅

- **목적**: 청년삶 2024 전체 응답자(19~34세) + 노동상태 라벨 + 쉬었음 파생. 전 분석의 기준.
- **원본**: `data/raw/youth_life/2024_총괄_20260527_89328.csv` (15,098행)
- **전처리 함수**: `src.preprocess.build_youth_2024_analysis()`
- **주요 컬럼**: gender, age_group, edu_final, marital, live_with_parents, econ_status, main_activity,
  living_cost, income_year, hh_income_year, transfer_private/public, debt_total, debt_living, interest_monthly,
  asset_total, housing_tenure, life_satisfaction, happiness, subjective_class, outing_freq,
  help_living_*(5), weight_person
- **파생 컬럼**: `labor_group`, `is_employed`, `is_unemployed`, `is_rested`, `*_label`,
  `has_help`, `family_help_flag`, `no_help_flag`, `not_parent_cohabit`,
  `has_debt`, `has_living_cost_debt`, `has_interest`, `has_private/public_transfer`,
  `isolation_flag`, `vuln_score`(0~6), `safety_net_type`(⚠ 참고용·아래 주), `survey_year`=2024
- **쉬었음 분석**: `WHERE is_rested=1` 로 1,062명 추출(별도 테이블 아님).
- **취약 하위유형(군집)**: DB에 저장하지 않고 **런타임 계산**(`src.clustering.cluster_rested`, K-means k=3).
- **조인 키**: 없음(개인 단위 독립).

> ⚠️ **`safety_net_type` 강등**: 도움원천을 '없음→공식→비공식' 우선순위로 1유형 강제배정한 휴리스틱.
> 순서가 임의적이라 **핵심 분석에서는 제외**, 참고용으로만 유지. 하위유형은 데이터기반 군집화로 대체.

## 2. `youth_life_2022_analysis` (재현성 비교) ✅

- **목적**: 2024와 **동일 정의·동일 파생규칙**으로 처리한 재현성 비교용.
- **원본**: `data/raw/youth_life/2022_총괄_20260527_89328.csv` (14,966행, 494열)
- **전처리 함수**: `src.preprocess.build_youth_2022_analysis()`
- **2024와 다른 점**: 경제활동상태 코드가 **1=취업/2=실업/3=비경활**(2024는 1~8) → 별도 매핑.
  단 쉬었음 정의(비경활 AND 주된활동=10)와 파생 로직(`_derive_safety_and_vuln`)은 동일하게 맞춤.
- **파생 컬럼**: 1번과 동일 + `survey_year`=2022.
- **활용**: 쉬었음 비중·내부 취약지표·군집 하위유형의 **연도 간 재현성**(`scripts/compare_years.py`).

## 3. `eaps_labor_status_summary` (집계 · 배경) ✅

- **목적**: 배경 추이(실업률 vs 쉬었음). EAPS 공식 집계표 기반.
- **원본**: EAPS 3종 집계표(xlsx) → `src.preprocess.build_eaps_summary()`
- **주요 컬럼**: source, age_group, indicator(실업률/쉬었음/비경제활동인구…), year, value, unit
- **전처리**: wide(연도=열) → long 변환, 단위(천명/%) 보존.
- **활용**: S1 배경 2단 추이 차트. 청년 정의(15~29) ≠ 청년삶(19~34) 차이 주석.

## 4. `klips_youth_2023` (KLIPS 보조검증, 개인-가구 결합) ✅

- **목적**: 다른 패널에서의 방향성 보조검증(취업 vs 미취업 가구 부채).
- **원본**: `klips26p`(개인) ⨝ `klips26h`(가구) on `hhid26` → `src.preprocess.build_klips_youth()`
- **확정 변수**: 연령 `p260107`, 성별 `p260101`, 경제활동상태 `p260211`, 근로소득 `p261702`,
  가구 부채유무 `h262632` 등(`scripts/klips_map.py` 로 코드북 매핑 확정).
- **파생**: 19~34 청년 필터, `is_employed_klips`, `is_nonemployed_klips`, `has_debt_klips`, `-1`등 음수→NaN.
- **한계**: KLIPS엔 '쉬었음' 단독 식별 변수 부재 → 취업 vs 미취업 대조까지만. 소표본·회고형 소득 → 방향성 참고.

---

## 테이블 의존 관계

```
EAPS(3) ─────────→ eaps_labor_status_summary
청년삶2024 ───────→ youth_life_2024_analysis ──(is_rested=1 필터)──→ 쉬었음 분석 ──(런타임)──→ 군집 하위유형
청년삶2022 ───────→ youth_life_2022_analysis  (동일 규칙, 재현성 비교)
KLIPS26p ⨝ 26h ──→ klips_youth_2023  (hhid26 결합)
```

| 테이블 | 용도 | 현 상태 |
| --- | --- | --- |
| youth_life_2024_analysis | 메인 | ✅ 구현·적재 |
| youth_life_2022_analysis | 재현성 비교 | ✅ 구현·적재 |
| eaps_labor_status_summary | 배경 추이 | ✅ 구현·적재 |
| klips_youth_2023 | 보조검증 | ✅ 구현·적재 |
