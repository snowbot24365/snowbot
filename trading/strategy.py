"""
매매 전략 및 종목 평가 모듈
- data.evaluator 모듈을 import하여 사용 (로직 중복 제거)
- 스케줄러 실행 시 매수 후보(is_buy_candidate) 상태 저장 누락 수정
"""

import logging
from datetime import datetime, date
from typing import Dict
from enum import Enum

# 평가 로직(Evaluator) 임포트
from data.evaluator import Evaluator, SwingData
from config.database import get_session, ItemMst, ItemPrice, FinancialSheet, ItemEquity, EvaluationResult

logger = logging.getLogger(__name__)

class TradeSignal(Enum):
    STRONG_BUY = "강력매수"
    BUY = "매수"
    HOLD = "관망"
    SELL = "매도"
    STRONG_SELL = "강력매도"

class TradingStrategy:
    """
    종목 분석 및 평가 전략
    """
    
    def __init__(self):
        # 순수 평가 로직 인스턴스
        self.evaluator = Evaluator()
        
    def analyze_stock(self, stock_code: str, base_date: date = None) -> Dict:
        """단일 종목 상세 분석 (UI용)"""
        if base_date is None:
            base_date = date.today()
            
        result = {
            'item_cd': stock_code,
            'item_nm': '',
            'current_price': 0,
            'score': 0,
            'signal': TradeSignal.HOLD,
            'reasons': [],
            'target_price': 0,
            'details': {}
        }
        
        try:
            with get_session() as session:
                # 1. 데이터 조회
                item_info = session.query(ItemMst).filter(ItemMst.item_cd == stock_code).first()
                if not item_info:
                    result['reasons'].append("종목 정보 없음")
                    return result
                
                result['item_nm'] = item_info.itms_nm
                
                price_row = session.query(ItemPrice).filter(
                    ItemPrice.item_cd == stock_code
                ).order_by(ItemPrice.trade_date.desc()).first()
                
                if not price_row:
                    result['reasons'].append("시세 데이터 부족")
                    return result
                
                financial = session.query(FinancialSheet).filter(
                    FinancialSheet.item_cd == stock_code
                ).order_by(FinancialSheet.base_date.desc()).first()
                
                equity = session.query(ItemEquity).filter(
                    ItemEquity.item_cd == stock_code
                ).first()
                
                # 2. 데이터 변환 및 평가 실행
                swing_data = self._convert_to_swing_data(item_info, price_row, financial, equity)
                score_result = self.evaluator.evaluate(swing_data)
                
                # 3. 결과 매핑
                result['current_price'] = price_row.stck_clpr
                result['score'] = score_result.total_score
                result['target_price'] = int(price_row.stck_clpr * 1.05)
                
                # 상세 점수
                result['details'] = {
                    'sheet': score_result.sheet_score,
                    'trend': score_result.trend_score,
                    'price': score_result.price_score,
                    'buy': score_result.buy_score
                }
                
                # 4. 매매 시그널 결정
                if score_result.is_buy_candidate:
                    if score_result.total_score >= 30: # 기준점수는 Evaluator 로직에 따름
                        result['signal'] = TradeSignal.STRONG_BUY
                        result['reasons'].append("강력 매수 후보 (S등급)")
                    else:
                        result['signal'] = TradeSignal.BUY
                        result['reasons'].append("매수 유망 (A/B등급)")
                
                return result
                
        except Exception as e:
            logger.error(f"종목 분석 오류 ({stock_code}): {e}")
            return result

    def evaluate_all(self, base_date: date = None) -> int:
        """전 종목 일괄 평가 (스케줄러용)"""
        if base_date is None:
            base_date = date.today()
        
        base_date_str = base_date.strftime('%Y%m%d')
        count = 0
        
        try:
            with get_session() as session:
                items = session.query(ItemMst).all()
                total_items = len(items)
                logger.info(f"평가 시작: 총 {total_items}개 종목 (기준일: {base_date_str})")
                
                for item in items:
                    try:
                        price_row = session.query(ItemPrice).filter(
                            ItemPrice.item_cd == item.item_cd
                        ).order_by(ItemPrice.trade_date.desc()).first()
                        
                        if not price_row: continue
                            
                        financial = session.query(FinancialSheet).filter(
                            FinancialSheet.item_cd == item.item_cd
                        ).order_by(FinancialSheet.base_date.desc()).first()
                        
                        equity = session.query(ItemEquity).filter(
                            ItemEquity.item_cd == item.item_cd
                        ).first()
                        
                        # 평가 실행
                        swing_data = self._convert_to_swing_data(item, price_row, financial, equity)
                        score = self.evaluator.evaluate(swing_data)
                        
                        # 결과 저장
                        eval_result = session.query(EvaluationResult).filter(
                            EvaluationResult.item_cd == item.item_cd,
                            EvaluationResult.base_date == base_date_str
                        ).first()
                        
                        if not eval_result:
                            eval_result = EvaluationResult(
                                item_cd=item.item_cd,
                                base_date=base_date_str
                            )
                            session.add(eval_result)
                        
                        eval_result.item_nm = item.itms_nm
                        eval_result.current_price = price_row.stck_clpr
                        eval_result.total_score = score.total_score
                        
                        # [핵심 수정] 매수 후보 여부 저장 추가
                        eval_result.is_buy_candidate = score.is_buy_candidate
                        
                        # 세부 점수 저장
                        eval_result.sheet_score = score.sheet_score
                        eval_result.trend_score = score.trend_score
                        eval_result.price_score = score.price_score
                        eval_result.buy_score = score.buy_score
                        eval_result.kpi_score = score.kpi_score
                        eval_result.avls_score = score.avls_score
                        eval_result.per_score = score.per_score
                        eval_result.pbr_score = score.pbr_score
                        
                        eval_result.updated_at = datetime.now()
                        
                        count += 1
                        if count % 100 == 0:
                            session.commit()
                            
                    except Exception as e:
                        continue
                        
                session.commit()
                logger.info(f"일괄 평가 완료: {count}개 종목 업데이트됨")
                return count
                
        except Exception as e:
            logger.error(f"일괄 평가 전체 오류: {e}")
            return count

    def _convert_to_swing_data(self, item: ItemMst, price: ItemPrice, fs: FinancialSheet, eq: ItemEquity) -> SwingData:
        """DB 모델 -> SwingData 변환"""
        data = SwingData(item_cd=item.item_cd, item_nm=item.itms_nm)
        
        if price:
            data.stck_clpr = price.stck_clpr or 0
            data.ma5 = price.ma5 or 0
            data.ma20 = price.ma20 or 0
            data.ma60 = price.ma60 or 0
            data.ma120 = price.ma120 or 0
        
        if fs:
            data.grs = fs.grs or 0
            data.bsop_prfi_inrt = fs.bsop_prfi_inrt or 0
            data.roe_val = fs.roe_val or 0
            data.lblt_rate = fs.lblt_rate or 999
            data.thtr_ntin = fs.thtr_ntin or 0
            data.rsrv_rate = fs.rsrv_rate or 0
            
        if eq:
            data.frgn_ntby_qty = eq.frgn_ntby_qty or 0
            data.pgtr_ntby_qty = eq.pgtr_ntby_qty or 0
            data.hts_avls = eq.hts_avls or 0
            data.per = eq.per or 0
            data.pbr = eq.pbr or 0
            data.high_rate = eq.dryy_hgpr_vrss_prpr_rate or -99
            data.low_rate = eq.dryy_lwpr_vrss_prpr_rate or -99
            data.frgn_rate = eq.hts_frgn_ehrt or 0
            
        return data