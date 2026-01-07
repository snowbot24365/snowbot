"""
자동매매 실행 모듈
- 계좌 잔고 조회 및 리스크 관리
- 매도 로직: 보유 종목 수익률 점검 및 매도 주문
- 매수 로직: 평가 우수 종목 선정 및 매수 주문
"""

import logging
from datetime import datetime, date
import time

from config.settings import get_settings_manager
from config.database import get_session, TradeHistory, EvaluationResult, ItemMst
from data.price_fetcher import KISAPIFetcher
from trading.strategy import TradingStrategy

logger = logging.getLogger(__name__)

class AutoTrader:
    def __init__(self):
        self.settings_manager = get_settings_manager()
        self.settings = self.settings_manager.settings
        
        # 실행 모드 확인 (simulation / real_trading)
        self.mode = self.settings.execution_mode
        
        # API 모드 확인 (real / mock)
        if self.mode == "real_trading" and self.settings.api.kis_trading_account_mode == "real":
            self.api_mode = "real"
        else:
            self.api_mode = "mock"
            
        self.kis = KISAPIFetcher(mode=self.api_mode)
        self.strategy = TradingStrategy()
        
        # 매매 설정 로드
        self.trade_cfg = self.settings.trading

    def run(self) -> str:
        """자동매매 메인 실행 함수"""
        logs = []
        
        if not self.kis.is_configured():
            return "자동매매 실패: KIS API 설정이 필요합니다."

        try:
            # 1. 계좌 정보 조회
            time.sleep(0.2)
            balance = self._get_account_balance()
            if not balance:
                return "자동매매 실패: 계좌 정보를 가져올 수 없습니다."
            
            # logs.append(f"계좌 잔고 조회 완료 (예수금: {balance['deposit']:,}원)")
            
            # 2. 매도 프로세스 (수익 실현 / 손절)
            sell_logs = self._process_selling(balance['holdings'])
            logs.extend(sell_logs)
            
            # 3. 매수 프로세스 (신규 진입)
            if self.trade_cfg.buy_enabled:
                # 매도 후 예수금 갱신 필요 (간단히 계산하거나 API 재호출)
                # 여기서는 보수적으로 이전 예수금 사용
                buy_logs = self._process_buying(balance['deposit'], len(balance['holdings']))
                logs.extend(buy_logs)
            else:
                logs.append("매수 비활성화됨 (설정 확인)")
                
            return "\n".join(logs)
            
        except Exception as e:
            logger.error(f"자동매매 실행 중 오류: {e}")
            return f"오류 발생: {str(e)}"

    def _get_account_balance(self):
        """계좌 잔고 및 보유종목 조회"""
        if self.api_mode == "real":
            acc_no = self.settings.api.kis_real_account_no
            acc_cd = self.settings.api.kis_real_account_cd
        else:
            acc_no = self.settings.api.kis_mock_account_no
            acc_cd = self.settings.api.kis_mock_account_cd
            
        return self.kis.get_account_balance(acc_no, acc_cd)

    def _process_selling(self, holdings):
        """매도 로직 수행"""
        logs = []
        if not holdings:
            return logs
            
        sell_up = self.trade_cfg.sell_up_rate     # 익절률 (예: 10%)
        sell_down = self.trade_cfg.sell_down_rate # 손절률 (예: -5%)
        
        for item in holdings:
            # KIS API 잔고 포맷 파싱
            item_cd = item.get('pdno')
            item_nm = item.get('prdt_name')
            qty = int(item.get('hldg_qty', 0))
            profit_rate = float(item.get('evlu_pfls_rt', 0))
            
            if qty <= 0: continue
            
            action = None
            reason = ""
            
            # 1. 익절 조건
            if profit_rate >= sell_up:
                action = "SELL"
                reason = f"익절 조건 도달 ({profit_rate:.2f}% >= {sell_up}%)"
                
            # 2. 손절 조건
            elif profit_rate <= sell_down:
                action = "SELL"
                reason = f"손절 조건 도달 ({profit_rate:.2f}% <= {sell_down}%)"
            
            # TODO: 트레일링 스탑 로직 추가 가능
            
            # 매도 실행
            if action == "SELL":
                # 시장가 매도 주문
                res = self.kis.send_order(
                    order_type="sell",
                    stock_code=item_cd,
                    qty=qty,
                    price=0, # 시장가
                    account_no=self._get_account_no(),
                    account_cd=self._get_account_cd()
                )
                
                if res['success']:
                    msg = f"📉 [매도성공] {item_nm}({item_cd}) {qty}주 - {reason}"
                    logs.append(msg)
                    logger.info(msg)
                    
                    # DB 기록
                    self._save_trade_history(item_cd, 'sell', qty, 0, reason)
                else:
                    msg = f"❌ [매도실패] {item_nm} - {res.get('message')}"
                    logs.append(msg)
                    logger.error(msg)
                    
        return logs

    def _process_buying(self, deposit, current_holdings_count):
        """매수 로직 수행"""
        # DB 모델 임포트 (TradeHistory 추가)
        from config.database import ItemPrice, TradeHistory, EvaluationResult
        
        logs = []
        
        # 1. 보유 종목 수 제한 확인
        limit_count = self.trade_cfg.limit_count
        if current_holdings_count >= limit_count:
            logs.append(f"매수 생략: 최대 보유 종목 수 도달 ({current_holdings_count}/{limit_count})")
            return logs
            
        # 2. 매수 가능 종목 수 계산
        slots_available = limit_count - current_holdings_count
        
        # 3. 1회 매수 금액 계산
        max_per_trade = self.trade_cfg.max_buy_amount
        budget_by_rate = int(deposit * (self.trade_cfg.buy_rate / 100))
        target_amount = min(max_per_trade, budget_by_rate)
        
        if target_amount < 10000: # 최소 1만원 이상
            logs.append("매수 생략: 가용 예산 부족")
            return logs
            
        # 4. 매수 후보 종목 선정
        today_str = date.today().strftime('%Y%m%d')
        
        with get_session() as session:
            # [추가] A. 당일 이미 매수한 종목 코드 조회 (중복 매수 방지)
            # TradeHistory 테이블에서 오늘 날짜, 'buy' 타입인 종목 코드를 Set으로 가져옵니다.
            today_bought_codes = {
                row[0] for row in session.query(TradeHistory.item_cd).filter(
                    TradeHistory.trade_date == today_str,
                    TradeHistory.trade_type == 'buy'
                ).all()
            }

            # 평가 점수 상위 종목 조회
            candidates = session.query(EvaluationResult).filter(
                EvaluationResult.base_date == today_str,
                EvaluationResult.total_score >= self.settings.evaluation.min_total_score,
                EvaluationResult.is_buy_candidate == True  # <--- ✅ 매수 추천 종목만 필터링
            ).order_by(EvaluationResult.total_score.desc()).limit(10).all()
            
            buy_count = 0
            for cand in candidates:
                if buy_count >= slots_available:
                    break
                
                # [추가] B. 당일 매수 이력 체크
                if cand.item_cd in today_bought_codes:
                    # 이미 오늘 매수한 종목은 패스
                    continue

                time.sleep(0.2) # API 호출 간격

                # C. 현재가 조회 (실시간)
                curr_price_info = self.kis.get_stock_info(cand.item_cd)

                # 1. 데이터 수신 실패 체크
                if not curr_price_info:
                    continue
                
                # 2. 현재가 추출 및 정수 변환 (안전하게 처리)
                # API 응답값은 문자열이므로 int 변환 필수
                current_price = int(curr_price_info.get('stck_prpr') or curr_price_info.get('stck_clpr') or 0)
                if current_price == 0: continue
                
                # 3. [추가하신 조건] 동전주(1,000원 미만) 및 가격 오류(0원) 필터링
                if current_price < 1000:
                    # 로그를 남겨두면 나중에 왜 매수 안 했는지 알 수 있어 좋습니다.
                    # logs.append(f"매수 제외: 동전주 ({cand.item_nm}: {current_price}원)") 
                    continue

                # =========================================================
                # [기존] D. 피벗(Pivot) 지지선 확인 로직
                # =========================================================
                try:
                    # D-1. 전일 시세 데이터 조회
                    prev_candle = session.query(ItemPrice).filter(
                        ItemPrice.item_cd == cand.item_cd,
                        ItemPrice.trade_date < today_str 
                    ).order_by(ItemPrice.trade_date.desc()).first()

                    if prev_candle:
                        # D-2. 피벗 포인트 계산
                        high = int(prev_candle.stck_hgpr)
                        low = int(prev_candle.stck_lwpr)
                        close = int(prev_candle.stck_clpr)

                        pp = (high + low + close) / 3
                        s1 = (2 * pp) - high
                        s2 = pp - (high - low)
                        
                        pivot_support_avg = (s1 + s2) / 2
                        
                        # D-3. 가격 조건 비교 (현재가 > 지지선평균 이면 매수 보류)
                        if current_price > pivot_support_avg:
                            logs.append(f"✋ [매수보류] {cand.item_nm} - 현재가({current_price}) > 지지선평균({int(pivot_support_avg)})")
                            logger.info(f"[{cand.item_nm}] Pivot 미달: Cur({current_price}) > Avg({int(pivot_support_avg)})")
                            continue
                    else:
                        logger.warning(f"[{cand.item_nm}] 전일 시세 없음. Pivot 체크 건너뜀")
                        continue

                except Exception as e:
                    logger.error(f"Pivot 계산 중 오류: {e}")
                    continue
                # =========================================================

                # 매수 수량 계산
                qty = target_amount // current_price
                if qty <= 0: continue
                
                # 매수 주문 실행
                res = self.kis.send_order(
                    order_type="buy",
                    stock_code=cand.item_cd,
                    qty=qty,
                    price=0, # 시장가
                    account_no=self._get_account_no(),
                    account_cd=self._get_account_cd()
                )
                
                if res['success']:
                    msg = f"📈 [매수성공] {cand.item_nm}({cand.item_cd}) {qty}주 - Pivot조건만족"
                    logs.append(msg)
                    logger.info(msg)
                    # DB 기록 시 'buy' 타입으로 저장되므로, 다음 루프부터는 today_bought_codes 체크에 걸리게 됨
                    self._save_trade_history(cand.item_cd, 'buy', qty, current_price, f"점수{cand.total_score}/Pivot지지")
                    
                    # 방금 산 종목도 리스트에 즉시 추가 (한 루프 내 중복 방지 안전장치)
                    today_bought_codes.add(cand.item_cd)
                    buy_count += 1
                else:
                    msg = f"❌ [매수실패] {cand.item_nm} - {res.get('message')}"
                    logs.append(msg)
                    logger.error(msg)
                    
        if buy_count == 0 and not logs:
            logs.append("매수 대상 종목이 없거나 조건(이미매수/Pivot)을 만족하지 못했습니다.")
            
        return logs

    def _get_account_no(self):
        return self.settings.api.kis_real_account_no if self.api_mode == "real" else self.settings.api.kis_mock_account_no

    def _get_account_cd(self):
        return self.settings.api.kis_real_account_cd if self.api_mode == "real" else self.settings.api.kis_mock_account_cd

    def _save_trade_history(self, item_cd, trade_type, qty, price, reason):
        """매매 이력 DB 저장"""
        try:
            with get_session() as session:
                history = TradeHistory(
                    item_cd=item_cd,
                    trade_date=date.today().strftime('%Y%m%d'),
                    trade_time=datetime.now().strftime('%H%M%S'),
                    trade_type=trade_type,
                    quantity=qty,
                    price=price,
                    amount=qty * price,
                    trade_source="auto",
                    trade_reason=reason,
                    created_at=datetime.now()
                )
                session.add(history)
                session.commit()
        except Exception as e:
            logger.error(f"DB 기록 실패: {e}")