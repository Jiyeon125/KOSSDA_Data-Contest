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
- [ ] EAPS 집계표 wide→long (`labor_status_summary`)
- [ ] KLIPS 코드북 변수 매핑 확정(연령/성별/경활/소득/부채 변수명)
- [ ] KLIPS 26p/26h 전처리 + `hhid26` 조인 (`klips_youth_joined`)
- [ ] (선택) 청년삶 2022 비교 테이블

## 2. 분석 / 통계검증
- [ ] 집단비교 검정 헬퍼(Mann-Whitney/카이제곱 + 효과크기) `queries.py`
- [ ] 쉬었음 내부 비교(부모동거/도움유무/부채여부) 유의성·효과크기 보고
- [ ] (선택) 생활안전망 유형화(점수/군집)

## 3. 시각화 / 산출물
- [ ] Streamlit 분석 흐름 화면(개요→배경→메인→보조검증→격차→결론)
- [ ] 공모전 PPT 10장 / 수업 대시보드 페이지 구성

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
| 2026-06-03 01:44 | feat: 청년삶 2024 분석 전처리 + 설계문서 + 커밋 안전점검 자동화 | 문서 기반 청년삶2024 전처리(youth_life_2024_analysis) 작성, PROGRESS 체크리스트 및 GitHub 업로드 안전점검/자동커밋 스크립트 구축 |
