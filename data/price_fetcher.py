"""
가격 정보 및 주식 데이터 조회 모듈
- KIS API: 시세, 수급, PER/PBR, 시가총액 등 (실거래/데이터수집용)
- Yahoo Finance: 시뮬레이션 백업용
- 자동 토큰 갱신 (500 에러 대응)
"""

import logging
import requests
import json
import os
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
from pathlib import Path
import time

try:
    import yfinance as yf
except ImportError:
    yf = None

from config.settings import get_settings_manager
from config.database import get_session, ItemPrice, ItemEquity, ItemMst

logger = logging.getLogger(__name__)

# 토큰 저장 경로
TOKEN_DIR = Path(__file__).parent.parent / "config_data"
TOKEN_FILE = TOKEN_DIR / "kis_tokens.json"


class KISTokenManager:
    """한국투자증권 API 토큰 관리자 (발급, 저장, 갱신)"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized: return
        self._tokens = {
            'mock': {'access_token': None, 'token_expires': None, 'issue_count': 0, 'issue_date': None},
            'real': {'access_token': None, 'token_expires': None, 'issue_count': 0, 'issue_date': None}
        }
        self._load_tokens()
        self._initialized = True
    
    def _load_tokens(self):
        try:
            TOKEN_DIR.mkdir(exist_ok=True)
            if TOKEN_FILE.exists():
                with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for mode in ['mock', 'real']:
                    if mode in data:
                        self._tokens[mode]['access_token'] = data[mode].get('access_token')
                        expires_str = data[mode].get('token_expires')
                        if expires_str:
                            self._tokens[mode]['token_expires'] = datetime.fromisoformat(expires_str)
                        self._tokens[mode]['issue_count'] = data[mode].get('issue_count', 0)
                        issue_date_str = data[mode].get('issue_date')
                        if issue_date_str:
                            self._tokens[mode]['issue_date'] = datetime.fromisoformat(issue_date_str).date()
        except Exception as e:
            logger.warning(f"토큰 파일 로드 실패: {e}")
    
    def _save_tokens(self):
        try:
            TOKEN_DIR.mkdir(exist_ok=True)
            data = {}
            for mode in ['mock', 'real']:
                data[mode] = {
                    'access_token': self._tokens[mode]['access_token'],
                    'token_expires': self._tokens[mode]['token_expires'].isoformat() if self._tokens[mode]['token_expires'] else None,
                    'issue_count': self._tokens[mode]['issue_count'],
                    'issue_date': self._tokens[mode]['issue_date'].isoformat() if self._tokens[mode]['issue_date'] else None
                }
            with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"토큰 파일 저장 실패: {e}")

    def clear_token(self, mode: str):
        """토큰 정보 강제 초기화 (만료/오류 시 호출)"""
        if mode in self._tokens:
            logger.info(f"[{mode}] 만료된 토큰 정보를 삭제합니다.")
            self._tokens[mode]['access_token'] = None
            self._tokens[mode]['token_expires'] = None
            self._save_tokens()
    
    def get_token(self, mode: str, app_key: str, app_secret: str, base_url: str) -> Optional[str]:
        if mode not in ['mock', 'real']: return None
        token_data = self._tokens[mode]
        
        # 유효한 토큰이 있으면 반환
        if token_data['access_token'] and token_data['token_expires']:
            if datetime.now() < token_data['token_expires']:
                return token_data['access_token']
        
        # 일일 발급 한도 체크
        today = date.today()
        if token_data['issue_date'] != today:
            token_data['issue_count'] = 0
            token_data['issue_date'] = today
        
        if token_data['issue_count'] >= 5:
            logger.error(f"[{mode}] 일일 토큰 발급 한도 초과.")
            return None
        
        # 새 토큰 발급
        new_token = self._issue_new_token(mode, app_key, app_secret, base_url)
        if new_token:
            token_data['access_token'] = new_token
            # 유효기간: 24시간 중 여유를 두고 23시간으로 설정
            token_data['token_expires'] = datetime.now() + timedelta(hours=23)
            token_data['issue_count'] += 1
            token_data['issue_date'] = today
            self._save_tokens()
            return new_token
        return None
    
    def _issue_new_token(self, mode: str, app_key: str, app_secret: str, base_url: str) -> Optional[str]:
        try:
            url = f"{base_url}/oauth2/tokenP"
            headers = {"content-type": "application/json"}
            body = {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}
            
            logger.info(f"[{mode}] 새 접근 토큰 발급 요청 중...")
            response = requests.post(url, headers=headers, json=body, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"[{mode}] 토큰 발급 성공")
                return response.json().get('access_token')
            else:
                logger.error(f"[{mode}] 토큰 발급 실패: {response.text}")
                return None
        except Exception as e:
            logger.error(f"[{mode}] 토큰 발급 오류: {e}")
            return None
    
    def get_token_status(self, mode: str) -> Dict:
        token_data = self._tokens.get(mode, {})
        has_token = bool(token_data.get('access_token'))
        is_valid = False
        remaining_time = None
        if has_token and token_data.get('token_expires'):
            if datetime.now() < token_data['token_expires']:
                is_valid = True
                remaining_time = token_data['token_expires'] - datetime.now()
        issue_count = token_data.get('issue_count', 0)
        if token_data.get('issue_date') != date.today(): issue_count = 0
        return {
            'mode': mode, 'has_token': has_token, 'is_valid': is_valid,
            'expires': token_data.get('token_expires'), 'remaining_time': remaining_time,
            'issue_count_today': issue_count
        }


def get_token_manager() -> KISTokenManager:
    return KISTokenManager()


class KISAPIFetcher:
    """KIS API 데이터 수집 및 주문"""
    
    def __init__(self, mode: str = None):
        self.settings_manager = get_settings_manager()
        self.token_manager = get_token_manager()
        self._mode = mode
        self._load_api_config()
    
    def _load_api_config(self):
        api_settings = self.settings_manager.settings.api
        if self._mode is None: self._mode = api_settings.kis_api_mode
        
        if self._mode == "real":
            self.app_key = api_settings.kis_real_app_key
            self.app_secret = api_settings.kis_real_app_secret
            self.base_url = "https://openapi.koreainvestment.com:9443"
            self.is_mock = False
        else:
            self.app_key = api_settings.kis_mock_app_key
            self.app_secret = api_settings.kis_mock_app_secret
            self.base_url = "https://openapivts.koreainvestment.com:29443"
            self.is_mock = True
    
    def is_configured(self) -> bool:
        return bool(self.app_key and self.app_secret)
    
    def get_access_token(self) -> Optional[str]:
        if not self.is_configured(): return None
        return self.token_manager.get_token(self._mode, self.app_key, self.app_secret, self.base_url)
    
    def _get_headers(self, tr_id: str) -> Dict:
        token = self.get_access_token()
        if not token: return {}
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }

    def _call_api(self, tr_id: str, url: str, params: dict = None, body: dict = None, method: str = 'GET') -> Optional[Dict]:
        """
        [수정됨] API 호출 공통 메서드 (500 에러 시에도 토큰 만료 체크)
        """
        if not self.is_configured(): return None

        # 최대 2회 시도 (1회 실패 -> 토큰 갱신 -> 2회 재시도)
        for attempt in range(2):
            try:
                headers = self._get_headers(tr_id)
                if not headers: 
                    logger.error("헤더 생성 실패 (토큰 없음)")
                    return None
                
                if method == 'GET':
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                else:
                    response = requests.post(url, headers=headers, json=body, timeout=10)
                
                # 1. 응답 파싱 시도 (상태코드와 상관없이 JSON일 수 있음)
                data = None
                try:
                    data = response.json()
                except:
                    pass

                # 2. 토큰 만료 에러 코드 감지 (EGW00123: 만료, EGW00121: 유효하지 않음)
                # HTTP 500이어도 msg_cd가 이것들이면 토큰 문제임.
                if data and isinstance(data, dict):
                    msg_cd = data.get('msg_cd', '')

                    # 초당 전송 횟수 초과 (EGW00201)
                    if msg_cd == 'EGW00201':
                        logger.warning(f"API 호출 제한(초당 건수 초과). 0.5초 대기 후 재시도합니다.")
                        time.sleep(0.5) # 0.5초 쉬고 재시도
                        continue

                    if msg_cd in ['EGW00123', 'EGW00121']:
                        logger.warning(f"API 호출 실패 ({msg_cd}): 토큰 만료됨 (상태코드 {response.status_code}). 재발급 후 재시도합니다.")
                        self.token_manager.clear_token(self._mode)
                        continue  # 재시도 루프
                
                # 3. HTTP 상태 확인
                if response.status_code == 200:
                    return data
                else:
                    logger.error(f"HTTP 오류 ({response.status_code}): {response.text}, tr_id: {tr_id}")
                    return None
                    
            except Exception as e:
                logger.error(f"API 요청 중 예외 발생: {e}")
                return None
        
        return None
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict]:
        """종목 상세정보 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code}
        
        data = self._call_api("FHKST01010100", url, params=params)
        
        if data and data.get('rt_cd') == '0':
            o = data.get('output', {})
            return {
                'stck_clpr': self._int(o.get('stck_prpr')),
                'stck_oprc': self._int(o.get('stck_oprc')),
                'stck_hgpr': self._int(o.get('stck_hgpr')),
                'stck_lwpr': self._int(o.get('stck_lwpr')),
                'acml_vol': self._int(o.get('acml_vol')),
                'per': self._float(o.get('per')),
                'pbr': self._float(o.get('pbr')),
                'eps': self._float(o.get('eps')),
                'bps': self._float(o.get('bps')),
                'hts_avls': self._int(o.get('hts_avls')),
                'lstn_stcn': self._int(o.get('lstn_stcn')),
                'w52_hgpr': self._int(o.get('w52_hgpr')),
                'w52_hgpr_date': o.get('w52_hgpr_date', ''),
                'w52_lwpr': self._int(o.get('w52_lwpr')),
                'w52_lwpr_date': o.get('w52_lwpr_date', ''),
                'stck_dryy_hgpr': self._int(o.get('stck_dryy_hgpr')),
                'stck_dryy_lwpr': self._int(o.get('stck_dryy_lwpr')),
                'dryy_hgpr_vrss_prpr_rate': self._float(o.get('dryy_hgpr_vrss_prpr_rate')),
                'dryy_lwpr_vrss_prpr_rate': self._float(o.get('dryy_lwpr_vrss_prpr_rate')),
                'hts_frgn_ehrt': self._float(o.get('hts_frgn_ehrt')),
            }
        return None

    def get_period_prices(self, stock_code: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """기간별 시세 조회"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date, "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D", "FID_ORG_ADJ_PRC": "1"
        }
        
        data = self._call_api("FHKST03010100", url, params=params)
        
        if data and data.get('rt_cd') == '0':
            result = []
            items = data.get('output2', [])
            for item in items:
                if not item.get('stck_bsop_date'): continue
                result.append({
                    'stck_bsop_date': item.get('stck_bsop_date'),
                    'stck_clpr': self._int(item.get('stck_clpr')),
                    'stck_oprc': self._int(item.get('stck_oprc')),
                    'stck_hgpr': self._int(item.get('stck_hgpr')),
                    'stck_lwpr': self._int(item.get('stck_lwpr')),
                    'acml_vol': self._int(item.get('acml_vol')),
                    'prdy_vrss': self._int(item.get('prdy_vrss')),
                })
            return result
        return None

    def get_investor_trading(self, stock_code: str) -> Optional[Dict]:
        """투자자 매매동향"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor"
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code}
        
        data = self._call_api("FHKST01010900", url, params=params)
        
        if data and data.get('rt_cd') == '0':
            output_list = data.get('output', [])
            if output_list and isinstance(output_list, list) and len(output_list) > 0:
                latest_data = output_list[0]
                return {
                    'frgn_ntby_qty': self._int(latest_data.get('frgn_ntby_qty')),
                    'orgn_ntby_qty': self._int(latest_data.get('orgn_ntby_qty')),
                    'prsn_ntby_qty': self._int(latest_data.get('prsn_ntby_qty')),
                }
        return None

    def get_account_balance(self, account_no: str, account_cd: str) -> Optional[Dict]:
        """주식 잔고 및 예수금 조회"""
        tr_id = "TTTC8434R" if not self.is_mock else "VTTC8434R"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        params = {
            "CANO": account_no, "ACNT_PRDT_CD": account_cd, "AFHR_FLPR_YN": "N",
            "OFL_YN": "", "INQR_DVSN": "02", "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N", "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "", "CTX_AREA_NK100": ""
        }
        
        data = self._call_api(tr_id, url, params=params)
        
        if data:
            if data.get('rt_cd') == '0':
                output2 = data.get('output2', [])
                output1 = data.get('output1', [])
                if output2:
                    summary = output2[0]
                    deposit = int(summary.get('dnca_tot_amt', '0'))
                    total_eval = int(summary.get('tot_evlu_amt', '0'))
                    profit = int(summary.get('evlu_pfls_smtl_amt', '0'))
                    buy_amt = int(summary.get('pchs_amt_smtl_amt', '0'))
                    profit_rate = (profit / buy_amt) * 100 if buy_amt > 0 else 0.0
                    return {
                        'deposit': deposit, 'total_eval': total_eval, 'profit': profit,
                        'profit_rate': profit_rate, 'holdings_count': len(output1),
                        'holdings': output1
                    }
            else:
                logger.error(f"잔고조회 실패: {data.get('msg1')}")
        return None

    def send_order(self, order_type: str, stock_code: str, qty: int, price: int, account_no: str, account_cd: str) -> Dict:
        """주식 주문 (매수/매도)"""
        # TR ID 결정
        if self.is_mock:
            tr_id = "VTTC0012U" if order_type == 'buy' else "VTTC0011U"
        else:
            tr_id = "TTTC0012U" if order_type == 'buy' else "TTTC0011U"
            
        # 주문 구분 (00: 지정가, 01: 시장가)
        ord_dvsn = "01" if price == 0 else "00"
        ord_unpr = "0" if price == 0 else str(price)
        
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        
        body = {
            "CANO": account_no,
            "ACNT_PRDT_CD": account_cd,
            "PDNO": stock_code,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(qty),
            "ORD_UNPR": ord_unpr
        }
        
        data = self._call_api(tr_id, url, body=body, method='POST')
        
        if data:
            if data.get('rt_cd') == '0':
                return {
                    'success': True,
                    'message': data.get('msg1', '주문 완료'),
                    'order_no': data.get('output', {}).get('ODNO')
                }
            else:
                msg = data.get('msg1', '알 수 없는 오류')
                logger.error(f"주문 실패: {msg}")
                return {'success': False, 'message': msg}
        else:
            return {'success': False, 'message': 'API 호출 오류 (토큰/통신)'}

    def _int(self, v) -> int:
        if v is None: return 0
        try: return int(str(v).replace(',', ''))
        except: return 0
    
    def _float(self, v) -> float:
        if v is None: return 0.0
        try: return float(str(v).replace(',', ''))
        except: return 0.0


class StockDataCollector:
    """주식 데이터 수집 서비스"""
    
    def __init__(self, mode: str = None):
        self.kis_api = KISAPIFetcher(mode=mode)
    
    def collect_stock_data(self, stock_code: str, base_date_str: str) -> Dict:
        result = {'success': False, 'price_saved': False, 'equity_saved': False, 'error': None}
        if not self.kis_api.is_configured():
            result['error'] = "KIS API 미설정"
            return result
        try:
            stock_info = self.kis_api.get_stock_info(stock_code)
            investor_data = self.kis_api.get_investor_trading(stock_code)
            
            with get_session() as session:
                # 1. 시세 데이터 수집 (최근 400일 - 배치 처리)
                BATCH_SIZE = 100
                EPOCH = 4
                today = date.today()
                
                # 최근 데이터가 있으면 EPOCH 줄임 (업데이트 모드)
                latest_price = session.query(ItemPrice).filter(
                    ItemPrice.item_cd == stock_code
                ).order_by(ItemPrice.trade_date.desc()).first()
                
                if latest_price:
                    last_date = datetime.strptime(latest_price.trade_date, "%Y%m%d").date()
                    if (today - last_date).days < 3: EPOCH = 1
                
                collected_prices = []
                for i in range(EPOCH):
                    days_ago_to = i * BATCH_SIZE
                    days_ago_from = ((i + 1) * BATCH_SIZE) - 1
                    
                    to_date = today - timedelta(days=days_ago_to)
                    from_date = today - timedelta(days=days_ago_from)
                    
                    batch_data = self.kis_api.get_period_prices(
                        stock_code, 
                        from_date.strftime("%Y%m%d"), 
                        to_date.strftime("%Y%m%d")
                    )
                    
                    if batch_data:
                        collected_prices.extend(batch_data)
                    time.sleep(0.1) # API 부하 조절
                
                # DB 저장
                if collected_prices:
                    for p in collected_prices:
                        t_date = p['stck_bsop_date']
                        if not t_date: continue
                        
                        existing = session.query(ItemPrice).filter(
                            ItemPrice.item_cd == stock_code,
                            ItemPrice.trade_date == t_date
                        ).first()
                        
                        if not existing:
                            new_p = ItemPrice(
                                item_cd=stock_code,
                                trade_date=t_date,
                                stck_clpr=p['stck_clpr'],
                                stck_oprc=p['stck_oprc'],
                                stck_hgpr=p['stck_hgpr'],
                                stck_lwpr=p['stck_lwpr'],
                                acml_vol=p['acml_vol'],
                                prdy_vrss=p['prdy_vrss']
                            )
                            session.add(new_p)
                    session.flush()
                    result['price_saved'] = True
                
                # 이동평균 계산 및 업데이트
                all_prices = session.query(ItemPrice).filter(
                    ItemPrice.item_cd == stock_code
                ).order_by(ItemPrice.trade_date.desc()).limit(300).all()
                
                if all_prices:
                    closes = [p.stck_clpr for p in all_prices if p.stck_clpr]
                    ma = {}
                    if len(closes) >= 5: ma['ma5'] = sum(closes[:5])/5
                    if len(closes) >= 10: ma['ma10'] = sum(closes[:10])/10
                    if len(closes) >= 20: ma['ma20'] = sum(closes[:20])/20
                    if len(closes) >= 60: ma['ma60'] = sum(closes[:60])/60
                    if len(closes) >= 120: ma['ma120'] = sum(closes[:120])/120
                    if len(closes) >= 240: ma['ma240'] = sum(closes[:240])/240
                    
                    latest = all_prices[0]
                    latest.ma5 = ma.get('ma5', 0)
                    latest.ma10 = ma.get('ma10', 0)
                    latest.ma20 = ma.get('ma20', 0)
                    latest.ma60 = ma.get('ma60', 0)
                    latest.ma120 = ma.get('ma120', 0)
                    latest.ma240 = ma.get('ma240', 0)
                
                # 오래된 데이터 정리 (1년)
                one_year_ago = (today - timedelta(days=400)).strftime('%Y%m%d')
                session.query(ItemPrice).filter(
                    ItemPrice.item_cd == stock_code,
                    ItemPrice.trade_date < one_year_ago
                ).delete(synchronize_session=False)
                
                # 2. 주식 기본 정보 (Equity) 저장
                if stock_info:
                    eq = session.query(ItemEquity).filter(ItemEquity.item_cd == stock_code).first()
                    u_data = {
                        'lstn_stcn': stock_info.get('lstn_stcn'),
                        'hts_avls': stock_info.get('hts_avls'),
                        'per': stock_info.get('per'),
                        'pbr': stock_info.get('pbr'),
                        'eps': stock_info.get('eps'),
                        'bps': stock_info.get('bps'),
                        'stck_dryy_hgpr': stock_info.get('stck_dryy_hgpr'),
                        'stck_dryy_lwpr': stock_info.get('stck_dryy_lwpr'),
                        'dryy_hgpr_vrss_prpr_rate': stock_info.get('dryy_hgpr_vrss_prpr_rate'),
                        'dryy_lwpr_vrss_prpr_rate': stock_info.get('dryy_lwpr_vrss_prpr_rate')
                    }
                    if investor_data:
                        u_data['frgn_ntby_qty'] = investor_data.get('frgn_ntby_qty')
                        u_data['pgtr_ntby_qty'] = investor_data.get('orgn_ntby_qty')
                        
                    if eq:
                        for k, v in u_data.items():
                            if v is not None: setattr(eq, k, v)
                        eq.updated_date = datetime.now()
                    else:
                        session.add(ItemEquity(item_cd=stock_code, **u_data))
                    result['equity_saved'] = True
                
                session.commit()
                result['success'] = True
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"주식데이터 수집 오류 ({stock_code}): {e}")
            
        return result


class PriceFetcher:
    def __init__(self):
        self.kis = KISAPIFetcher()
        self.yf = YahooFinanceFetcher() if yf else None
    
    def get_current_price(self, code: str) -> Optional[Dict]:
        if self.kis.is_configured():
            r = self.kis.get_stock_info(code)
            if r:
                return {
                    'price': r.get('stck_clpr', 0),
                    'open': r.get('stck_oprc', 0),
                    'high': r.get('stck_hgpr', 0),
                    'low': r.get('stck_lwpr', 0),
                    'volume': r.get('acml_vol', 0),
                    'change': 0
                }
        
        # KIS 실패 시 야후 파이낸스 시도 (백업)
        if self.yf: return self.yf.get_current_price(code)
        return None

class YahooFinanceFetcher:
    def get_current_price(self, code: str) -> Optional[Dict]:
        try:
            # 코스피 우선 시도
            t = yf.Ticker(f"{code}.KS")
            h = t.history(period="1d")
            
            # 코스닥 재시도
            if h.empty:
                t = yf.Ticker(f"{code}.KQ")
                h = t.history(period="1d")
            
            if h.empty: return None
            
            l = h.iloc[-1]
            return {
                'price': int(l['Close']),
                'open': int(l['Open']),
                'high': int(l['High']),
                'low': int(l['Low']),
                'volume': int(l['Volume']),
                'change': 0
            }
        except: return None