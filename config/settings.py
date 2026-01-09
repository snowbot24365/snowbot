"""
설정 관리 모듈
- 환경별(Local/Production) 설정 분리
- Streamlit session_state 연동
- JSON 파일 기반 영구 저장
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

# 설정 파일 경로
CONFIG_DIR = Path(__file__).parent.parent / "config_data"
CONFIG_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = CONFIG_DIR / "settings.json"


class Environment(Enum):
    """실행 환경 구분"""
    LOCAL = "local"
    PRODUCTION = "production"


class ExecutionMode(Enum):
    """실행 모드 구분"""
    SIMULATION = "simulation"
    REAL_TRADING = "real_trading"


@dataclass
class APISettings:
    """API 관련 설정"""
    opendart_api_key: str = ""
    
    # KRX API (종목 목록 조회용)
    krx_api_key: str = ""
    
    # KIS(한국투자증권) API - 모의투자
    kis_mock_app_key: str = ""
    kis_mock_app_secret: str = ""
    kis_mock_account_no: str = ""
    kis_mock_account_cd: str = "01"
    
    # KIS(한국투자증권) API - 실전투자
    kis_real_app_key: str = ""
    kis_real_app_secret: str = ""
    kis_real_account_no: str = ""
    kis_real_account_cd: str = "01"
    
    # KIS API 사용 모드 - 데이터 수집용 ("mock" 또는 "real")
    kis_api_mode: str = "mock"
    
    # KIS 거래 계좌 모드 ("mock" 또는 "real")
    kis_trading_account_mode: str = "mock"
    
    # 실전투자 동의 여부
    kis_real_confirmed: bool = False


@dataclass
class DatabaseSettings:
    """데이터베이스 연결 설정"""
    # 데이터베이스 유형 ("sqlite" 또는 "oracle")
    db_type: str = "sqlite"
    
    # Local (SQLite)
    sqlite_path: str = "stock_data.db"
    
    # Production (Oracle ATP)
    oracle_user: str = ""
    oracle_password: str = ""
    oracle_dsn: str = ""
    oracle_wallet_path: str = ""


@dataclass
class CollectionSettings:
    """데이터 수집 설정"""
    # 시장 선택
    collect_kospi: bool = True
    collect_kosdaq: bool = True
    
    # 종목 개수 설정 (0 = 전체)
    kospi_top_n: int = 0
    kosdaq_top_n: int = 0
    random_n_stocks: int = 10  # 무작위 N개 종목 수집 (테스트용)
    
    # 수집 모드: "all" (전체) 또는 "random_n" (무작위 N개)
    collection_mode: str = "random_n"
    
    # 재시도 설정
    max_retries: int = 3
    retry_delay_seconds: int = 5


@dataclass
class TradingSettings:
    """트레이딩 설정"""
    # 매수 설정
    buy_enabled: bool = False  # 매수 기능 활성화
    buy_rate: float = 10.0  # 1회 매수 비율 (총 투자금 대비 %)
    max_buy_amount: int = 500000  # 종목당 최대 매수 금액 (원)
    limit_count: int = 10  # 최대 보유 종목 수
    
    # 매도 설정
    sell_up_rate: float = 10.0  # 익절 기준 (%)
    sell_down_rate: float = -20.0  # 손절 기준 (%)
    use_loss_cut: bool = True  # 손절 기능 사용
    sell_hold_rate: float = 80.0  # 매도 보류 비율 (최대매수금액의 N% 도달 전 매도 제외)
    
    # 트레일링 스탑
    trailing_stop_enabled: bool = False  # 트레일링 스탑 사용
    trailing_stop_rate: float = 5.0  # 트레일링 스탑 비율 (%)
    
    # 시뮬레이션 설정
    initial_balance: int = 10000000  # 가상 계좌 초기 잔고
    apply_fee: bool = True  # 수수료 적용
    fee_rate: float = 0.00015  # 수수료율 (0.015%)
    tax_rate: float = 0.0023  # 세금율 (0.23%)


@dataclass
class EvaluationSettings:
    """종목 평가 기준 설정"""
    # 최소 점수 기준
    min_total_score: int = 30
    
    # 8가지 지표별 가중치 (기본 1.0)
    weight_sheet: float = 1.0    # 1. 재무제표 점수 가중치
    weight_trend: float = 1.0    # 2. 주가 모멘텀 점수 가중치
    weight_price: float = 1.0    # 3. 주가 점수 가중치
    weight_kpi: float = 1.0      # 4. 보조지표 점수 가중치 (RSI/OBV)
    weight_buy: float = 1.0      # 5. 수급 점수 가중치
    weight_avls: float = 1.0     # 6. 시가총액 점수 가중치
    weight_per: float = 1.0      # 7. PER 점수 가중치
    weight_pbr: float = 1.0      # 8. PBR 점수 가중치


@dataclass
class ScheduleItem:
    """스케줄 항목"""
    id: str = ""
    name: str = ""
    task_type: str = ""  # data_collection, evaluation
    cron_expression: str = ""
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleItem':
        return cls(**data)


@dataclass
class ScheduleSettings:
    """스케줄 설정"""
    schedules: List[ScheduleItem] = field(default_factory=list)
    
    def add_schedule(self, schedule: ScheduleItem):
        self.schedules.append(schedule)
    
    def remove_schedule(self, schedule_id: str):
        self.schedules = [s for s in self.schedules if s.id != schedule_id]
    
    def get_schedule(self, schedule_id: str) -> Optional[ScheduleItem]:
        for s in self.schedules:
            if s.id == schedule_id:
                return s
        return None
    
    def update_schedule(self, schedule: ScheduleItem):
        for i, s in enumerate(self.schedules):
            if s.id == schedule.id:
                self.schedules[i] = schedule
                return
        self.add_schedule(schedule)


@dataclass
class AppSettings:
    """애플리케이션 전체 설정"""
    environment: str = Environment.LOCAL.value
    execution_mode: str = ExecutionMode.SIMULATION.value
    
    api: APISettings = field(default_factory=APISettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    collection: CollectionSettings = field(default_factory=CollectionSettings)
    trading: TradingSettings = field(default_factory=TradingSettings)
    evaluation: EvaluationSettings = field(default_factory=EvaluationSettings)
    schedule: ScheduleSettings = field(default_factory=ScheduleSettings)
    
    # 메타데이터
    last_updated: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        data = {
            "environment": self.environment,
            "execution_mode": self.execution_mode,
            "api": asdict(self.api),
            "database": asdict(self.database),
            "collection": asdict(self.collection),
            "trading": asdict(self.trading),
            "evaluation": asdict(self.evaluation),
            "schedule": {
                "schedules": [s.to_dict() for s in self.schedule.schedules]
            },
            "last_updated": self.last_updated
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppSettings':
        """딕셔너리에서 설정 객체 생성"""
        settings = cls()
        
        settings.environment = data.get("environment", Environment.LOCAL.value)
        settings.execution_mode = data.get("execution_mode", ExecutionMode.SIMULATION.value)
        
        if "api" in data:
            settings.api = APISettings(**data["api"])
        if "database" in data:
            settings.database = DatabaseSettings(**data["database"])
        if "collection" in data:
            settings.collection = CollectionSettings(**data["collection"])
        if "trading" in data:
            settings.trading = TradingSettings(**data["trading"])
        if "evaluation" in data:
            settings.evaluation = EvaluationSettings(**data["evaluation"])
        if "schedule" in data:
            schedules = [
                ScheduleItem.from_dict(s) 
                for s in data["schedule"].get("schedules", [])
            ]
            settings.schedule = ScheduleSettings(schedules=schedules)
        
        settings.last_updated = data.get("last_updated", "")
        
        return settings


class SettingsManager:
    """설정 관리자 - 싱글톤 패턴"""
    _instance: Optional['SettingsManager'] = None
    _settings: Optional[AppSettings] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._settings is None:
            self.load()
    
    @property
    def settings(self) -> AppSettings:
        """현재 설정 반환"""
        if self._settings is None:
            self.load()
        return self._settings
    
    def load(self) -> AppSettings:
        """파일에서 설정 로드"""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._settings = AppSettings.from_dict(data)
            except Exception as e:
                print(f"설정 파일 로드 오류: {e}")
                self._settings = AppSettings()
        else:
            self._settings = AppSettings()
            self.save()
        
        return self._settings
    
    def save(self):
        """설정을 파일에 저장"""
        self._settings.last_updated = datetime.now().isoformat()
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._settings.to_dict(), f, ensure_ascii=False, indent=2)
    
    def update(self, **kwargs):
        """설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        self.save()
    
    def update_api(self, **kwargs):
        """API 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._settings.api, key):
                setattr(self._settings.api, key, value)
        self.save()
    
    def update_database(self, **kwargs):
        """데이터베이스 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._settings.database, key):
                setattr(self._settings.database, key, value)
        self.save()
    
    def update_collection(self, **kwargs):
        """수집 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._settings.collection, key):
                setattr(self._settings.collection, key, value)
        self.save()
    
    def update_trading(self, **kwargs):
        """트레이딩 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._settings.trading, key):
                setattr(self._settings.trading, key, value)
        self.save()
    
    def update_evaluation(self, **kwargs):
        """평가 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self._settings.evaluation, key):
                setattr(self._settings.evaluation, key, value)
        self.save()
    
    def is_simulation_mode(self) -> bool:
        """시뮬레이션 모드 여부"""
        return self._settings.execution_mode == ExecutionMode.SIMULATION.value
    
    def is_local_environment(self) -> bool:
        """로컬 환경 여부"""
        return self._settings.environment == Environment.LOCAL.value
    
    def get_db_connection_string(self) -> str:
        """현재 환경에 맞는 DB 연결 문자열 반환"""
        db_type = self._settings.database.db_type
        
        if db_type == "sqlite":
            db_path = CONFIG_DIR / self._settings.database.sqlite_path
            return f"sqlite:///{db_path}"
        else:
            # Oracle ATP 연결 (oracledb 사용)
            dialect = "oracle+oracledb"
            
            return (
                f"{dialect}://{self._settings.database.oracle_user}:"
                f"{self._settings.database.oracle_password}@"
                f"{self._settings.database.oracle_dsn}"
            )


# 전역 설정 관리자 인스턴스
def get_settings() -> AppSettings:
    """현재 설정 반환"""
    return SettingsManager().settings


def get_settings_manager() -> SettingsManager:
    """설정 관리자 반환"""
    return SettingsManager()
