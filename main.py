import re
from itertools import combinations
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="급식 규칙 찾기", page_icon="🍱", layout="wide")
st.title("🍱 급식 규칙 찾기 (연관 규칙 분석)")


@st.cache_data
def load_and_preprocess():
    url = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"
    df = pd.read_csv(url, encoding="utf-8")

    baskets = []
    all_items = set()

    for raw_menu in df["메뉴"].dropna():
        if not isinstance(raw_menu, str):
            continue
        items = raw_menu.split("|")
        cleaned_basket = set()
        for item in items:
            cleaned_item = re.sub(r"\(.*?\)", "", item).strip()
            if cleaned_item:
                cleaned_basket.add(cleaned_item)
                all_items.add(cleaned_item)
        if cleaned_basket:
            baskets.append(cleaned_basket)

    total_days = len(baskets)
    num_unique_items = len(all_items)

    item_counts = {}
    for basket in baskets:
        for item in basket:
            item_counts[item] = item_counts.get(item, 0) + 1

    pair_counts = {}
    for basket in baskets:
        for item1, item2 in combinations(sorted(basket), 2):
            pair = (item1, item2)
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    rules = []
    for (item1, item2), co_occur in pair_counts.items():
        sup = co_occur / total_days
        conf_12 = co_occur / item_counts[item1]
        lift_12 = conf_12 / (item_counts[item2] / total_days)

        rules.append(
            {
                "조건": item1,
                "결과": item2,
                "동시": co_occur,
                "지지도": round(sup, 4),
                "신뢰도": round(conf_12, 4),
                "향상도": round(lift_12, 4),
            }
        )

        conf_21 = co_occur / item_counts[item2]
        lift_21 = conf_21 / (item_counts[item1] / total_days)

        rules.append(
            {
                "조건": item2,
                "결과": item1,
                "동시": co_occur,
                "지지도": round(sup, 4),
                "신뢰도": round(conf_21, 4),
                "향상도": round(lift_21, 4),
            }
        )

    rules_df = pd.DataFrame(rules)
    total_pairs = len(pair_counts)

    return (
        total_days,
        num_unique_items,
        total_pairs,
        rules_df,
        sorted(list(all_items)),
        item_counts,
        baskets,
    )


(
    total_days,
    num_unique_items,
    total_pairs,
    rules_df,
    item_list,
    item_counts,
    baskets,
) = load_and_preprocess()

# 전체 급식 요약 정보
st.markdown(
    f"**급식 일수:** {total_days}일 | **메뉴 종류 수:** {num_unique_items}개 | **함께 나온 적이 있는 메뉴 쌍의 수:** {total_pairs}개"
)
st.markdown("---")

# 사이드바 설정 (필터링 및 정렬)
st.sidebar.header("🔍 검색 및 정렬 설정")

# 최소 동시 일수 슬라이더 (1~10, 기본값 1)
min_co_occur = st.sidebar.slider(
    "최소 동시 출현 일수", min_value=1, max_value=10, value=1
)

# 메뉴 선택 필터
selected_item = st.sidebar.selectbox(
    "특정 메뉴 선택 (전체 보기: 선택 안 함)", ["전체"] + item_list
)

# 정렬 기준 선택
sort_option = st.sidebar.radio(
    "정렬 기준 선택", ["향상도 순", "신뢰도 순", "동시 순"]
)

sort_column_map = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시",
}

# 1. 최소 동시 일수 필터링
filtered_df = rules_df[rules_df["동시"] >= min_co_occur].copy()

# 2. 메뉴 좁혀보기 필터링
if selected_item != "전체":
    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_item)
        | (filtered_df["결과"] == selected_item)
    ]

# 3. 정렬 적용
target_col = sort_column_map[sort_option]
filtered_df = filtered_df.sort_values(
    by=[target_col, "동시"], ascending=False
).reset_index(drop=True)

# 필터링 후 남아있는 규칙 수 표시
st.info(f"💡 현재 설정 조건(최소 동시 일수 {min_co_occur}일 이상)에 해당하는 규칙: **총 {len(filtered_df)}개**")

# Plotly 가로 막대그래프 (상위 10개)
st.subheader("📊 향상도 상위 10개 규칙")
top10_df = filtered_df.sort_values(by="향상도", ascending=False).head(10)

if not top10_df.empty:
    top10_df["규칙"] = top10_df["조건"] + " ➔ " + top10_df["결과"]
    plot_df = top10_df.sort_values(by="향상도", ascending=True)

    fig = px.bar(
        plot_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        title=f"연관 규칙 향상도 Top 10 ({'전체' if selected_item == '전체' else selected_item})",
        labels={"향상도": "향상도 (Lift)", "규칙": "메뉴 규칙 (조건 ➔ 결과)"},
        color="향상도",
        color_continuous_scale="Blues",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(height=450, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("선택한 조건에 해당하는 규칙이 없습니다.")

# 연관 규칙 데이터 테이블
st.subheader("📋 연관 규칙 데이터")
st.dataframe(filtered_df, use_container_width=True)

st.markdown("---")

# 함께 나온 적 없는 짝 조회 화면
st.subheader("🚫 함께 나온 적 없는 짝 찾기")
st.write(
    "선택한 메뉴와 한 번도 함께 나온 적이 없으면서, 혼자서는 10일 이상 제공된 메뉴를 조회합니다."
)

target_menu = st.selectbox(
    "분석할 기준 메뉴를 선택하세요",
    item_list,
    key="never_paired_menu_select",
)

if target_menu:
    target_days = item_counts[target_menu]

    # 해당 메뉴와 함께 나온 적 있는 다른 메뉴들 추출
    co_occurring_items = set()
    for basket in baskets:
        if target_menu in basket:
            co_occurring_items.update(basket)

    # 한 번도 함께 나오지 않았으면서 + 단독 출현 10일 이상인 메뉴 추출
    never_paired_list = []
    for item, count in item_counts.items():
        if item != target_menu and item not in co_occurring_items and count >= 10:
            never_paired_list.append({"메뉴": item, "출현 일수": count})

    never_paired_df = pd.DataFrame(never_paired_list)

    st.write(f"📌 **{target_menu}**이(가) 급식에 나온 총 일수: **{target_days}일**")

    if not never_paired_df.empty:
        never_paired_df = never_paired_df.sort_values(
            by="출현 일수", ascending=False
        ).reset_index(drop=True)
        st.dataframe(never_paired_df, use_container_width=True)
    else:
        st.info("조건(함께 나온 적 없음 & 10일 이상 출현)을 만족하는 메뉴가 없습니다.")
