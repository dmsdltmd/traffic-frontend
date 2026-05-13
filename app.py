import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

# 나눔고딕 폰트 적용
font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
try:
    fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = fm.FontProperties(fname=font_path).get_name()
except:
    pass
plt.rcParams['axes.unicode_minus'] = False

API_URL = "https://seongnam-api.onrender.com/predict"

# 🟢 법정동별 안전 기준선(평균치) 세팅
dong_baselines = {
    "수진1동": {'과속': 4, '중앙선 침범': 3, '신호위반': 15, '안전거리': 5, '안전운전': 30, '보행자': 3, '기타': 1},
    "수진2동": {'과속': 2, '중앙선 침범': 1, '신호위반': 8,  '안전거리': 3, '안전운전': 20, '보행자': 1, '기타': 0},
    "신흥1동": {'과속': 6, '중앙선 침범': 4, '신호위반': 20, '안전거리': 7, '안전운전': 40, '보행자': 5, '기타': 2},
    "신흥2동": {'과속': 5, '중앙선 침범': 2, '신호위반': 18, '안전거리': 6, '안전운전': 35, '보행자': 4, '기타': 1},
    "신흥3동": {'과속': 3, '중앙선 침범': 1, '신호위반': 12, '안전거리': 4, '안전운전': 25, '보행자': 2, '기타': 1},
    "단대동":  {'과속': 7, '중앙선 침범': 5, '신호위반': 22, '안전거리': 8, '안전운전': 45, '보행자': 6, '기타': 3},
    "은행동":  {'과속': 4, '중앙선 침범': 2, '신호위반': 14, '안전거리': 5, '안전운전': 28, '보행자': 3, '기타': 1},
    "양지동":  {'과속': 2, '중앙선 침범': 1, '신호위반': 9,  '안전거리': 3, '안전운전': 18, '보행자': 1, '기타': 0},
    "태평1동": {'과속': 8, '중앙선 침범': 6, '신호위반': 25, '안전거리': 9, '안전운전': 50, '보행자': 7, '기타': 4},
    "태평2동": {'과속': 5, '중앙선 침범': 3, '신호위반': 16, '안전거리': 6, '안전운전': 32, '보행자': 4, '기타': 2},
    "태평3동": {'과속': 4, '중앙선 침범': 2, '신호위반': 13, '안전거리': 5, '안전운전': 27, '보행자': 3, '기타': 1},
    "태평4동": {'과속': 3, '중앙선 침범': 1, '신호위반': 10, '안전거리': 4, '안전운전': 22, '보행자': 2, '기타': 1},
}
default_baseline = {'과속': 4, '중앙선 침범': 3, '신호위반': 15, '안전거리': 5, '안전운전': 30, '보행자': 3, '기타': 1}

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

# 🟢 선택한 동의 평균값 불러오기
current_base = dong_baselines.get(dong_name, default_baseline)

target    = st.sidebar.selectbox("사고 대상", target_options)

st.sidebar.markdown("---")
st.sidebar.subheader("🚗 법규 위반 수치 입력")
speeding   = st.sidebar.number_input("과속",                min_value=0, max_value=100, value=current_base['과속'])
center     = st.sidebar.number_input("중앙선 침범",          min_value=0, max_value=50,  value=current_base['중앙선 침범'])
signal     = st.sidebar.number_input("신호위반",             min_value=0, max_value=100, value=current_base['신호위반'])
safe_dist  = st.sidebar.number_input("안전거리 미확보",      min_value=0, max_value=100, value=current_base['안전거리'])
duty       = st.sidebar.number_input("안전운전 의무 불이행", min_value=0, max_value=100, value=current_base['안전운전'])
pedestrian = st.sidebar.number_input("보행자 보호의무 위반", min_value=0, max_value=50,  value=current_base['보행자'])
etc        = st.sidebar.number_input("기타",                 min_value=0, max_value=50,  value=current_base['기타'])

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

    # ── 예측 결과 카드 ──
    st.markdown("---")
    st.subheader(f"📊 {dong_name} 예측 결과")
    with st.container(border=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric(label="예측 위험지수", value=f"{score} 점")
        with col2:
            st.write("")
            avg_check = {
                '과속': current_base['과속'],
                '중앙선 침범': current_base['중앙선 침범'],
                '신호위반': current_base['신호위반'],
                '안전거리 미확보': current_base['안전거리'],
                '안전운전 의무 불이행': current_base['안전운전']
            }
            current_check = {
                '과속': speeding, '중앙선 침범': center, '신호위반': signal,
                '안전거리 미확보': safe_dist, '안전운전 의무 불이행': duty
            }
            is_danger = any(current_check[k] > avg_check[k] for k in avg_check)

            if is_danger:
                st.error("🚨 **위험 수준** : 단속 및 집중 관리가 필요한 지역입니다.")
            else:
                st.success("✅ **안전 수준** : 비교적 안전하게 관리되고 있는 지역입니다.")

    # ── 탭 3개 ──
    tab1, tab2, tab3 = st.tabs(["🚦 실시간 위험도 분석", "📊 인공지능 판단 근거", "🔮 정책 시뮬레이터"])

    # ── 탭1: 지도 + SHAP ──
    with tab1:
        st.markdown("---")
        st.subheader("🗺️ 성남시 위험도 지도")
        st.caption("지도를 확대/축소하거나 마커를 클릭해 보세요.")
        m = folium.Map(
            location=[lat, lng], zoom_start=13,
            tiles="https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}&hl=ko",
            attr="Google Maps"
        )
        for name, (code, d_lat, d_lng) in dong_options.items():
            if name == dong_name:
                color = "red" if is_danger else "green"
                folium.Marker(
                    [d_lat, d_lng],
                    popup=f"<b>{name}</b><br>위험지수: {score}점",
                    icon=folium.Icon(color=color, icon="info-sign")
                ).add_to(m)
            else:
                folium.CircleMarker(
                    [d_lat, d_lng], radius=6, color="#bdc3c7",
                    fill=True, fill_color="#bdc3c7", popup=name
                ).add_to(m)
        st_folium(m, use_container_width=True, height=400, returned_objects=[])

        if shap:
            st.markdown("---")
            st.subheader("🔍 위험도 원인 분석 (SHAP Waterfall)")
            st.caption("해당 지역의 위험도를 높인 요인(빨간색)과 낮춘 요인(초록색)을 분석합니다.")
            fig = go.Figure(go.Waterfall(
                name="위험도 분석", orientation="v",
                measure=["relative"] * len(shap),
                x=list(shap.keys()),
                textposition="outside",
                text=[f"{v:+.1f}" for v in shap.values()],
                y=list(shap.values()),
                connector={"line": {"color": "rgba(0,0,0,0)"}},
                increasing={"marker": {"color": "#ef4444"}},
                decreasing={"marker": {"color": "#11CAA0"}},
                totals={"marker": {"color": "#34495e"}}
            ))
            fig.update_layout(
                showlegend=False, height=450,
                margin=dict(l=20, r=20, t=30, b=20),
                plot_bgcolor="rgba(0,0,0,0)",
            )
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            st.plotly_chart(fig, use_container_width=True)

    # ── 탭2: 방사형 차트 + 변수 중요도 ──
    with tab2:
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🕸️ 입력값 vs 기준값 비교")
            st.caption("빨간 영역이 파란 영역을 크게 벗어날수록 위험한 수치입니다.")
            categories  = ['과속', '중앙선 침범', '신호위반', '안전거리 미확보', '안전운전 의무 불이행']
            avg_values  = [current_base['과속'], current_base['중앙선 침범'], current_base['신호위반'], current_base['안전거리'], current_base['안전운전']]
            user_values = [speeding, center, signal, safe_dist, duty]

            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(
                r=avg_values, theta=categories, fill='toself',
                name='기준값', line_color='rgba(49, 130, 189, 1.0)'
            ))
            fig_r.add_trace(go.Scatterpolar(
                r=user_values, theta=categories, fill='toself',
                name='현재 입력값', line_color='rgba(227, 74, 51, 0.9)'
            ))
            fig_r.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, max(user_values + avg_values) + 10])),
                showlegend=True,
                title="기준값 vs 현재 입력값 비교",
                height=400,
                margin=dict(l=20, r=20, t=50, b=20)
            )
            st.plotly_chart(fig_r, use_container_width=True)

        with col2:
            st.subheader("📈 AI 핵심 판단 요인")
            st.caption("AI가 위험도를 계산할 때 가장 중요하게 본 변수입니다.")
            if shap:
                shap_df = pd.DataFrame({
                    "항목": list(shap.keys()),
                    "중요도": [abs(v) for v in shap.values()]
                }).sort_values("중요도", ascending=True)

                fig_i = go.Figure(go.Bar(
                    x=shap_df["중요도"],
                    y=shap_df["항목"],
                    orientation='h',
                    marker_color='teal'
                ))
                fig_i.update_layout(
                    title="AI 핵심 판단 요인",
                    height=400,
                    margin=dict(l=20, r=20, t=50, b=20),
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                fig_i.update_xaxes(showgrid=True, gridcolor='LightGray')
                st.plotly_chart(fig_i, use_container_width=True)
            else:
                st.info("예측 후 변수 중요도가 표시됩니다.")

    # ── 탭3: 정책 시뮬레이터 ──
    with tab3:
        st.markdown("---")
        st.markdown("### 🔮 교통안전 정책 시뮬레이터 (What-If Analysis)")
        st.caption("※ 기준: 사전 산출된 기준값 기반")

        avg_data = {
            '과속': current_base['과속'],
            '중앙선 침범': current_base['중앙선 침범'],
            '신호위반': current_base['신호위반'],
            '안전거리 미확보': current_base['안전거리'],
            '안전운전 의무 불이행': current_base['안전운전']
        }
        current_data = {
            '과속': speeding, '중앙선 침범': center, '신호위반': signal,
            '안전거리 미확보': safe_dist, '안전운전 의무 불이행': duty
        }

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📊 현재 입력값 vs 안전 기준선")
            st.caption("빨간 영역이 파란 기준선을 벗어날수록 정책 개입이 필요한 수치입니다.")
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatterpolar(
                r=list(avg_data.values()), theta=list(avg_data.keys()), fill='toself',
                name='안전 기준선', line_color='rgba(49, 130, 189, 0.7)'
            ))
            fig_s.add_trace(go.Scatterpolar(
                r=list(current_data.values()), theta=list(current_data.keys()), fill='toself',
                name='현재 시뮬레이션 수치', line_color='rgba(227, 74, 51, 0.9)'
            ))
            fig_s.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                showlegend=True,
                height=400,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_s, use_container_width=True)

        with col2:
            st.subheader("💡 정책 제안")
            st.caption("현재 입력값 기준으로 평균을 초과한 항목입니다.")
            exceeded = {k: v for k, v in current_data.items() if v > avg_data[k]}
            if exceeded:
                for item, val in exceeded.items():
                    avg = avg_data[item]
                    diff = val - avg
                    st.warning(
                        f"⚠️ **{item}** : 현재 **{val}건** (평균 {avg}건 대비 **+{diff}건 초과**)\n\n"
                        f"안전 기준선으로 돌아가려면 **최소 {diff}건의 추가 단속**이 필요합니다. "
                        f"집중 단속 및 주민 대상 교통안전 캠페인 시행을 권고합니다."
                    )
                st.error(
                    "🚨 **즉각적인 행정 조치가 필요합니다!**\n\n"
                    "위 항목들은 기준값을 초과한 위험 요인입니다. "
                    "한정된 예산을 해당 항목의 단속에 집중 투입하면 가장 효과적으로 위험도를 낮출 수 있습니다."
                )
            else:
                st.success(
                    "✅ **모든 항목이 기준값 이하입니다.**\n\n"
                    "현재 입력된 수치는 안전 기준선 범위 내에 있습니다. "
                    "지속적인 모니터링을 통해 현재의 안전 수준을 유지하시기 바랍니다."
                )
