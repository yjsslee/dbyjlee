import os
from typing import Any

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="키움 모의투자 보유종목 대시보드", page_icon="📈", layout="wide")

BASE_URL = "https://mockapi.kiwoom.com"
TOKEN_URL = f"{BASE_URL}/oauth2/token"

# 국내주식 계좌평가현황 조회 TR
HOLDINGS_URL = f"{BASE_URL}/api/dostk/acnt"
HOLDINGS_API_ID = "kt00004"

st.title("📈 키움증권 모의투자 보유종목 대시보드")
st.caption("모의투자 계좌의 보유종목과 계좌 평가정보를 조회합니다.")


def get_credentials():
    """Streamlit secrets 또는 환경변수에서 API 인증정보를 읽습니다."""
    try:
        app_key = st.secrets.get("KIWOOM_APP_KEY", "")
        app_secret = st.secrets.get("KIWOOM_APP_SECRET", "")
    except Exception:
        app_key, app_secret = "", ""

    app_key = app_key or os.getenv("KIWOOM_APP_KEY", "")
    app_secret = app_secret or os.getenv("KIWOOM_APP_SECRET", "")
    return app_key, app_secret


def issue_token(app_key: str, app_secret: str) -> str:
    response = requests.post(
        TOKEN_URL,
        json={
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_secret,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    token = data.get("token") or data.get("access_token")
    if not token:
        raise RuntimeError(f"접근토큰 발급 실패: {data}")
    return token


def as_number(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).replace(",", "").replace("+", "").strip()
    if text in {"", "-"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def get_holdings(token: str, account_no: str) -> dict:
    """키움 REST API의 계좌평가현황을 조회합니다."""
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": HOLDINGS_API_ID,
    }

    # API 명세의 입력 필드는 버전에 따라 일부가 추가될 수 있으므로
    # 대표적인 계좌평가현황 조회 필드를 사용합니다.
    body = {
        "qry_tp": "1",
        "dmst_stex_tp": "KRX",
        "acnt_no": account_no,
    }

    response = requests.post(HOLDINGS_URL, headers=headers, json=body, timeout=20)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and data.get("return_code") not in (None, 0, "0"):
        raise RuntimeError(data.get("return_msg", str(data)))
    return data


def find_list(data: dict) -> list:
    """응답에서 보유종목 배열을 유연하게 찾습니다."""
    candidates = [
        "stk_acnt_evlt_prst",
        "acnt_evlt_prst",
        "output",
        "list",
    ]
    for key in candidates:
        value = data.get(key)
        if isinstance(value, list):
            return value
    for value in data.values():
        if isinstance(value, list):
            return value
    return []


def make_dataframe(items: list) -> pd.DataFrame:
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "종목코드": item.get("stk_cd", item.get("code", "")),
                "종목명": item.get("stk_nm", item.get("name", "")),
                "보유수량": as_number(item.get("hldg_qty", item.get("hold_qty", 0))),
                "매입가": as_number(item.get("buy_uv", item.get("pchs_avg_pric", 0))),
                "현재가": as_number(item.get("cur_prc", item.get("current_price", 0))),
                "평가금액": as_number(item.get("evlt_amt", item.get("eval_amt", 0))),
                "매입금액": as_number(item.get("pchs_amt", item.get("purchase_amt", 0))),
                "평가손익": as_number(item.get("evltv_prft", item.get("eval_profit", 0))),
                "수익률(%)": as_number(item.get("prft_rt", item.get("profit_rate", 0))),
            }
        )
    return pd.DataFrame(rows)


app_key, app_secret = get_credentials()

with st.sidebar:
    st.header("🔐 연결 설정")
    account_no = st.text_input("모의투자 계좌번호", type="password", help="계좌번호는 GitHub에 저장하지 마세요.")
    st.info("App Key / App Secret은 GitHub 코드에 직접 넣지 않고 Streamlit Secrets에 저장하세요.")
    refresh = st.button("🔄 보유종목 조회", type="primary", use_container_width=True)

if not app_key or not app_secret:
    st.warning("Streamlit Secrets에 KIWOOM_APP_KEY와 KIWOOM_APP_SECRET을 등록해 주세요.")
    st.code('KIWOOM_APP_KEY = "모의투자_APP_KEY"\nKIWOOM_APP_SECRET = "모의투자_APP_SECRET"')
    st.stop()

if not account_no:
    st.info("왼쪽에 모의투자 계좌번호를 입력한 후 '보유종목 조회'를 눌러주세요.")
    st.stop()

if refresh or "kiwoom_data" not in st.session_state:
    try:
        with st.spinner("키움증권 모의투자 서버에서 데이터를 조회하는 중입니다..."):
            token = issue_token(app_key, app_secret)
            st.session_state.kiwoom_data = get_holdings(token, account_no)
    except requests.HTTPError as exc:
        st.error(f"키움 API HTTP 오류: {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"조회 중 오류가 발생했습니다: {exc}")
        st.stop()

data = st.session_state.kiwoom_data
items = find_list(data)
df = make_dataframe(items)

# 응답에 전체 계좌 요약값이 존재하면 사용하고, 없으면 보유종목 데이터로 계산합니다.
total_purchase = sum(df["매입금액"]) if not df.empty else 0
total_eval = sum(df["평가금액"]) if not df.empty else 0
total_profit = sum(df["평가손익"]) if not df.empty else 0
profit_rate = total_profit / total_purchase * 100 if total_purchase else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("보유종목 수", f"{len(df):,}개")
c2.metric("총 매입금액", f"{total_purchase:,.0f}원")
c3.metric("총 평가금액", f"{total_eval:,.0f}원")
c4.metric("평가손익", f"{total_profit:,.0f}원", f"{profit_rate:.2f}%")

st.subheader("보유종목")
if df.empty:
    st.info("보유종목 데이터가 없습니다. 계좌번호와 모의투자 API 설정을 확인해 주세요.")
else:
    display_df = df.copy()
    for col in ["보유수량", "매입가", "현재가", "평가금액", "매입금액", "평가손익"]:
        display_df[col] = display_df[col].map(lambda x: f"{x:,.0f}")
    display_df["수익률(%)"] = df["수익률(%)"].map(lambda x: f"{x:.2f}%")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    chart_df = df[["종목명", "평가금액"]].copy().set_index("종목명")
    st.subheader("종목별 평가금액")
    st.bar_chart(chart_df)

with st.expander("API 원본 응답 보기"):
    st.json(data)

st.caption("※ 본 프로그램은 조회 전용 대시보드입니다. 주문 기능은 포함하지 않습니다.")
