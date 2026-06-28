import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.graph_objects as fgo
from datetime import datetime
import requests

# 1. 웹 페이지 기본 및 레이아웃 설정
st.set_page_config(page_title="장중 실시간 듀얼 이격도 진단기", layout="wide")

st.title("⚡ 실시간 현재가 반영 5-20 / 20-50 듀얼 이격도 진단 시스템")
st.markdown("정규장 중에는 **현재 시점의 실시간 가격**을 반영하여 5, 20, 50일 이평선 및 단기·중기 이격도를 즉시 재계산합니다.")
st.divider()

# 2. 장중 실시간 현재가를 가져오는 함수 (네이버 금융 API 활용)
def get_realtime_price(symbol):
    try:
        url = f"https://polling.finance.naver.com/api/realtime/site/domestic/index/{symbol}" if symbol == 'KS11' else f"https://polling.finance.naver.com/api/realtime/site/domestic/stock/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers).json()
        return float(res['result']['areas'][0]['datas'][0]['nv'])
    except:
        return None

# 3. 데이터 수집 및 이평선/이격도 실시간 연산 함수
def get_live_processed_data(symbol, name):
    df = fdr.DataReader(symbol, '2025-01-01')
    now_price = get_realtime_price(symbol)
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    if now_price is not None:
        if today_date in df.index.strftime('%Y-%m-%d'):
            df.loc[df.index.strftime('%Y-%m-%d') == today_date, 'Close'] = now_price
        else:
            new_row = pd.DataFrame({'Close': [now_price]}, index=[pd.to_datetime(today_date)])
            df = pd.concat([df, new_row])
            
    # 이동평균선 계산
    df['5일선'] = df['Close'].rolling(window=5).mean()
    df['20일선'] = df['Close'].rolling(window=20).mean()
    df['50일선'] = df['Close'].rolling(window=50).mean()
    
    # ★ 이격도 산출 (%)
    df['이격도_5_20'] = (df['5일선'] / df['20일선']) * 100
    df['이격도_20_50'] = (df['20일선'] / df['50일선']) * 100  # 20-50일 이격도 추가
    return df, now_price

# 데이터 계산 구동
try:
    with st.spinner("최신 장중 실시간 데이터를 연산하는 중입니다..."):
        kospi_df, k_now = get_live_processed_data('KS11', '코스피')
        sam_df, s_now = get_live_processed_data('005930', '삼성전자')
        
    k_today = kospi_df.iloc[-1]
    s_today = sam_df.iloc[-1]

    # 4. 상단 대시보드 현황판 (20-50일 이격도 지표 대폭 보강)
    st.subheader(f"📊 현재가 기준 핵심 지표 현황 ({datetime.now().strftime('%H:%M:%S')} 실시간)")
    
    # 코스피 현황판
    k_col1, k_col2, k_col3 = st.columns(3)
    with k_col1:
        st.metric(label="🏛️ 코스피 현재가", value=f"{k_now:.2f}" if k_now else f"{k_today['Close']:.2f}")
    with k_col2:
        st.metric(label="🏛️ KOSPI 단기이격 (5-20)", value=f"{k_today['이격도_5_20']:.1f}%")
    with k_col3:
        st.metric(label="🏛️ KOSPI 중기이격 (20-50)", value=f"{k_today['이격도_20_50']:.1f}%")
        
    # 삼성전자 현황판
    s_col1, s_col2, s_col3 = st.columns(3)
    with s_col1:
        st.metric(label="📱 삼성전자 현재가", value=f"{s_now:,.0f}원" if s_now else f"{s_today['Close']:,.0f}원")
    with s_col2:
        st.metric(label="📱 삼전 단기이격 (5-20)", value=f"{s_today['이격도_5_20']:.1f}%")
    with s_col3:
        st.metric(label="📱 삼전 중기이격 (20-50)", value=f"{s_today['이격도_20_50']:.1f}%")

    st.divider()

    # 5. 핵심 종합 판단 및 개별 이격도 진단문구 출력
    st.subheader("🚨 현재가 기준 매수 타이밍 및 추세 진단")
    
    k_5_20 = k_today['이격도_5_20']
    k_20_50 = k_today['이격도_20_50']
    
    s_5_20 = s_today['이격도_5_20']
    s_20_50 = s_today['이격도_20_50']
    
    # 이격도 개별 자산 종합 평가 함수
    def 세부_평가_텍스트_생성(i_5_20, i_20_50):
        txt = ""
        # 1) 단기 이격(5-20) 평가
        if 100.0 <= i_5_20 <= 103.0:
            txt += "🔸 **단기(5-20):** 🟢 [적정] 강세장 속 눌림목 구간\n\n"
        elif i_5_20 > 103.0:
            txt += "🔸 **단기(5-20):** 🟡 [과열] 단기 급등 구간 (추격 금지)\n\n"
        else:
            txt += "🔸 **단기(5-20):** 🔴 [추세이탈] 단기 하락세 강함\n\n"
            
        # 2) 중기 이격(20-50) 평가
        if 100.0 <= i_20_50 <= 103.5:
            txt += "🔸 **중기(20-50):** 🔵 [정배열 안정] 중기 추세 든든하게 지지 중"
        elif i_20_50 > 103.5:
            txt += "🔸 **중기(20-50):** ⚠️ [중기 과열] 중기적으로도 꽤 많이 올라온 자리"
        else:
            txt += "🔸 **중기(20-50):** 📉 [역배열 위험] 20일선이 50일선 밑으로 꺾임 (주의)"
            
        return txt

    kospi_status = 세부_평가_텍스트_생성(k_5_20, k_20_50)
    samsung_status = 세부_평가_텍스트_생성(s_5_20, s_20_50)

    # 종합 매수 신호 조건문 (단기 적정 + 중기도 정배열 안정 상태일 때)
    is_k_ok = (100.0 <= k_5_20 <= 103.0) and (k_20_50 >= 100.0)
    is_s_ok = (100.0 <= s_5_20 <= 103.0) and (s_20_50 >= 100.0)

    if is_k_ok and is_s_ok:
        st.success("🔥 **[강력 공통 매수 신호]** 코스피와 삼성전자가 모두 단기 눌림목 안착 및 중기 정배열 지지를 받고 있습니다. 매수하기 아주 좋은 타이밍입니다!")
    elif (k_5_20 > 103.0) or (s_5_20 > 103.0):
        st.warning("⚠️ **[진단 결과: 관망 (단기 과열)]** 주가가 20일선 위로 너무 벌어져 있습니다. 지금 사면 물리기 쉬우니 단기 숨고르기를 기다리세요.")
    elif (k_5_20 < 100.0) or (s_5_20 < 100.0):
        st.error("📉 **[진단 결과: 관망 (단기 추세 이탈)]** 5일선이 20일선 밑으로 꺾였습니다. 단기 매도세가 강하니 바닥 확인 후 진입하세요.")
    else:
        st.info("📊 **[진단 결과: 보통]** 지수와 종목 간의 숨고르기 장세입니다.")

    # 각 자산별 세부 상태 라벨 출력
    st.markdown("#### 🔍 자산별 단기·중기 이격 상태 상세")
    box_col1, box_col2 = st.columns(2)
    with box_col1:
        st.info(f"🏛️ **코스피 지수 현황**\n\n{kospi_status}\n\n*(5-20일: {k_5_20:.1f}% / 20-50일: {k_20_50:.1f}%)*")
    with box_col2:
        st.info(f"📱 **삼성전자 종목 현황**\n\n{samsung_status}\n\n*(5-20일: {s_5_20:.1f}% / 20-50일: {s_20_50:.1f}%)*")

    st.divider()

    # 6. 차트 시각화
    st.subheader("📈 현재가가 포함된 이평선 차트")
    tab1, tab2 = st.tabs(["🏛️ 코스피 지수 차트", "📱 삼성전자 차트"])
    
    with tab1:
        fig_k = fgo.Figure()
        fig_k.add_trace(fgo.Scatter(x=kospi_df.index, y=kospi_df['Close'], name='현재가(종가)', line=dict(color='#1f77b4', width=2.5)))
        fig_k.add_trace(fgo.Scatter(x=kospi_df.index, y=kospi_df['5일선'], name='5일선', line=dict(color='#e31a1c', width=1.2)))
        fig_k.add_trace(fgo.Scatter(x=kospi_df.index, y=kospi_df['20일선'], name='20일선', line=dict(color='#33a02c', width=1.5)))
        fig_k.add_trace(fgo.Scatter(x=kospi_df.index, y=kospi_df['50일선'], name='50일선', line=dict(color='#ff7f00', width=1.5)))
        fig_k.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_k, use_container_width=True)
        
    with tab2:
        fig_s = fgo.Figure()
        fig_s.add_trace(fgo.Scatter(x=sam_df.index, y=sam_df['Close'], name='현재가(종가)', line=dict(color='#1f77b4', width=2.5)))
        fig_s.add_trace(fgo.Scatter(x=sam_df.index, y=sam_df['5일선'], name='5일선', line=dict(color='#e31a1c', width=1.2)))
        fig_s.add_trace(fgo.Scatter(x=sam_df.index, y=sam_df['20일선'], name='20일선', line=dict(color='#33a02c', width=1.5)))
        fig_s.add_trace(fgo.Scatter(x=sam_df.index, y=sam_df['50일선'], name='50일선', line=dict(color='#ff7f00', width=1.5)))
        fig_s.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_s, use_container_width=True)

except Exception as e:
    st.error(f"데이터를 처리하는 중 오류가 발생했습니다: {e}")