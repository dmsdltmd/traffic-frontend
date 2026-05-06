import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.ticker
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

# 나눔고딕 폰트 적용 (packages.txt로 설치됨)
font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
try:
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = fm.FontProperties(fname=font_path).get_name()
except:
    pass
plt.rcParams['axes.unicode_minus'] = False

API_URL = "https://seongnam-api.onrender.com/predict"

dong_options = {
    "수진1동": ("4113110100", 37.4386, 127.1378),
    "수진2동": ("4113110200", 37.4361, 127.1401),
    "신흥1동": ("4113110300", 37.4412, 127.1356),
    "신흥2동": ("4113110400", 37.4438, 127.1334),
    "신흥3동": ("4113110500", 37.4459, 127.1312),
    "단대동":  ("4113110600", 37.4502, 127.1289),
    "은행동":  ("4113110700", 37.4478, 127.1423),
    "양지동":  ("4113110800", 37.4334, 127.1445),
    "태평1동": ("4113110900", 37.4298, 127.1356),
    "태평2동": ("4113111000", 37.4312, 127.1312),
    "태평3동": ("4113111100", 37.4289, 127.1289),
    "태평4동": ("4113111200", 37.4267, 127.1267),
}

target_options = ["어린이사고", "노인사고", "야간사고", "음주사고", "전체사고"]

st.set_page_config(page_title="성남시 교통사고 예측", layout="wide")
st.title("🚦 성남시 교통사고 위험 예측 플랫폼")
st.markdown("법정동과 법규 위반 수치를 입력하면 AI가 위험도를 예측합니다.")

st.sidebar.header("📝 조건 입력")
year      = st.sidebar.selectbox("연도", list(range(2024, 2009, -1)))
dong_name = st.sidebar.selectbox("법정동", list(dong_options.keys()))
dong_code, lat, lng = dong_options[dong_name]
target    = st.sidebar.selectbox("사고 대상", target_options)

st.sidebar.markdown("---")
st.sidebar.subheader("🚗 법규 위반 수치 입력")
speeding   = st.sidebar.number_input("과속",                min_value=0, max_value=100, value=10)
center     = st.sidebar.number_input("중앙선 침범",          min_value=0, max_value=50,  value=2)
signal     = st.sidebar.number_input("신호위반",             min_value=0, max_value=100, value=10)
safe_dist  = st.sidebar.number_input("안전거리 미확보",      min_value=0, max_value=100, value=5)
duty       = st.sidebar.number_input("안전운전 의무 불이행", min_value=0, max_value=100, value=20)
pedestrian = st.sidebar.number_input("보행자 보호의무 위반", min_value=0, max_value=50,  value=3)
etc        = st.sidebar.number_input("기타",                 min_value=0, max_value=50,  value=1)

if st.sidebar.button("🔍 위험도 예측하기"):
    payload = {
        "year": year, "dong": dong_code, "target_name": target,
        "speeding": float(speeding), "center_line": float(center),
        "signal": float(signal), "safe_dist": float(safe_dist),
        "duty": float(duty), "pedestrian": float(pedestrian), "etc": float(etc)
    }

    with st.spinner("AI 분석 중... (최초 실행 시 1분 정도 소요될 수 있습니다)"):
        try:
            res = requests.post(API_URL, json=payload, timeout=120)
            result = res.json()
        except Exception as e:
            st.error(f"서버 연결 오류: {e}")
            st.stop()

    score  = result.get("위험지수_결과", 0)
    status = result.get("상태", "")
    shap   = result.get("SHAP_분석", {})

    # ── 1. 예측 결과 ──
    st.markdown("---")
    st.subheader(f"📊 {dong_name} 예측 결과")
    with st.container(border=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric(label="예측 위험지수", value=f"{score} 점")
        with col2:
            st.write("")
            if status == "위험":
                st.error("🚨 **위험 수준** : 단속 및 집중 관리가 필요한 지역입니다.")
            else:
                st.success("✅ **안전 수준** : 비교적 안전하게 관리되고 있는 지역입니다.")

    # ── 2. 지도 ──
    st.markdown("---")
    st.subheader("🗺️ 성남시 위험도 지도")
    st.caption("지도를 확대/축소하거나 마커를 클릭해 보세요.")
    m = folium.Map(location=[lat, lng], zoom_start=13, tiles="CartoDB positron")
    for name, (code, d_lat, d_lng) in dong_options.items():
        if name == dong_name:
            color = "red" if status == "위험" else "green"
            folium.Marker(
                [d_lat, d_lng],
                popup=f"<b>{name}</b><br>위험지수: {score}점",
                icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(m)
        else:
            folium.CircleMarker(
                [d_lat, d_lng], radius=6, color="#bdc3c7", fill=True, fill_color="#bdc3c7", popup=name
            ).add_to(m)
    st_folium(m, use_container_width=True, height=400)

    # ── 3. SHAP Waterfall ──
    if shap:
        st.markdown("---")
        st.subheader("🔍 위험도 원인 분석 (SHAP Waterfall)")
        st.caption("해당 지역의 위험도를 높인 요인(빨간색)과 낮춘 요인(초록색)을 분석합니다.")
        fig = go.Figure(go.Waterfall(
            name="위험도 분석",
            orientation="v",
            measure=["relative"] * len(shap),
            x=list(shap.keys()),
            textposition="outside",
            text=[f"{v:+.1f}" for v in shap.values()],
            y=list(shap.values()),
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#2ecc71"}},
            increasing={"marker": {"color": "#e74c3c"}},
            totals={"marker": {"color": "#34495e"}}
        ))
        fig.update_layout(
            showlegend=False,
            height=450,
            margin=dict(l=20, r=20, t=30, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
        st.plotly_chart(fig, use_container_width=True)
