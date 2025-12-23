# Snowbot 통합 대시보드

## 개요
Snowbot 주식 자동매매 시스템의 통합 대시보드 Web UI입니다. 이 대시보드를 통해 매수 대상 종목, 분할 매수 진행 현황, 보유 종목 수익률, 트레이딩 설정을 한눈에 확인할 수 있습니다.

## 기술 스택
- **Backend**: Spring Boot 3.1.7
- **Template Engine**: Thymeleaf
- **Styling**: Bootstrap 5
- **Icons**: Font Awesome 6.4.0
- **Database**: Oracle (JPA)

## 주요 기능

### 1. 매수 대상 종목 조회 (Scoring Result)
- 스코어링 로직에 의해 선정된 매수 후보군을 표시합니다.
- 표시 정보: 순위, 종목코드, 종목명, 스코어링 점수, 현재가, 선정 일자

### 2. 현재 분할 매수 진행 종목 (Buying Process)
- 현재 매수 로직이 동작 중이며, 아직 목표 수량을 다 채우지 못한 종목을 표시합니다.
- 표시 정보: 종목명, 현재 모은 수량, 목표 수량, 진행률(%), 평균단가, 현재가
- 진행률은 Progress Bar로 시각화됩니다.

### 3. 보유 현황 및 수익률 (Portfolio & Profit)
- 매수가 완료되었거나 분할 매수 중인 종목의 전체 수익률을 확인합니다.
- 표시 정보: 종목명, 평균단가, 현재가, 보유수량, 평가금액, 평가손익(금액), 수익률(%)
- **수익률 색상**: 양수(+) = 빨간색, 음수(-) = 파란색

### 4. 트레이딩 설정 관리 (Settings)
- `application.yml`에 정의된 매매 전략 변수들을 화면에서 확인할 수 있습니다.
- 주요 설정값:
  - **기본 설정**: 1회 매수 비율, 종목당 최대 보유 한도, 최대 보유 종목 수
  - **매수 설정**: 매수 로직 동작 여부, 강제 매수 테스트 플래그
  - **매도 설정**: 익절 기준, 손절 기준, 손절 기능 사용 여부, 매도 보류 비율, 강제 매도 테스트

## 설치 및 실행

### 1. 의존성 설치
프로젝트에 이미 Thymeleaf 의존성이 추가되어 있습니다 (`build.gradle`):

```gradle
implementation 'org.springframework.boot:spring-boot-starter-thymeleaf'
```

### 2. Gradle 빌드
```bash
./gradlew clean build
```

### 3. 애플리케이션 실행
```bash
./gradlew bootRun
```

또는

```bash
java -jar build/libs/snowbot-0.0.1-SNAPSHOT.jar
```

### 4. 대시보드 접속
브라우저에서 다음 URL로 접속합니다:

```
http://localhost:8080/dashboard
```

## REST API 엔드포인트

대시보드는 다음과 같은 REST API 엔드포인트를 제공합니다:

### GET /dashboard
- 대시보드 메인 페이지를 렌더링합니다.

### GET /dashboard/api/data
- 전체 대시보드 데이터를 JSON 형태로 반환합니다.

### GET /dashboard/api/scoring-results
- 매수 대상 종목 목록을 JSON 형태로 반환합니다.
- Query Parameter: `date` (optional) - 조회 날짜 (YYYYMMDD)

### GET /dashboard/api/buying-processes
- 분할 매수 진행 종목 목록을 JSON 형태로 반환합니다.
- Query Parameter: `date` (optional) - 조회 날짜 (YYYYMMDD)

### GET /dashboard/api/portfolios
- 보유 현황 목록을 JSON 형태로 반환합니다.
- Query Parameter: `date` (optional) - 조회 날짜 (YYYYMMDD)

### GET /dashboard/api/settings
- 트레이딩 설정 정보를 JSON 형태로 반환합니다.

## 파일 구조

```
snowbot/
├── src/main/java/me/project/snowbot/
│   ├── controller/
│   │   └── DashboardController.java          # 대시보드 컨트롤러
│   ├── service/
│   │   └── DashboardService.java             # 대시보드 서비스
│   └── dto/
│       ├── DashboardDto.java                 # 통합 대시보드 DTO
│       ├── ScoringResultDto.java             # 매수 대상 종목 DTO
│       ├── BuyingProcessDto.java             # 분할 매수 진행 DTO
│       ├── PortfolioDto.java                 # 보유 현황 DTO
│       └── TradingSettingsDto.java           # 트레이딩 설정 DTO
└── src/main/resources/
    ├── templates/
    │   ├── dashboard.html                     # 대시보드 메인 페이지
    │   └── error.html                         # 에러 페이지
    └── static/
        └── css/
            └── dashboard.css                  # 커스텀 CSS
```

## 주요 기능 설명

### DashboardService
- 각 기능별 데이터를 조회하고 DTO로 변환하는 서비스 계층입니다.
- `application.yml`의 설정값을 `@Value` 어노테이션으로 주입받습니다.
- 스코어링 결과, 매수 진행 현황, 보유 종목 수익률을 계산합니다.

### DashboardController
- 대시보드 페이지를 렌더링하고 REST API를 제공합니다.
- Thymeleaf를 사용하여 서버 사이드 렌더링을 수행합니다.
- 에러 발생 시 error.html 페이지로 리다이렉트됩니다.

### Dashboard UI
- Bootstrap 5를 사용한 반응형 디자인
- 탭(Tab) 구조로 4가지 기능을 분리
- Font Awesome 아이콘으로 시각적 개선
- 실시간 시계 표시
- 수익률 색상 구분 (양수: 빨간색, 음수: 파란색)

## 설정 변경 방법

트레이딩 설정을 변경하려면 `src/main/resources/application.yml` 파일을 수정합니다:

```yaml
snowbot:
  trading:
    contract-rate: 0.1        # 1회 매수 시 예수금 대비 비율
    limit-price: 500000       # 종목당 최대 보유 한도 금액
    limit-cnt: 20             # 최대 보유 종목 수
    buy:
      use-yn: Y               # 매수 로직 동작 여부 (Y/N)
      test-force-buy: N       # 강제 매수 테스트 플래그
    sell:
      up-rate: 10.0           # 익절 기준 수익률 (%)
      down-rate: -20.0        # 손절 기준 수익률 (%)
      use-loss-cut: Y         # 손절 기능 사용 여부 (Y/N)
      hold-rate: 0.8          # 매도 보류 비율
      test-force-sell: N      # 강제 매도 테스트 플래그
```

설정 변경 후 애플리케이션을 재시작하세요.

## 스크린샷

대시보드는 다음과 같은 요소로 구성됩니다:
- **상단 요약 카드**: 보유 종목 수, 총 평가 금액, 평가 손익, 수익률
- **탭 메뉴**: 4가지 주요 기능 탭
- **테이블**: 각 탭별 상세 데이터 표시
- **설정 폼**: 트레이딩 전략 설정 확인

## 문제 해결

### 대시보드 접속 시 오류가 발생하는 경우
1. 데이터베이스 연결을 확인하세요.
2. `application.yml` 설정이 올바른지 확인하세요.
3. 애플리케이션 로그를 확인하세요.

### 데이터가 표시되지 않는 경우
1. 데이터베이스에 데이터가 존재하는지 확인하세요.
2. `CustomDateUtils.getToday()` 메서드가 올바른 날짜를 반환하는지 확인하세요.
3. 로그에서 에러 메시지를 확인하세요.

## 라이센스
이 프로젝트는 Snowbot 프로젝트의 일부입니다.

## 문의
프로젝트 관련 문의사항이 있으시면 이슈를 등록해주세요.
