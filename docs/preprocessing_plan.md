# 전처리 계획 (Preprocessing Plan)

> 데이터별 필터·컬럼·코드값·결측·파생변수 규칙을 정의한다.
> 실제 컬럼명/코드값을 확인 못한 부분은 **"확인 필요"** 로 표기하고 임의 확정하지 않는다.
> 통계 검증·분석방법은 `docs/research_design.md` 를, 변수 의미는 `docs/variable_candidates.md` 를 참조.

## 0. 공통 원칙

- 인코딩: 청년삶 CSV = **cp949** (utf-8 → cp949 → euc-kr 폴백). KLIPS xlsx = **engine="calamine"**. KLIPS 코드북 = **xlrd**.
- 경로: 모두 `pathlib` 사용(Windows 호환). 파일 없으면 죽지 않고 안내.
- 선별 적재: 원본 전체 컬럼이 아니라 **분석 변수만** 선택. 모든 파일 일괄 병합 금지.
- 코드값: 코드북 확인 전 0/9/99 를 결측으로 단정 금지. 금액 변수의 `0` 은 "없음"이라는 **유효값**.
- 코드 보존: 원본 코드 컬럼은 유지하고, `*_label` 라벨 컬럼을 추가(원본 훼손 금지).

## 1. 청년삶실태조사 2024 (메인) — 확정 규칙

### 1-1. 필터링
- 청년 전체: 전 응답자(19~34세, age_group∈{1,2,3}).
- **쉬었음 청년**: `econ_status == 8` (비경제활동인구) **AND** `main_activity == 10` (쉬었음) → 1차 EDA 1,062명.
- 노동상태 그룹(labor_group):
  - 취업자: econ_status ∈ {1,2,3,4,5,6}
  - 실업자: econ_status == 7
  - 비경활_쉬었음: econ_status == 8 & main_activity == 10
  - 비경활_기타: econ_status == 8 & main_activity ≠ 10

### 1-2. 사용할 핵심 컬럼
`variable_candidates.md §1` 의 변수(식별/연령/성별/학력/혼인/부모동거/경활/활동상태/구직·취업의사/생활비/소득/이전소득/부채/이자/자산/주거/만족도/계층인식/고립/도움집단/가중치).

### 1-3. 컬럼명 표준화
- 긴 한글 라벨 → 영문 분석명(`variable_candidates.md` 의 "변수명(제안)").
- 정규화: 소문자, 공백→`_`, 특수문자 제거(`preprocess.normalize_column_names`).

### 1-4. 코드값 처리 (코드북 확정)
| 변수 | 코드→라벨 |
| --- | --- |
| gender | 1=남, 2=여 |
| age_group | 1=19~24, 2=25~29, 3=30~34 |
| live_with_parents | 1=부모동거, 2=비동거 |
| econ_status | 1~6=취업, 7=실업, 8=비경활 |
| main_activity | 10=쉬었음 (그 외 1~11 라벨) |
| housing_tenure | 1=자가…7=무상거주 |
| subjective_class | 1=하층…5=상층 |
| marital | 1=배우자있음,2=미혼,3=이혼,4=별거,5=사별 |
| edu_final | 1=무학…8=박사 |
| life_satisfaction | 0~10 (11점) |

### 1-5. 결측 처리
- 금액(생활비/소득/부채/이자/자산): `0` = 유효(없음). 음수·공백만 결측 검토(코드북 특이사항 **확인 필요**).
- 도움집단 복수응답: `1`=해당, 비해당 코드 **확인 필요**(공백/0/2 여부).
- 비해당 다수 변수(은둔 지속기간 등): 비해당은 NaN, 분석 시 해당자만.

### 1-6. 파생변수 (쉬었음 부분집합용)
| 파생변수 | 정의 |
| --- | --- |
| labor_group | §1-1 |
| has_debt | debt_total > 0 |
| has_living_cost_debt | debt_living > 0 |
| has_interest | interest_monthly > 0 |
| has_private_transfer | transfer_private > 0 |
| has_public_transfer | transfer_public > 0 |
| family_help_flag | help_living_family == 1 |
| no_help_flag | help_living_none == 1 |
| has_help | 가족/지인/공공/민간 중 하나라도 1 |
| not_parent_cohabit | live_with_parents == 2 |
| isolation_flag(추정) | outing_freq ∈ {7,8} (은둔성향) — 해석 주의 |
| safety_net_type(⚠참고) | 도움원천을 없음>공식>비공식 우선순위로 1유형 배정 — **임의성으로 핵심분석 제외, 참고용** |

> ✅ 구현 완료: 위 파생은 `build_youth_2024_analysis()` + 공통 `_derive_safety_and_vuln()` 에 반영됨.
> **취약 하위유형은 손으로 안 나누고 데이터기반 군집화로 대체** — `src/clustering.py`(K-means k=3,
> 입력: no_help/not_parent_cohabit/has_debt/has_interest/isolation). 결과: 안정형/사회적 고립형/부채압박형.

### 1-7. 쉬었음 여부 변수 생성 방식
`is_rested = (econ_status==8) & (main_activity==10)` (Boolean→int). labor_group 으로도 표현.

### 1-8. 취약성 지표(vuln_score) 생성 방식
취약 방향 가산(각 1점): not_parent_cohabit, family_help 불가, no_help_flag, has_debt, has_living_cost_debt, has_interest.
- 합산(0~6) → 분위로 안정형/중간형/취약형 구분.
- ⚠️ **이전소득 없음은 취약 가산 제외**(소득·자산 충분해 없을 수 있음 → 단독 해석 금지).
- 점수 가중치/임계값은 분포 확인 후 조정(임의 확정 금지).

## 2. 청년삶 2022 (재현성 비교) — ✅ 구현 완료

- **단순 병합 금지** 원칙 유지. row union 아닌 **연도별 별 테이블**(`youth_life_2022_analysis`, survey_year=2022).
- **확정된 코드 차이**: 경제활동상태가 **1=취업/2=실업/3=비경활**(2024의 1~8과 다름). 쉬었음=`econ==3 & main_activity==10`.
  도움망은 `...[복수응답_...]_1~_5`(가족/지인/공공/민간/없음, 0·1) — 2024의 5개 이항과 동일 구조.
- 컬럼 매핑: `YOUTH_2022_ANALYSIS_COLMAP`(대괄호 표기 `[청년(개인) 기준]` 등) + `_add_labor_group_2022()`.
- 파생은 2024와 **동일 함수**(`_derive_safety_and_vuln`)로 처리 → 사과 대 사과 비교.
- 불일치/부재 변수(income 총소득 등)는 비교에서 제외하고 한계로 명시.

## 3. KLIPS 26차(2023) — ✅ 변수 확정·구현 완료

> 변수명은 `scripts/klips_map.py` 로 `개인용`/`가구용` 코드북을 파싱해 확정. `build_klips_youth()` 에 반영.
> 한계: KLIPS엔 '쉬었음' 단독 식별 변수 부재 → 취업 vs 미취업 대조까지만(보조검증).

### 3-1. 필터링
- 청년: 연령 `p260107` 기준 19~34.
- 취업/미취업: 경제활동상태 `p260211`(취업/실업/비경활)로 파생.

### 3-2. 사용한 핵심 컬럼 (확정)
- 개인(p): `pid`, `hhid26`, `hmem26`, 연령 `p260107`, 성별 `p260101`, 경제활동상태 `p260211`, 근로소득 `p261702`.
- 가구(h): `hhid26`, 가구 부채유무 `h262632` 등.

### 3-3. 컬럼명 표준화
- `p26####`/`h26####` → 의미 영문명(코드북 변수설명 기반). 매핑표 작성 후 적용.

### 3-4. 코드값/결측 처리
- KLIPS 결측 규약: **`-1` = 모름/무응답** → NaN.
- 금액 단위·물가보정 여부 **확인 필요**(연도 비교 시).

### 3-5. 파생변수
- youth_employed(취업/미취업), 가구 부채/소득 비율, 순자산 등 — 변수 확정 후.

### 3-6. KLIPS 개인-가구 결합 방식
- **조인 키 = `hhid26`** (개인.hhid26 = 가구.hhid26), LEFT JOIN(개인 기준).
- 개인번호 `hmem26` 은 가구 내 식별용. 과거 wave 결합 시 wave별 hhid(`hhid25` 등) 사용.
- ⚠️ 청년삶/EAPS 와는 **개인 단위 결합하지 않음**(층위 분리).

## 4. EAPS 집계표

- wide(연도=열) → **long(year, age_group, indicator, value, unit)** 변환.
- 쉬었음 표(2003~2025), 경활총괄(2000~2025, 8지표), 비경활(2000~2025) 통합 → `labor_status_summary`.
- 단위(천명/%) 컬럼 보존. 청년 정의(15-29) ≠ 청년삶(19-34) 차이 주석.

## 5. 전처리 산출물 현황 (모두 완료)

| 작업 | 산출물 | 상태 |
| --- | --- | --- |
| 청년삶2024 파생변수 + vuln_score | `build_youth_2024_analysis()` | ✅ |
| EAPS wide→long 변환 | `build_eaps_summary()` | ✅ |
| KLIPS 코드북 변수 매핑 확정 | `scripts/klips_map.py` | ✅ |
| KLIPS 26p/26h 선별·결합 | `build_klips_youth()` | ✅ |
| 청년삶2022 동일규칙 비교 테이블 | `build_youth_2022_analysis()` | ✅ |
| 취약 하위유형 데이터기반 군집화 | `src/clustering.py` (런타임) | ✅ |
| 2022↔2024 재현성·추세 비교 | `scripts/compare_years.py` | ✅ |

> requirements 반영됨: **`xlrd>=2.0.1`**, **`python-calamine`**, **`scipy`**, **`scikit-learn`**(군집화).
