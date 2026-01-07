# 📈 SnowBot (Python)

Python + Streamlit 기반의 주식 자동매매 시스템입니다.

## 주요 기능

### 1. 데이터 수집
- OpenDart API를 통한 종목 정보 수집
- 재무제표 및 재무비율 수집
- KOSPI/KOSDAQ 시장 선택 가능

### 2. 종목 평가
- 재무 점수 (매출성장률, ROE, 부채비율, 유보율)
- 추세 점수 (이동평균선 배열)
- 가격 점수 (52주 고저 대비)
- 수급 점수 (외국인/기관 매수)
- 밸류에이션 (PER, PBR)
- 기술지표 (RSI, OBV)

### 3. 시뮬레이션 매매
- 가상 계좌 운영
- 수수료/세금 반영
- 매수/매도 이력 관리

### 4. 스케줄 관리
- Cron 기반 스케줄링
- 데이터 수집, 평가, 자동매매 스케줄

## 기술 스택

- **UI**: Streamlit
- **데이터**: OpenDartReader, yfinance
- **DB**: SQLite (로컬), Oracle ATP (클라우드)
- **스케줄러**: APScheduler
- **ORM**: SQLAlchemy

## 설치

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

## 실행

```bash
# Streamlit 앱 실행
streamlit run main.py
```

## 프로젝트 구조

```
stock_trading/
├── main.py                 # Streamlit 메인 앱
├── requirements.txt        # 의존성 패키지
├── config/
│   ├── settings.py        # 설정 관리
│   └── database.py        # DB 모델 및 연결
├── data/
│   ├── dart_collector.py  # OpenDart 데이터 수집
│   ├── price_fetcher.py   # 가격 데이터 조회
│   └── evaluator.py       # 종목 평가
├── trading/
│   ├── simulator.py       # 시뮬레이션 엔진
│   └── strategy.py        # 매매 전략
├── scheduler/
│   └── task_manager.py    # 스케줄러
├── ui/
│   ├── dashboard.py       # 대시보드
│   ├── settings_page.py   # 설정 페이지
│   ├── trading_page.py    # 매매 페이지
│   ├── manual_run.py      # 수동 실행
│   └── schedule_page.py   # 스케줄 관리
└── utils/
    └── logger.py          # 로깅
```

## 설정

### API 키 설정
1. [OpenDart](https://opendart.fss.or.kr/)에서 API 키 발급
2. 설정 > API 키에서 입력

### 데이터베이스 설정
- **로컬**: SQLite 자동 생성
- **클라우드**: Oracle ATP 연결 정보 입력

### 트레이딩 설정
- 1회 매수 비율: 예수금 대비 비율
- 종목당 한도: 개별 종목 최대 투자금
- 익절/손절선: 자동 매도 기준

## 사용법

### 1. 데이터 수집
```
수동 실행 > 데이터 수집 실행
```

### 2. 종목 평가
```
수동 실행 > 종목 평가 실행
```

### 3. 매매
```
매매 > 종목 분석 또는 매수/매도
```

### 4. 스케줄 설정
```
스케줄 관리 > 스케줄 추가
```

## 주의사항

⚠️ **이 시스템은 교육 및 연구 목적으로 제작되었습니다.**

- 실제 투자에 사용 시 손실이 발생할 수 있습니다.
- 투자 결정은 본인 책임입니다.
- 실거래 모드 사용 시 증권사 API 연동이 필요합니다.

## 라이선스

MIT License
