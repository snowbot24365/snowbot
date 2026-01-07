"""
데이터 수집 모듈
- KRX API: KOSPI/KOSDAQ 종목 목록 수집
- OpenDart API: 재무제표, 기업정보 수집
- 통합 수집 로직 (run_collection)
"""

import logging
import random
from datetime import datetime, date
from typing import List, Dict, Optional, Callable
import time

import requests
import pandas as pd

try:
    import OpenDartReader as odr
except ImportError:
    odr = None

from config.settings import get_settings_manager
from config.database import (
    get_session, ItemMst, FinancialSheet
)

logger = logging.getLogger(__name__)


class KRXCollector:
    """KRX Open API 기반 종목 목록 수집기"""
    
    # KRX Open API 엔드포인트
    KRX_KOSPI_URL = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_isu_base_info"
    KRX_KOSDAQ_URL = "https://data-dbg.krx.co.kr/svc/apis/sto/ksq_isu_base_info"
    
    def __init__(self):
        self.settings_manager = get_settings_manager()
    
    def get_last_trading_date(self, base_date: date = None) -> str:
        """
        가장 최근 장이 열린 날짜 반환
        """
        import holidays
        from datetime import timedelta
        
        kr_holidays = holidays.KR()
        
        if base_date is None:
            base_date = date.today()
        
        # 오늘이면 어제부터 검색 (당일 데이터는 장 마감 후에만 제공될 수 있음)
        if base_date == date.today():
            check_date = base_date - timedelta(days=1)
        else:
            check_date = base_date
        
        # 최대 30일 전까지 검색
        for _ in range(30):
            if check_date.weekday() < 5 and check_date not in kr_holidays:
                return check_date.strftime('%Y%m%d')
            check_date -= timedelta(days=1)
        
        return base_date.strftime('%Y%m%d')
    
    def collect_stock_list(
        self,
        market: str = "ALL",
        base_date: date = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[Dict]:
        """KRX에서 상장 종목 목록 수집"""
        results = []
        bas_dd = self.get_last_trading_date(base_date)
        logger.info(f"KRX API 조회 기준일: {bas_dd}")
        
        try:
            if market in ["KOSPI", "ALL"]:
                if progress_callback:
                    progress_callback(f"KOSPI 종목 목록 조회 중... (기준일: {bas_dd})")
                kospi_list = self._fetch_market_list("STK", bas_dd)
                for item in kospi_list:
                    item['mrkt_ctg'] = 'KOSPI'
                results.extend(kospi_list)
                logger.info(f"KOSPI 종목 수집: {len(kospi_list)}개")
            
            if market in ["KOSDAQ", "ALL"]:
                if progress_callback:
                    progress_callback(f"KOSDAQ 종목 목록 조회 중... (기준일: {bas_dd})")
                kosdaq_list = self._fetch_market_list("KSQ", bas_dd)
                for item in kosdaq_list:
                    item['mrkt_ctg'] = 'KOSDAQ'
                results.extend(kosdaq_list)
                logger.info(f"KOSDAQ 종목 수집: {len(kosdaq_list)}개")
            
            logger.info(f"전체 종목 수집 완료: {len(results)}개")
            return results
            
        except Exception as e:
            logger.error(f"KRX 종목 목록 수집 오류: {e}")
            raise
    
    def _fetch_market_list(self, market_code: str, bas_dd: str) -> List[Dict]:
        """특정 시장의 종목 목록 조회"""
        try:
            api_key = self.settings_manager.settings.api.krx_api_key
            
            if not api_key:
                raise ValueError("KRX API 키가 설정되지 않았습니다.")
            
            url = self.KRX_KOSPI_URL if market_code == "STK" else self.KRX_KOSDAQ_URL
            
            params = {
                'AUTH_KEY': api_key,
                'basDd': bas_dd
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            items = data.get('OutBlock_1', [])
            
            result = []
            for item in items:
                stock_code = item.get('ISU_SRT_CD', '')
                if len(stock_code) == 6 and stock_code.isdigit():
                    result.append({
                        'item_cd': stock_code,
                        'itms_nm': item.get('ISU_ABBRV', ''),
                        'corp_nm': item.get('ISU_NM', ''),
                        'sector': item.get('IDX_IND_NM', ''),
                        'list_shares': item.get('LIST_SHRS', ''),
                        'mkt_cap': item.get('MKTCAP', ''),
                    })
            return result
            
        except Exception as e:
            logger.error(f"KRX API 요청 오류 ({market_code}): {e}")
            return []


class DartCollector:
    """OpenDart 데이터 수집기 (재무제표)"""
    
    def __init__(self):
        self.settings_manager = get_settings_manager()
        self._dart = None
    
    @property
    def dart(self):
        if self._dart is None:
            api_key = self.settings_manager.settings.api.opendart_api_key
            if not api_key:
                raise ValueError("OpenDart API 키가 설정되지 않았습니다.")
            if odr is None:
                raise ImportError("OpenDartReader 패키지가 설치되지 않았습니다.")
            self._dart = odr(api_key)
        return self._dart
    
    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """종목코드로 기업고유번호(corp_code) 조회"""
        try:
            corp_list = self.dart.corp_codes
            match = corp_list[corp_list['stock_code'] == stock_code]
            if len(match) > 0:
                return match.iloc[0]['corp_code']
            return None
        except Exception as e:
            logger.debug(f"기업코드 조회 실패: {stock_code} - {e}")
            return None
    
    def collect_financial_ratios(self, stock_code: str, year: int) -> Optional[Dict]:
        """재무비율 수집 (DART API 직접 활용)"""
        try:
            corp_code = self.get_corp_code(stock_code)
            if not corp_code:
                return None
            
            # 우선순위: 사업보고서(11011) -> 3분기 -> 반기 -> 1분기
            codes = ['11011', '11014', '11012', '11013']
            
            for r_code in codes:
                try:
                    fs = self.dart.finstate(corp_code, year, reprt_code=r_code)
                    if fs is not None and not isinstance(fs, dict) and not fs.empty:
                        res = self._parse_financial_data(fs, stock_code, year)
                        if res.get('has_data'):
                            return res
                except:
                    continue
            
            # 전년도 시도
            try:
                fs = self.dart.finstate(corp_code, year - 1, reprt_code='11011')
                if fs is not None and not isinstance(fs, dict) and not fs.empty:
                    res = self._parse_financial_data(fs, stock_code, year - 1)
                    if res.get('has_data'):
                        return res
            except:
                pass
            
            return None
            
        except Exception as e:
            logger.debug(f"재무비율 수집 오류 ({stock_code}): {e}")
            return None
    
    def _parse_financial_data(self, fs_df, stock_code: str, year: int) -> Dict:
        """재무제표 DataFrame에서 필요한 데이터 추출"""
        result = {
            'item_cd': stock_code,
            'year': year,
            'has_data': False
        }
        
        try:
            if 'fs_nm' in fs_df.columns:
                cfs_df = fs_df[fs_df['fs_nm'].str.contains('연결', na=False)]
                if cfs_df.empty:
                    cfs_df = fs_df
            else:
                cfs_df = fs_df
            
            def get_amount(df, keywords, column='thstrm_amount'):
                for keyword in keywords:
                    mask = df['account_nm'].str.contains(keyword, na=False, regex=False)
                    rows = df[mask]
                    if not rows.empty:
                        val = rows.iloc[0].get(column)
                        if val and pd.notna(val):
                            if isinstance(val, str):
                                val = val.replace(',', '').replace(' ', '')
                                try: return float(val)
                                except: return None
                            return float(val)
                return None
            
            revenue = get_amount(cfs_df, ['매출액', '영업수익', '수익(매출액)'])
            operating_profit = get_amount(cfs_df, ['영업이익', '영업손익'])
            net_income = get_amount(cfs_df, ['당기순이익', '당기순손익', '분기순이익'])
            total_equity = get_amount(cfs_df, ['자본총계'])
            total_liabilities = get_amount(cfs_df, ['부채총계'])
            retained_earnings = get_amount(cfs_df, ['이익잉여금', '결손금'])
            prev_revenue = get_amount(cfs_df, ['매출액', '영업수익'], 'frmtrm_amount')
            prev_operating_profit = get_amount(cfs_df, ['영업이익', '영업손익'], 'frmtrm_amount')
            capital = get_amount(cfs_df, ['자본금', '납입자본'])
            
            if revenue and prev_revenue and prev_revenue != 0:
                result['grs'] = self._validate_ratio(((revenue - prev_revenue) / abs(prev_revenue)) * 100, '매출액증가율', -100, 500)
            
            if operating_profit and prev_operating_profit and prev_operating_profit != 0:
                result['bsop_prfi_inrt'] = self._validate_ratio(((operating_profit - prev_operating_profit) / abs(prev_operating_profit)) * 100, '영업이익증가율', -100, 500)
            
            if retained_earnings and capital and capital != 0:
                result['rsrv_rate'] = self._validate_ratio((retained_earnings / capital) * 100, '유보율', -1000, 50000)
            
            if total_liabilities and total_equity and total_equity != 0:
                result['lblt_rate'] = self._validate_ratio((total_liabilities / total_equity) * 100, '부채비율', 0, 5000)
            
            if net_income:
                result['thtr_ntin'] = net_income
            
            if net_income and total_equity and total_equity != 0:
                result['roe'] = self._validate_ratio((net_income / total_equity) * 100, 'ROE', -100, 200)
            
            if any([result.get(k) is not None for k in ['grs', 'bsop_prfi_inrt', 'lblt_rate', 'roe', 'thtr_ntin']]):
                result['has_data'] = True
            
            return result
            
        except Exception as e:
            logger.debug(f"재무데이터 파싱 오류 ({stock_code}): {e}")
            return result
    
    def _validate_ratio(self, value: float, name: str, min_val: float = -1000, max_val: float = 1000) -> Optional[float]:
        if value is None: return None
        if value < min_val or value > max_val: return None
        return round(value, 2)


class DataCollectionService:
    """데이터 수집 통합 서비스"""
    
    def __init__(self):
        self.krx_collector = KRXCollector()
        self.dart_collector = DartCollector()
        self.settings_manager = get_settings_manager()

    # =========================================================================
    # [통합] 데이터 수집 메인 함수 (Full + Incremental)
    # =========================================================================
    def run_collection(
        self,
        base_date: date = None,
        collect_source: str = 'auto',  # 'auto' or 'manual'
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict:
        """
        통합 데이터 수집 로직
        - 설정(collection_mode)에 따라 '전체' 또는 '무작위 N개' 수집
        - DB 상태에 따라 초기화(Full) 또는 이어하기(Incremental) 자동 처리
        """
        if base_date is None:
            base_date = date.today()
        
        base_date_str = base_date.strftime('%Y%m%d')
        
        result = {
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'base_date': base_date_str,
            'collect_source': collect_source,
            'items_collected': 0,
            'financial_collected': 0,
            'financial_skipped': 0,
            'kis_collected': 0,
            'errors': [],
            'logs': []
        }
        
        def log(message: str, level: str = "INFO"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_msg = f"[{timestamp}] {message}"
            result['logs'].append(log_msg)
            if level == "ERROR": logger.error(message)
            else: logger.info(message)
            if log_callback: log_callback(log_msg)

        try:
            settings = self.settings_manager.settings.collection
            mode_label = "무작위 N개" if settings.collection_mode == "random_n" else "전체"
            log("=" * 50)
            log(f"데이터 수집 시작 (기준일: {base_date_str}, 모드: {mode_label})")
            
            # -------------------------------------------------------
            # 1단계: 종목 리스트 준비 (없으면 KRX 수집)
            # -------------------------------------------------------
            item_count = 0
            with get_session() as session:
                item_count = session.query(ItemMst).filter(ItemMst.base_date == base_date_str).count()
            
            if item_count == 0:
                log("DB에 금일 종목 리스트가 없습니다. KRX 수집을 진행합니다.")
                if progress_callback: progress_callback(0, 100, "KRX 종목 목록 수집 중...")
                
                # 시장 선택
                market = "ALL"
                if settings.collect_kospi and not settings.collect_kosdaq: market = "KOSPI"
                elif not settings.collect_kospi and settings.collect_kosdaq: market = "KOSDAQ"
                
                # KRX 수집
                all_items = self.krx_collector.collect_stock_list(
                    market=market, base_date=base_date, 
                    progress_callback=lambda msg: log(msg)
                )
                
                if not all_items:
                    log("KRX 종목 목록 수집 실패 (장 휴장일 가능성)", "ERROR")
                    return result
                
                # [중요] 설정에 따른 수집 대상 필터링 (DB 저장 단계에서 제한)
                if settings.collection_mode == "random_n":
                    target_count = min(settings.random_n_stocks, len(all_items))
                    all_items = random.sample(all_items, target_count)
                    log(f"설정에 따라 무작위 {target_count}개 종목만 선택하여 저장합니다.")
                
                saved = self._save_items_to_db(all_items, base_date_str)
                result['items_collected'] = saved
                log(f"종목 리스트 DB 저장 완료: {saved}개")
            else:
                log(f"DB에 이미 {item_count}개의 종목 리스트가 존재합니다. 상세 수집 단계로 이동합니다.")

            # -------------------------------------------------------
            # 2단계: 미수집 종목(Pending) 대상 선정
            # -------------------------------------------------------
            target_items = []
            with get_session() as session:
                # collect_source가 NULL인 것만 조회 (완료된 것은 건너뜀)
                query = session.query(ItemMst).filter(
                    ItemMst.base_date == base_date_str,
                    ItemMst.collect_source.is_(None)
                ).all()
                for item in query:
                    target_items.append({
                        'item_cd': item.item_cd,
                        'itms_nm': item.itms_nm,
                        'mrkt_ctg': item.mrkt_ctg
                    })
            
            # [중요] 이미 DB에 전체 데이터가 있는데 '무작위 N개'로 모드를 변경한 경우 대비
            # 미수집 종목이 설정된 N개보다 많으면, N개까지만 무작위로 선택해서 진행
            if settings.collection_mode == "random_n":
                limit_n = settings.random_n_stocks
                if len(target_items) > limit_n:
                    target_items = random.sample(target_items, limit_n)
                    log(f"수집 대상이 많아 설정된 {limit_n}개만 무작위로 선택하여 진행합니다.")

            total_count = len(target_items)
            if total_count == 0:
                log("수집할 대상이 없습니다. (모든 종목 수집 완료됨)")
                result['end_time'] = datetime.now().isoformat()
                if progress_callback: progress_callback(100, 100, "완료")
                return result

            log(f"상세 데이터 수집 대상: {total_count}개 종목")

            # -------------------------------------------------------
            # 3단계: 상세 데이터 수집 (시세/재무)
            # -------------------------------------------------------
            current_year = date.today().year - 1
            
            # KIS API 준비
            from data.price_fetcher import StockDataCollector
            stock_data_collector = StockDataCollector()
            kis_configured = stock_data_collector.kis_api.is_configured()
            
            if kis_configured: log("KIS API 연결됨 (시세 수집 가능)")
            else: log("KIS API 미연결 (재무 정보만 수집)")

            for idx, item in enumerate(target_items):
                stock_code = item['item_cd']
                stock_name = item.get('itms_nm', stock_code)
                market_type = item.get('mrkt_ctg', '')
                
                if progress_callback:
                    progress = int((idx / total_count) * 100)
                    progress_callback(progress, 100, f"[{idx+1}/{total_count}] {stock_name}")

                # 작업 시작 표시
                self._update_item_collect_source(stock_code, base_date_str, collect_source or 'manual')
                
                try:
                    # [KIS] 시세/수급/PER/PBR 수집
                    if kis_configured:
                        kis_res = stock_data_collector.collect_stock_data(stock_code, base_date_str)
                        if kis_res.get('success'):
                            result['kis_collected'] += 1
                    
                    # [DART] 재무제표 수집
                    financial = self.dart_collector.collect_financial_ratios(stock_code, current_year)
                    
                    if financial and financial.get('has_data'):
                        self._save_financial_to_db(stock_code, financial, base_date_str)
                        result['financial_collected'] += 1
                        log(f"✓ [{market_type}] {stock_name} - 수집 성공")
                    else:
                        result['financial_skipped'] += 1
                        log(f"- [{market_type}] {stock_name} - 재무 없음")
                    
                    time.sleep(0.3) 
                    
                except Exception as e:
                    result['errors'].append(f"{stock_code}: {e}")
                    log(f"✗ {stock_name} 오류: {e}", "ERROR")

            log("데이터 수집 작업이 완료되었습니다.")
            result['end_time'] = datetime.now().isoformat()
            if progress_callback: progress_callback(100, 100, "수집 완료")
            
        except Exception as e:
            log(f"프로세스 치명적 오류: {e}", "ERROR")
            result['errors'].append(str(e))
            
        return result

    # --- Helper Methods ---
    
    def _save_items_to_db(self, items: List[Dict], base_date_str: str) -> int:
        count = 0
        with get_session() as session:
            for item in items:
                try:
                    existing = session.query(ItemMst).filter(
                        ItemMst.item_cd == item['item_cd'],
                        ItemMst.base_date == base_date_str
                    ).first()
                    if not existing:
                        new_item = ItemMst(
                            item_cd=item['item_cd'],
                            base_date=base_date_str,
                            itms_nm=item.get('itms_nm', ''),
                            corp_nm=item.get('corp_nm', ''),
                            mrkt_ctg=item.get('mrkt_ctg', ''),
                            sector=item.get('sector', ''),
                            collect_source=None,
                            created_date=datetime.now()
                        )
                        session.add(new_item)
                        count += 1
                except: pass
        return count

    def _update_item_collect_source(self, stock_code: str, base_date_str: str, source: str):
        try:
            with get_session() as session:
                item = session.query(ItemMst).filter(
                    ItemMst.item_cd == stock_code,
                    ItemMst.base_date == base_date_str
                ).first()
                if item:
                    item.collect_source = source
                    item.updated_date = datetime.now()
                    session.commit()
        except: pass

    def _save_financial_to_db(self, stock_code: str, data: Dict, base_date_str: str):
        try:
            with get_session() as session:
                year = data.get('year')
                stac = f"{year}12"
                
                sheet = session.query(FinancialSheet).filter(
                    FinancialSheet.item_cd == stock_code,
                    FinancialSheet.base_date == base_date_str
                ).first()
                
                if not sheet:
                    sheet = FinancialSheet(
                        item_cd=stock_code,
                        base_date=base_date_str,
                        sheet_cl='0',
                        stac_yymm=stac
                    )
                    session.add(sheet)
                
                sheet.grs = data.get('grs')
                sheet.bsop_prfi_inrt = data.get('bsop_prfi_inrt')
                sheet.rsrv_rate = data.get('rsrv_rate')
                sheet.lblt_rate = data.get('lblt_rate')
                sheet.thtr_ntin = data.get('thtr_ntin')
                sheet.roe_val = data.get('roe')
                session.commit()
        except: pass

    # 기존 호환성 유지를 위한 Alias
    def run_full_collection(self, **kwargs):
        return self.run_collection(**kwargs)

    def run_incremental_collection(self, **kwargs):
        return self.run_collection(**kwargs)