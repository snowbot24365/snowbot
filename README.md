# 📈 SnowBot (Python)

**SnowBot**은 Python과 Streamlit을 기반으로 구축된 **한국 주식(KOSPI/KOSDAQ) 자동매매 및 데이터 분석 시스템**입니다.
OpenDart를 통한 재무 데이터 분석과 한국투자증권(KIS) API를 이용한 실전/모의 투자를 지원하며, Oracle Cloud Database(ATP)를 연동하여 데이터를 안정적으로 관리합니다.

## ✨ 주요 기능

### 1. 📥 데이터 수집 (Data Collection)

* **KRX API**: KOSPI/KOSDAQ 전 종목 기본 정보 수집
* **OpenDart API**: 기업 재무제표(매출, 영업이익, 부채비율 등) 및 재무비율 수집
* **KIS API**: 실시간/일별 시세 데이터 수집
* **자동 관리**: 데이터 보관 주기에 따른 자동 정리 (최근 1개월 데이터 유지 등)

### 2. 📊 종목 평가 (Evaluation)

다양한 지표를 종합하여 종목별 점수(Score) 산출:

* **재무 점수**: 매출성장률, 영업이익률, 부채비율, 유보율, ROE 등
* **추세 점수**: 이동평균선(5/20/60일) 배열 및 이격도 분석
* **가격 점수**: 52주 신고가/신저가 대비 현재 위치
* **수급 점수**: 외국인/기관 순매수 추이
* **밸류에이션**: PER, PBR 저평가 여부

### 3. ⚡ 트레이딩 (Trading)

세 가지 실행 모드를 지원합니다:

1. **시뮬레이션 (Simulation)**: 가상 계좌를 이용한 백테스팅 및 전략 검증
2. **모의투자 (Mock)**: 한국투자증권 모의투자 API 연동
3. **실전투자 (Real)**: 한국투자증권 실계좌 API 연동

**매매 전략 기능:**

* **자금 관리**: 예수금 대비 매수 비율, 종목당 최대 매수금액 설정
* **익절/손절**: 목표 수익률 및 손절 제한선 설정
* **트레일링 스탑 (Trailing Stop)**: 고점 대비 하락 시 이익 실현 기능
* **분할 매수/매도**: (설정에 따라 지원 가능)

### 4. 🗓️ 스케줄 관리 (Scheduler)

* **APScheduler** 기반의 백그라운드 작업 수행
* 장 마감 후 데이터 자동 수집
* 매일 아침 종목 평가 및 매수 후보 선정
* 장 중 자동 매매 스케줄링 (Cron 표현식 지원)

---

## 🛠 기술 스택

* **Language**: Python 3.10+
* **Web Framework**: Streamlit
* **Database**:
* **Local**: SQLite
* **Cloud**: Oracle Autonomous Database (ATP) with `python-oracledb` (Thin Mode)


* **API**:
* **OpenDartReader**: 금융감독원 공시 데이터
* **KIS API**: 한국투자증권 트레이딩/시세
* **KRX**: 한국거래소 정보


* **ORM**: SQLAlchemy
* **Scheduler**: APScheduler

---

## 📂 프로젝트 구조

```bash
snowbot/
├── main.py                 # Streamlit 앱 진입점
├── requirements.txt        # 의존성 패키지 목록
├── config/                 # 설정 관리
│   ├── settings.py         # 환경 설정 (JSON 연동)
│   └── database.py         # DB 연결 및 SQLAlchemy 모델 정의
├── data/                   # 데이터 처리
│   ├── dart_collector.py   # Dart 재무 데이터 수집
│   ├── price_fetcher.py    # KIS 시세 조회
│   └── evaluator.py        # 종목 평가 알고리즘
├── trading/                # 트레이딩 로직
│   ├── simulator.py        # 시뮬레이션 엔진
│   ├── auto_trader.py      # KIS 실전/모의 투자 로직
│   └── strategy.py         # 매수/매도 전략 판단
├── scheduler/              # 작업 스케줄러
│   └── task_manager.py     # 스케줄 등록 및 관리
├── ui/                     # Streamlit UI 페이지
│   ├── dashboard.py        # 메인 대시보드
│   ├── trading_page.py     # 매매 현황
│   ├── settings_page.py    # 설정 화면
│   └── ...                 # 기타 기능별 페이지
└── utils/                  # 유틸리티
    └── logger.py           # 로깅 설정

```

---

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
# Repository Clone
git clone https://github.com/username/snowbot.git
cd snowbot

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate      # Mac/Linux
.\venv\Scripts\activate       # Windows

# 패키지 설치
pip install -r requirements.txt

```

### 2. 설정 파일 준비

`config_data/` 폴더 내에 `settings.json` 파일이 생성됩니다. UI의 **설정 페이지**에서 입력하거나 파일을 직접 수정할 수 있습니다.

**필수 API 키:**

* **OpenDart API Key**: [OpenDart](https://opendart.fss.or.kr/) 발급
* **KRX API Key**: (선택) 데이터 수집용
* **KIS API (App Key/Secret)**: [한국투자증권 개발자센터](https://apiportal.koreainvestment.com/) 발급

### 3. 데이터베이스 설정

* **SQLite**: 별도 설정 없이 즉시 사용 가능 (`stock_data.db`)
* **Oracle ATP**:
1. Oracle Cloud에서 전자지갑(Wallet) 다운로드 및 압축 해제
2. `settings.json` 또는 UI에서 **Wallet 경로** 지정
3. `oracledb` Thin Mode를 통해 클라이언트 설치 없이 접속



### 4. 실행

```bash
streamlit run main.py

```

---

## ⚙️ 주요 설정 항목 (`settings.json`)

| 구분 | 항목 | 설명 |
| --- | --- | --- |
| **Execution** | `mode` | `simulation` (시뮬레이션) / `real_trading` (실전/모의) |
| **API** | `kis_api_mode` | `mock` (모의투자) / `real` (실전투자) |
| **Trading** | `buy_rate` | 1회 매수 시 예수금 대비 비율 (%) |
|  | `max_buy_amount` | 종목당 최대 매수 금액 |
|  | `sell_up_rate` | 익절 수익률 (%) |
|  | `sell_down_rate` | 손절 수익률 (%) |
|  | `trailing_stop` | 트레일링 스탑 사용 여부 및 감지율 (%) |
| **Evaluation** | `min_total_score` | 매수 후보 선정을 위한 최소 점수 |
|  | `weight_*` | 각 평가 항목별 가중치 조절 |

---

## ⚠️ 주의사항

1. **투자 책임**: 본 시스템은 알고리즘 학습 및 연구용으로 개발되었습니다. 실제 투자로 인한 손실의 책임은 전적으로 사용자에게 있습니다.
2. **API 제한**: OpenDart 및 KIS API의 호출 제한(초당/일일 횟수)을 준수해야 합니다.
3. **보안**: `settings.json` 및 Oracle Wallet 파일에는 민감한 정보가 포함되어 있으므로 **GitHub 등에 절대 업로드하지 마십시오.** (`.gitignore` 등록 필수)

---

## License

MIT License