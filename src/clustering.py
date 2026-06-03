"""쉬었음 청년 내부의 '취약 하위유형'을 데이터 기반으로 도출(군집화).

배경: 분석자가 손으로 나눈 우선순위 유형(safety_net_type)은 임의적이라,
      복수응답·구조 변수들을 함께 넣어 K-means 가 스스로 하위유형을 나누게 한다.

특징(이항 취약지표, 해석 가능하도록 최소한으로 선별):
    지원망 없음 · 부모 비동거 · 부채 보유 · 이자 부담 · 고립 경향
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

# 군집 입력 특징 (이항 0/1) -> 표시 라벨
FEATURES = {
    "no_help_flag": "지원망 없음",
    "not_parent_cohabit": "부모 비동거",
    "has_debt": "부채 보유",
    "has_interest": "이자 부담",
    "isolation_flag": "고립 경향",
}
# 군집 해석에 쓰는 외부 결과지표(특징에 포함되지 않음 → 동어반복 아님)
OUTCOMES = {
    "life_satisfaction": "삶 만족도(0-10)",
    "happiness": "행복감(0-10)",
    "subjective_class": "주관 계층(1-5)",
    "vuln_score": "취약점수(0-6)",
}
RANDOM_STATE = 42


def _feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = df[list(FEATURES)].apply(pd.to_numeric, errors="coerce")
    mask = X.notna().all(axis=1)
    return X[mask], mask


def silhouette_by_k(df: pd.DataFrame, k_range=range(2, 6)) -> dict[int, float]:
    """k 후보별 실루엣 점수(군집 수 선택 근거)."""
    Xv, _ = _feature_matrix(df)
    Xs = StandardScaler().fit_transform(Xv)
    scores = {}
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(Xs)
        scores[k] = float(silhouette_score(Xs, km.labels_))
    return scores


def inertia_by_k(df: pd.DataFrame, k_range=range(1, 7)) -> dict[int, float]:
    """k 후보별 관성(WCSS) — 엘보우 기법용. 꺾이는 지점이 적정 k."""
    Xv, _ = _feature_matrix(df)
    Xs = StandardScaler().fit_transform(Xv)
    out = {}
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(Xs)
        out[k] = float(km.inertia_)
    return out


def cluster_rested(df: pd.DataFrame, k: int | None = None) -> tuple[pd.DataFrame, int, dict]:
    """쉬었음 청년을 군집화해 cluster 라벨을 붙인다.

    Returns: (라벨 추가된 df, 선택된 k, 실루엣 점수 dict)
    """
    Xv, mask = _feature_matrix(df)
    Xs = StandardScaler().fit_transform(Xv)
    scores = silhouette_by_k(df)
    if k is None:
        k = max(scores, key=scores.get)
    km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(Xs)

    out = df.copy()
    out["cluster"] = pd.NA
    out.loc[mask, "cluster"] = km.labels_
    return out, k, scores


def profile(df_labeled: pd.DataFrame, weight_col: str = "weight_person") -> pd.DataFrame:
    """군집별 특징 보유율(%)·외부지표 평균·표본수·모집단 추정."""
    rows = []
    w_all = pd.to_numeric(df_labeled[weight_col], errors="coerce")
    for c, gdf in df_labeled.dropna(subset=["cluster"]).groupby("cluster"):
        w = pd.to_numeric(gdf[weight_col], errors="coerce")
        rec = {"cluster": int(c), "표본n": int(len(gdf)),
               "모집단추정(명)": int(round(float(w.sum())))}
        for f, label in FEATURES.items():
            rec[label] = round(float(pd.to_numeric(gdf[f], errors="coerce").mean() * 100), 1)
        for o, label in OUTCOMES.items():
            v = pd.to_numeric(gdf[o], errors="coerce")
            ww = w[v.notna()]
            rec[label] = round(float((v.dropna() * ww).sum() / ww.sum()), 2) if ww.sum() else np.nan
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("cluster").reset_index(drop=True)


def auto_name(profile_df: pd.DataFrame) -> dict[int, str]:
    """군집 프로파일에서 지배적 특징으로 휴리스틱 이름을 만든다."""
    names = {}
    feat_labels = list(FEATURES.values())
    for _, r in profile_df.iterrows():
        c = int(r["cluster"])
        vals = {fl: r[fl] for fl in feat_labels}
        top = max(vals, key=vals.get)
        if r["고립 경향"] >= 50:
            names[c] = "사회적 고립형"
        elif r["지원망 없음"] >= 40:
            names[c] = "무지원형"
        elif r["부채 보유"] >= 50 or r["이자 부담"] >= 40:
            names[c] = "부채압박형"
        elif r["부모 비동거"] >= 60 and max(vals.values()) < 40:
            names[c] = "독립·저부담형"
        elif max(vals.values()) < 25:
            names[c] = "안정형"
        else:
            names[c] = f"{top} 중심형"
    return names
