"""
데이터베이스 연결 및 모델 정의
- SQLite (Local) / Oracle ATP (Production) 자동 전환
- Oracle Thin Mode 적용
- ORA-01400 해결: Sequence 객체 추가
"""

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, event,
    Boolean, BigInteger, Text, ForeignKey, Index, Date, Sequence # <--- Sequence 추가
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, Generator
import logging
import os

from config.settings import get_settings_manager

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============ 모델 정의 ============

class ItemMst(Base):
    """종목 마스터 테이블"""
    __tablename__ = 'item_mst'
    # 문자열 PK는 Sequence 불필요
    item_cd = Column(String(6), primary_key=True, comment='종목코드')
    base_date = Column(String(8), primary_key=True, comment='기준일자 (YYYYMMDD)')
    mrkt_ctg = Column(String(10), comment='시장구분 (KOSPI/KOSDAQ)')
    itms_nm = Column(String(200), comment='종목명')
    corp_nm = Column(String(200), comment='법인명')
    sector = Column(String(200), comment='섹터/업종')
    collect_source = Column(String(10), default=None, comment='수집구분 (manual/auto, NULL=미수집)')
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ItemPrice(Base):
    """일별 시세 테이블"""
    __tablename__ = 'item_price'
    # 문자열 PK는 Sequence 불필요
    item_cd = Column(String(6), primary_key=True) 
    trade_date = Column(String(8), primary_key=True, comment='거래일자 (YYYYMMDD)')
    stck_clpr = Column(Integer, comment='종가')
    stck_oprc = Column(Integer, comment='시가')
    stck_hgpr = Column(Integer, comment='고가')
    stck_lwpr = Column(Integer, comment='저가')
    acml_vol = Column(BigInteger, comment='누적거래량')
    acml_tr_pbmn = Column(BigInteger, comment='누적거래대금')
    prdy_vrss = Column(Integer, comment='전일대비')
    prdy_vrss_sign = Column(Integer, comment='전일대비부호')
    ma5 = Column(Float, comment='5일 이동평균')
    ma10 = Column(Float, comment='10일 이동평균')
    ma20 = Column(Float, comment='20일 이동평균')
    ma60 = Column(Float, comment='60일 이동평균')
    ma120 = Column(Float, comment='120일 이동평균')
    ma240 = Column(Float, comment='240일 이동평균')
    
    __table_args__ = (
        Index('idx_item_price_date', 'trade_date'),
    )

class ItemEquity(Base):
    """종목 기본 정보"""
    __tablename__ = 'item_equity'
    item_cd = Column(String(6), primary_key=True)
    bstp_kor_isnm = Column(String(100), comment='업종명')
    lstn_stcn = Column(BigInteger, comment='상장주수')
    hts_avls = Column(BigInteger, comment='시가총액')
    frgn_ntby_qty = Column(BigInteger, comment='외국인순매수수량')
    frgn_hldn_qty = Column(BigInteger, comment='외국인보유수량')
    hts_frgn_ehrt = Column(Float, comment='외국인소진율')
    pgtr_ntby_qty = Column(BigInteger, comment='프로그램순매수수량')
    w52_hgpr = Column(Integer, comment='52주최고가')
    w52_hgpr_date = Column(String(8), comment='52주최고가일자')
    w52_lwpr = Column(Integer, comment='52주최저가')
    w52_lwpr_date = Column(String(8), comment='52주최저가일자')
    stck_dryy_hgpr = Column(Integer, comment='연중최고가')
    stck_dryy_lwpr = Column(Integer, comment='연중최저가')
    dryy_hgpr_vrss_prpr_rate = Column(Float, comment='연중최고가대비현재가비율')
    dryy_lwpr_vrss_prpr_rate = Column(Float, comment='연중최저가대비현재가비율')
    per = Column(Float, comment='PER')
    pbr = Column(Float, comment='PBR')
    eps = Column(Float, comment='EPS')
    bps = Column(Float, comment='BPS')
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class FinancialSheet(Base):
    """재무제표 테이블"""
    __tablename__ = 'financial_sheet'
    item_cd = Column(String(6), primary_key=True)
    base_date = Column(String(8), primary_key=True, comment='기준일자 (YYYYMMDD)')
    sheet_cl = Column(String(1), primary_key=True, comment='시트구분 (0:연간, 1:분기)')
    stac_yymm = Column(String(6), primary_key=True, comment='결산년월')
    grs = Column(Float, comment='매출액증가율')
    bsop_prfi_inrt = Column(Float, comment='영업이익증가율')
    ntin_inrt = Column(Float, comment='순이익증가율')
    roe_val = Column(Float, comment='ROE')
    thtr_ntin = Column(BigInteger, comment='당기순이익')
    rsrv_rate = Column(Float, comment='유보율')
    lblt_rate = Column(Float, comment='부채비율')
    eps = Column(Float, comment='EPS')
    bps = Column(Float, comment='BPS')
    sps = Column(Float, comment='SPS')

class TradeStatus(Base):
    """매매 상태 테이블"""
    __tablename__ = 'trade_status'
    
    # [수정] Sequence 추가
    trade_id = Column(Integer, Sequence('trade_status_id_seq'), primary_key=True, autoincrement=True)
    
    item_cd = Column(String(6), nullable=False)
    trade_date = Column(String(8), nullable=False)
    trade_type = Column(String(2), nullable=False, comment='BS:매수, SS:매도')
    odno = Column(String(20), comment='주문번호')
    qty = Column(Integer, comment='수량')
    trade_price = Column(Integer, comment='거래가격')
    trade_time = Column(String(6), comment='거래시간')
    __table_args__ = (
        Index('idx_trade_status_item_date', 'item_cd', 'trade_date'),
    )

class TradeHistory(Base):
    """매매 이력 테이블"""
    __tablename__ = 'trade_history'
    
    # [수정] Sequence 추가
    id = Column(Integer, Sequence('trade_history_id_seq'), primary_key=True, autoincrement=True)
    
    item_cd = Column(String(6), nullable=False)
    trade_date = Column(String(8), nullable=False)
    trade_time = Column(String(6), nullable=False)
    trade_type = Column(String(10), nullable=False, comment='buy:매수, sell:매도')
    quantity = Column(Integer, comment='수량')
    price = Column(Integer, comment='가격')
    amount = Column(BigInteger, comment='거래금액')
    fee = Column(Integer, default=0, comment='수수료')
    tax = Column(Integer, default=0, comment='세금')
    profit = Column(Integer, comment='실현손익')
    profit_rate = Column(Float, comment='수익률')
    trade_source = Column(String(20), default='manual', comment='manual:수동, auto:자동')
    trade_reason = Column(String(200), comment='매매 사유')
    rmk = Column(Text, comment='비고')
    created_at = Column(DateTime, default=datetime.now)
    __table_args__ = (
        Index('idx_trade_history_date', 'trade_date'),
        Index('idx_trade_history_source', 'trade_source'),
    )

class VirtualAccount(Base):
    """가상 계좌 테이블"""
    __tablename__ = 'virtual_account'
    
    # [수정] Sequence 추가
    id = Column(Integer, Sequence('virtual_account_id_seq'), primary_key=True, autoincrement=True)
    
    balance = Column(BigInteger, comment='예수금')
    total_eval = Column(BigInteger, comment='총평가금액')
    total_profit = Column(BigInteger, comment='총손익')
    total_profit_rate = Column(Float, comment='총수익률')
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class VirtualHolding(Base):
    """가상 보유 종목 테이블"""
    __tablename__ = 'virtual_holding'
    item_cd = Column(String(6), primary_key=True)
    item_nm = Column(String(200), comment='종목명')
    qty = Column(Integer, comment='보유수량')
    avg_price = Column(Integer, comment='평균매입가')
    current_price = Column(Integer, comment='현재가')
    eval_amt = Column(BigInteger, comment='평가금액')
    profit = Column(BigInteger, comment='평가손익')
    profit_rate = Column(Float, comment='수익률')
    buy_date = Column(String(8), comment='최초매수일')
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ScheduleLog(Base):
    """스케줄 실행 로그 테이블"""
    __tablename__ = 'schedule_log'
    
    # [수정] Sequence 추가
    id = Column(Integer, Sequence('schedule_log_id_seq'), primary_key=True, autoincrement=True)
    
    schedule_id = Column(String(50), nullable=False)
    schedule_name = Column(String(100))
    task_type = Column(String(50))
    status = Column(String(20), comment='running, success, failed')
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    message = Column(Text)
    error_message = Column(Text)
    __table_args__ = (
        Index('idx_schedule_log_date', 'start_time'),
    )

class ScheduleItem(Base):
    """스케줄 설정 저장 테이블"""
    __tablename__ = 'schedule_item'
    
    # [수정] Sequence 추가 (에러 발생했던 부분)
    id = Column(Integer, Sequence('schedule_item_id_seq'), primary_key=True, autoincrement=True)
    
    name = Column(String(100), nullable=False, comment='스케줄 이름')
    task_type = Column(String(50), nullable=False, comment='작업 유형')
    cron_expression = Column(String(50), nullable=False, comment='Cron 표현식')
    enabled = Column(Boolean, default=True, comment='활성화 여부')
    created_at = Column(DateTime, default=datetime.now)

class EvaluationResult(Base):
    """종목 평가 결과 테이블"""
    __tablename__ = 'evaluation_result'
    item_cd = Column(String(6), primary_key=True, comment='종목코드')
    base_date = Column(String(8), primary_key=True, comment='기준일자 (YYYYMMDD)')
    item_nm = Column(String(200), comment='종목명')
    sheet_score = Column(Integer, default=0, comment='1.재무제표 점수')
    trend_score = Column(Integer, default=0, comment='2.주가 모멘텀 점수')
    price_score = Column(Integer, default=0, comment='3.주가 점수')
    kpi_score = Column(Integer, default=0, comment='4.보조지표 점수')
    buy_score = Column(Integer, default=0, comment='5.수급 점수')
    avls_score = Column(Integer, default=0, comment='6.시가총액 점수')
    per_score = Column(Integer, default=0, comment='7.PER 점수')
    pbr_score = Column(Integer, default=0, comment='8.PBR 점수')
    total_score = Column(Integer, default=0, comment='총점')
    is_buy_candidate = Column(Boolean, default=False, comment='매수 후보 여부')
    current_price = Column(Integer, comment='현재가')
    market_cap = Column(BigInteger, comment='시가총액')
    per = Column(Float, comment='PER')
    pbr = Column(Float, comment='PBR')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    __table_args__ = (
        Index('idx_eval_result_date', 'base_date'),
        Index('idx_eval_result_score', 'total_score'),
    )

class Holdings(Base):
    """보유 종목 테이블"""
    __tablename__ = 'holdings'
    item_cd = Column(String(6), primary_key=True, comment='종목코드')
    item_nm = Column(String(200), comment='종목명')
    quantity = Column(Integer, default=0, comment='보유수량')
    avg_price = Column(Integer, default=0, comment='평균매입가')
    current_price = Column(Integer, default=0, comment='현재가')
    buy_date = Column(String(8), comment='최초매수일')
    highest_price = Column(Integer, comment='최고가 (트레일링 스탑용)')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ============ 데이터베이스 연결 관리 (Thin Mode & Sequence 적용) ============

class DatabaseManager:
    """데이터베이스 연결 관리자"""
    _instance: Optional['DatabaseManager'] = None
    _engine = None
    _session_factory = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._engine is None:
            self._initialize()
    
    def _initialize(self):
        """엔진 및 세션 팩토리 초기화"""
        settings_manager = get_settings_manager()
        settings = settings_manager.settings
        
        connection_string = settings_manager.get_db_connection_string()
        
        logger.info(f"데이터베이스 연결 초기화 중... (Type: {settings.database.db_type})")
        
        connect_args = {}
        if settings.database.db_type == "oracle":
            wallet_path = settings.database.oracle_wallet_path
            if wallet_path and os.path.exists(wallet_path):
                connect_args = {
                    "config_dir": wallet_path,
                    "wallet_location": wallet_path,
                    "wallet_password": settings.database.oracle_password 
                }
                logger.info(f"Oracle Thin Mode 활성화 (Wallet: {wallet_path})")
            else:
                logger.warning(f"Wallet 경로를 찾을 수 없음: {wallet_path}")

        try:
            if 'sqlite' in connection_string:
                self._engine = create_engine(
                    connection_string,
                    echo=False,
                    connect_args={"check_same_thread": False}
                )
            else:
                self._engine = create_engine(
                    connection_string,
                    echo=False,
                    pool_size=5,
                    max_overflow=10,
                    connect_args=connect_args
                )

                @event.listens_for(self._engine, "connect")
                def do_connect(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    try:
                        cursor.execute("ALTER SESSION DISABLE PARALLEL DML")
                    except Exception:
                        pass
                    finally:
                        cursor.close()
            
            with self._engine.connect() as conn:
                logger.info("데이터베이스 연결 성공!")
                
            Base.metadata.create_all(self._engine)
            self._session_factory = sessionmaker(bind=self._engine)
            
        except Exception as e:
            logger.error(f"데이터베이스 엔진 생성 중 치명적 오류: {e}")
            raise e
    
    def reinitialize(self):
        if self._engine:
            self._engine.dispose()
        self._engine = None
        self._session_factory = None
        self._initialize()
    
    @property
    def engine(self):
        return self._engine
    
    @contextmanager
    def get_session(self) -> Generator:
        if self._session_factory is None:
            self._initialize()
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"데이터베이스 세션 오류: {e}")
            raise
        finally:
            session.close()

def get_db() -> DatabaseManager:
    return DatabaseManager()

def get_session():
    return get_db().get_session()