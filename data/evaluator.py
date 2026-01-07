"""
종목 평가 로직 모듈
- 8가지 평가 지표 (총 40점 만점)
- Evaluator: 단일 종목 점수 계산기
- EvaluationService: 전 종목 일괄 평가 실행기 (UI/스케줄러 공용)
"""

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Dict, Callable
from config.settings import get_settings_manager

from config.database import (
    get_session, ItemMst, ItemPrice, FinancialSheet, ItemEquity, EvaluationResult
)

logger = logging.getLogger(__name__)

# =========================================================
# 1. 데이터 구조 및 계산기 (Evaluator)
# =========================================================

@dataclass
class SwingData:
    """평가에 필요한 데이터 집합"""
    item_cd: str
    item_nm: str = ""
    
    # 1. 시세 정보
    stck_clpr: int = 0
    ma5: int = 0
    ma20: int = 0
    ma60: int = 0
    ma120: int = 0
    
    # 2. 재무 정보
    grs: float = 0.0
    bsop_prfi_inrt: float = 0.0
    roe_val: float = 0.0
    lblt_rate: float = 999.0
    thtr_ntin: int = 0
    rsrv_rate: float = 0.0
    
    # 3. 수급/추세 정보
    frgn_ntby_qty: int = 0
    pgtr_ntby_qty: int = 0
    hts_avls: int = 0
    per: float = 0.0
    pbr: float = 0.0
    
    # 4. 추가 지표
    high_rate: float = -99.0
    low_rate: float = -99.0
    frgn_rate: float = 0.0

@dataclass
class EvaluationScore:
    """평가 결과 점수"""
    item_cd: str
    item_nm: str
    total_score: int = 0
    
    sheet_score: int = 0
    trend_score: int = 0
    price_score: int = 0
    kpi_score: int = 0
    buy_score: int = 0
    avls_score: int = 0
    per_score: int = 0
    pbr_score: int = 0
    
    is_buy_candidate: bool = False

class Evaluator:
    """순수 점수 계산 로직"""
    
    def evaluate(self, data: SwingData) -> EvaluationScore:
        score = EvaluationScore(item_cd=data.item_cd, item_nm=data.item_nm)
        
        score.sheet_score = self._cal_sheet_score(data)
        score.trend_score = self._cal_trend_score(data)
        score.price_score = self._cal_price_score(data)
        score.kpi_score = self._cal_kpi_score(data)
        score.buy_score = self._cal_buy_score(data)
        score.avls_score = self._cal_avls_score(data)
        score.per_score = self._cal_per_score(data)
        score.pbr_score = self._cal_pbr_score(data)
        
        score.total_score = (
            score.sheet_score + score.trend_score + score.price_score +
            score.kpi_score + score.buy_score + score.avls_score +
            score.per_score + score.pbr_score
        )
        
        score.is_buy_candidate = self._check_safety_net(data, score.total_score)
        return score

    def _cal_sheet_score(self, d: SwingData) -> int:
        point = 0
        if d.grs > 0: point += 1
        if d.bsop_prfi_inrt > 0: point += 1
        if d.roe_val > 5: point += 1
        if d.lblt_rate < 200: point += 1
        if d.thtr_ntin > 0: point += 1
        return point

    def _cal_trend_score(self, d: SwingData) -> int:
        point = 0
        if d.high_rate > -10: point += 2
        elif d.high_rate > -20: point += 1
        if d.low_rate > 10: point += 2
        elif d.low_rate > 5: point += 1
        if d.frgn_rate > 10: point += 1
        return min(5, point)

    def _cal_price_score(self, d: SwingData) -> int:
        point = 0
        p = d.stck_clpr
        if d.ma5 == 0 or d.ma20 == 0: return 0
        if p >= d.ma5: point += 1
        if p >= d.ma20: point += 1
        if d.ma5 >= d.ma20: point += 1
        if d.ma20 >= d.ma60: point += 1
        if d.ma60 >= d.ma120: point += 1
        return point

    def _cal_kpi_score(self, d: SwingData) -> int:
        point = 2
        if d.ma20 > 0:
            disparity = (d.stck_clpr / d.ma20) * 100
            if 98 <= disparity <= 110: point += 2
            elif disparity > 115: point -= 1
        return min(5, max(0, point))

    def _cal_buy_score(self, d: SwingData) -> int:
        point = 0
        if d.frgn_ntby_qty > 0: point += 2
        if d.pgtr_ntby_qty > 0: point += 3
        return min(5, point)

    def _cal_avls_score(self, d: SwingData) -> int:
        mkt_cap_bil = d.hts_avls / 100000000
        if mkt_cap_bil < 500: return 1
        if mkt_cap_bil > 10000: return 4
        return 5

    def _cal_per_score(self, d: SwingData) -> int:
        if d.per <= 0: return 0
        if d.per < 10: return 5
        if d.per < 15: return 4
        if d.per < 20: return 3
        if d.per < 50: return 2
        return 1

    def _cal_pbr_score(self, d: SwingData) -> int:
        if d.pbr <= 0: return 0
        if d.pbr < 1.0: return 5
        if d.pbr < 1.5: return 4
        if d.pbr < 3.0: return 3
        return 2

    def _check_safety_net(self, d: SwingData, total_score: int) -> bool:
        """
        최소 안전장치 검증
        - 적자 기업 제외
        - 부채비율 과다 제외
        - [수정] 설정된 최소 점수 미만 제외
        """
        # 1. 최신 설정 가져오기
        settings = get_settings_manager().settings
        min_cutline = settings.evaluation.min_total_score  # UI에서 설정한 값 (예: 30)

        # 2. 기본 재무 필터링
        if d.thtr_ntin < 0: return False    # 당기순이익 적자
        if d.lblt_rate > 400: return False  # 부채비율 400% 초과
        
        # 3. [수정] 설정된 기준 점수와 비교
        if total_score < min_cutline: 
            return False
            
        return True


# =========================================================
# 2. 실행 서비스 (EvaluationService) - UI/스케줄러 호출용
# =========================================================

class EvaluationService:
    """종목 평가 일괄 실행 서비스"""
    
    def __init__(self):
        self.evaluator = Evaluator()
    
    def run_evaluation(
        self, 
        base_date: date, 
        target_data_date: Optional[str] = None, # [변경] 데이터 조회 기준일 파라미터 추가
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict:
        """
        지정된 날짜의 데이터를 기반으로 전 종목 평가 실행
        :param base_date: 평가 결과가 저장될 기준 날짜 (EvaluationResult의 PK)
        :param target_data_date: 실제 데이터를 조회할 날짜 문자열 (YYYYMMDD) (None일 경우 base_date 사용)
        """
        
        # 1. 날짜 설정 분리
        # eval_date_str: 결과 저장용 날짜 (예: 오늘 20260107)
        eval_date_str = base_date.strftime('%Y%m%d')
        
        # data_date_str: 데이터 조회용 날짜 (예: 어제 20260106)
        # target_data_date가 없으면 base_date를 그대로 사용
        data_date_str = target_data_date if target_data_date else eval_date_str

        result = {
            'total_evaluated': 0,
            'buy_candidates': 0,
            'errors': []
        }
        
        def log(msg):
            if log_callback: log_callback(msg)
            else: logger.info(msg)

        try:
            with get_session() as session:
                # 2. [변경] 평가 대상 종목 조회 (ItemMst) -> data_date_str 사용
                # 평가 대상 리스트는 '데이터가 존재하는 날짜'를 기준으로 가져옵니다.
                items = session.query(ItemMst).filter(ItemMst.base_date == data_date_str).all()
                total_count = len(items)
                
                if total_count == 0:
                    log(f"해당 데이터 날짜({data_date_str})에 수집된 종목 데이터가 없습니다.")
                    return result
                
                log(f"총 {total_count}개 종목 평가 시작... (기준일:{eval_date_str}, 데이터:{data_date_str})")
                
                for idx, item in enumerate(items):
                    # 진행률 업데이트
                    if progress_callback:
                        progress_callback(idx + 1, total_count, f"{item.item_cd} 평가 중...")
                    
                    try:
                        # 3. [변경] 관련 데이터 조회 -> data_date_str 사용
                        
                        # 최신 시세 (데이터 기준일 포함 이전 날짜 중 가장 최근)
                        price = session.query(ItemPrice).filter(
                            ItemPrice.item_cd == item.item_cd,
                            ItemPrice.trade_date <= data_date_str # data_date_str 기준
                        ).order_by(ItemPrice.trade_date.desc()).first()
                        
                        if not price: continue

                        # 재무제표 (데이터 기준일 포함 이전 데이터 중 가장 최근)
                        fs = session.query(FinancialSheet).filter(
                            FinancialSheet.item_cd == item.item_cd,
                            FinancialSheet.base_date <= data_date_str # data_date_str 기준
                        ).order_by(FinancialSheet.base_date.desc()).first()
                        
                        # 수급/기타 (해당 종목의 최신 정보 - 보통 날짜 컬럼이 없거나 최신본 유지)
                        eq = session.query(ItemEquity).filter(
                            ItemEquity.item_cd == item.item_cd
                        ).first()
                        
                        # 4. 데이터 변환 (SwingData)
                        swing_data = self._convert_to_swing_data(item, price, fs, eq)
                        
                        # 5. 평가 실행 (Evaluator)
                        score = self.evaluator.evaluate(swing_data)
                        
                        # 6. [중요] 결과 저장 (EvaluationResult) -> eval_date_str 사용
                        # 평가는 과거 데이터를 보고 했더라도, '평가 결과'는 오늘 날짜(base_date)로 남깁니다.
                        self._save_result(session, eval_date_str, score, price.stck_clpr)
                        
                        result['total_evaluated'] += 1
                        if score.is_buy_candidate:
                            result['buy_candidates'] += 1
                            
                    except Exception as e:
                        # 에러 발생 시 로그는 남기되 계속 진행
                        result['errors'].append(f"{item.item_cd}: {e}")
                        
                    # 배치 커밋 (메모리 관리 및 속도 향상)
                    if (idx + 1) % 100 == 0:
                        session.commit()
                
                session.commit()
                log(f"평가 완료: 총 {result['total_evaluated']}건, 매수후보 {result['buy_candidates']}건")
                
        except Exception as e:
            log(f"평가 프로세스 오류: {e}")
            result['errors'].append(str(e))
            
        return result

    def _convert_to_swing_data(self, item, price, fs, eq) -> SwingData:
        """DB 객체를 SwingData로 변환"""
        d = SwingData(item_cd=item.item_cd, item_nm=item.itms_nm)
        
        if price:
            d.stck_clpr = price.stck_clpr or 0
            d.ma5 = price.ma5 or 0
            d.ma20 = price.ma20 or 0
            d.ma60 = price.ma60 or 0
            d.ma120 = price.ma120 or 0
            
        if fs:
            d.grs = fs.grs or 0
            d.bsop_prfi_inrt = fs.bsop_prfi_inrt or 0
            d.roe_val = fs.roe_val or 0
            d.lblt_rate = fs.lblt_rate or 999
            d.thtr_ntin = fs.thtr_ntin or 0
            d.rsrv_rate = fs.rsrv_rate or 0
            
        if eq:
            d.frgn_ntby_qty = eq.frgn_ntby_qty or 0
            d.pgtr_ntby_qty = eq.pgtr_ntby_qty or 0
            d.hts_avls = eq.hts_avls or 0
            d.per = eq.per or 0
            d.pbr = eq.pbr or 0
            d.high_rate = eq.dryy_hgpr_vrss_prpr_rate or -99
            d.low_rate = eq.dryy_lwpr_vrss_prpr_rate or -99
            d.frgn_rate = eq.hts_frgn_ehrt or 0
            
        return d

    def _save_result(self, session, base_date, score: EvaluationScore, current_price: int):
        """평가 결과 DB 저장/업데이트"""
        try:
            # 기존 결과 확인
            existing = session.query(EvaluationResult).filter(
                EvaluationResult.item_cd == score.item_cd,
                EvaluationResult.base_date == base_date
            ).first()
            
            if existing:
                # 업데이트
                existing.total_score = score.total_score
                existing.sheet_score = score.sheet_score
                existing.trend_score = score.trend_score
                existing.price_score = score.price_score
                existing.kpi_score = score.kpi_score
                existing.buy_score = score.buy_score
                existing.avls_score = score.avls_score
                existing.per_score = score.per_score
                existing.pbr_score = score.pbr_score
                existing.is_buy_candidate = score.is_buy_candidate
                existing.current_price = current_price
                existing.updated_at = datetime.now()
            else:
                # 신규 생성
                new_res = EvaluationResult(
                    item_cd=score.item_cd,
                    base_date=base_date,
                    item_nm=score.item_nm,
                    total_score=score.total_score,
                    sheet_score=score.sheet_score,
                    trend_score=score.trend_score,
                    price_score=score.price_score,
                    kpi_score=score.kpi_score,
                    buy_score=score.buy_score,
                    avls_score=score.avls_score,
                    per_score=score.per_score,
                    pbr_score=score.pbr_score,
                    is_buy_candidate=score.is_buy_candidate,
                    current_price=current_price,
                    created_at=datetime.now()
                )
                session.add(new_res)
        except Exception as e:
            logger.error(f"결과 저장 실패 ({score.item_cd}): {e}")