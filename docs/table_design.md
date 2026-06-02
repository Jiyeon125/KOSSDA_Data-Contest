# 분석용 테이블 설계 (SQLite Table Design)

> `data/db/youth_analysis.sqlite3` 에 적재할 분석용 테이블 설계.
> 코드북은 적재하지 않는다. 원본 전체 컬럼을 그대로 넣지 않고 **분석 변수만 선별**해 넣는다.
> KLIPS는 변수명 확정 후 적재(현재는 설계만).

## 1. `youth_life_2024` (메인)

- **목적**: 청년삶 2024 전체 응답자 + 노동상태 라벨. 질문 A·B의 비교 기준.
- **원본 파일**: `data/raw/youth_life/2024_총괄_20260527_89328.csv` (15,098행)
- **주요 컬럼**: gender, age_group, edu_final, marital, live_with_parents, econ_status, main_activity, job_search_4wk, job_want, living_cost, income_year, hh_income_year, transfer_private/public, debt_total, debt_living, interest_monthly, asset_total, housing_tenure, life_satisfaction, happiness, subjective_class, outing_freq, help_living_*(5), weight_person, + **labor_group**(파생)
- **전처리 필요**: cp949 로드, 분석변수 선별·영문명 변경, 코드→라벨 매핑, labor_group 파생, 금액 단위/0 처리
- **조인 키**: 없음(개인 단위 독립). survey_year=2024 부여
- **활용**: 취업/실업/쉬었음 비교, 배경 통계
- **상태**: ✅ 이미 `youth_2024_all` 로 구현됨(컬럼 확장 필요)

## 2. `youth_life_2024_rested` (쉬었음 부분집합)

- **목적**: 쉬었음 청년(1,062명) 심층 분석(질문 C). 기술통계·지원망·취약성.
- **원본**: `youth_life_2024` 에서 `econ_status==8 & main_activity==10` 필터
- **주요 컬럼**: `youth_life_2024` 와 동일 + 파생(has_debt, has_living_cost_debt, has_interest, has_private_transfer, has_public_transfer, family_help_flag, no_help_flag, not_parent_cohabit, vuln_score)
- **전처리 필요**: 필터 + 취약 파생변수 + 취약점수
- **조인 키**: 없음
- **활용**: 집단비교, 취약성 유형화
- **상태**: ✅ `youth_2024_rested` 구현됨(파생변수 보강 필요)

## 3. `youth_life_2022` (비교용, 선택)

- **목적**: 2024 대비 시점 비교(질문 B 보조). 단순 병합 금지.
- **원본**: `data/raw/youth_life/2022_총괄_20260527_89328.csv` (14,966행, 494열)
- **주요 컬럼**: 2024와 매핑되는 핵심 변수만(gender, age, econ_status, main_activity, living_cost, debt_personal, help_*)
- **전처리 필요**: **2024↔2022 변수 매핑표 작성**, 코드 동일성 검증, 공통 변수만 정렬
- **조인 키**: 없음(별도 연도 테이블). survey_year=2022
- **활용**: 동일 변수만 연도 비교(별 테이블 union 아님)
- **상태**: ⬜ 매핑 확정 후 진행

## 4. `labor_status_summary` (집계 · 배경)

- **목적**: 질문 A·E 배경. 노동상태/연령/연도별 집계.
- **원본**: EAPS 3종 집계표(+ 청년삶 2024 노동상태 집계)
- **주요 컬럼**: source, year, age_group, indicator(취업/실업/비경활/쉬었음/실업률…), value, unit
- **전처리 필요**: EAPS wide→long 변환, 지표명 표준화, 단위(천명/%) 표기
- **조인 키**: 없음(long tidy 집계 테이블)
- **활용**: 추이선·구성비 시각화
- **상태**: ⬜ EAPS long 변환 후 진행

## 5. `klips_person_latest` (KLIPS 개인 26차)

- **목적**: 질문 D. 청년 취업/미취업 개인 경제조건.
- **원본**: `data/raw/klips/kor_data_CUM0066_klips26p.xlsx` (23,364행, 742열) — engine=calamine
- **주요 컬럼**: `pid`, `hhid26`, `hmem26`, 연령(확인필요), 성별(확인필요), 경제활동상태(확인필요), 개인소득(확인필요)
- **전처리 필요**: 분석변수 선별(코드북으로 변수명 확정), `-1`→NaN, 19~34 필터, 취업/미취업 파생
- **조인 키**: `hhid26`(→가구), `pid`
- **활용**: 가구 테이블과 조인해 청년 경제조건 분석
- **상태**: ⚠️ 변수명 확정 후 진행

## 6. `klips_household_latest` (KLIPS 가구 26차)

- **목적**: 질문 D. 가구 소득·소비·부채·자산.
- **원본**: `data/raw/klips/kor_data_CUM0066_klips26h.xlsx` (16,317행, 1,036열) — engine=calamine
- **주요 컬럼**: `hhid26`, 가구소득/소비/부채/자산(확인필요)
- **전처리 필요**: 분석변수 선별, `-1`→NaN, 단위 확인, 파생(부채/소득비 등)
- **조인 키**: `hhid26`
- **활용**: 개인 테이블과 조인
- **상태**: ⚠️ 변수명 확정 후 진행

## 7. `klips_youth_joined` (KLIPS 개인-가구 결합)

- **목적**: 질문 D. 청년 개인 + 소속 가구 경제조건 결합 분석.
- **원본**: `klips_person_latest` ⨝ `klips_household_latest`
- **주요 컬럼**: pid, hhid26, 청년 개인변수 + 가구 경제변수
- **전처리 필요**: `person.hhid26 = household.hhid26` LEFT JOIN, 19~34 청년 필터
- **조인 키**: `hhid26`
- **활용**: "청년 미취업 ↔ 가구 경제조건" 보조 검증
- **상태**: ⚠️ 5·6 완료 후 진행

---

## 테이블 의존 관계

```
EAPS(3) ─→ labor_status_summary ─┐
청년삶2024 ─→ youth_life_2024 ─→ youth_life_2024_rested
청년삶2022 ─→ youth_life_2022 (선택)
KLIPS26p ─→ klips_person_latest ─┐
                                 ├─(hhid26)─→ klips_youth_joined
KLIPS26h ─→ klips_household_latest ┘
```

| 테이블 | 우선순위 | 현 상태 |
| --- | --- | --- |
| youth_life_2024 / _rested | 1 | ✅ 구현(보강) |
| labor_status_summary (EAPS) | 2 | ⬜ |
| klips_person/household/joined | 3 | ⚠️ 변수확정 후 |
| youth_life_2022 | 4(선택) | ⬜ |
