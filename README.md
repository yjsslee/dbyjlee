# 키움증권 모의투자 보유종목 대시보드

Streamlit에서 키움증권 REST API 모의투자 계좌의 보유종목 정보를 조회하는 대시보드입니다.

## 파일

- `app.py` : Streamlit 대시보드
- `requirements.txt` : 필요한 Python 패키지

## 보안 설정

App Key와 App Secret은 GitHub 코드에 직접 입력하지 않습니다.
Streamlit Cloud를 사용하는 경우 앱의 **Settings → Secrets**에 다음처럼 등록하세요.

```toml
KIWOOM_APP_KEY = "모의투자_APP_KEY"
KIWOOM_APP_SECRET = "모의투자_APP_SECRET"
```

계좌번호는 앱의 왼쪽 사이드바에서 직접 입력합니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 주의

키움증권의 모의투자 App Key/Secret은 실전투자용과 별도로 발급됩니다.
이 프로그램은 현재 조회 전용이며 주문 기능은 포함하지 않습니다.

키움 REST API는 모의투자 서버를 별도 도메인으로 제공하며 OAuth 2.0 방식으로 접근 토큰을 발급합니다.
