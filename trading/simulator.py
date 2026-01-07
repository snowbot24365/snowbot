"""
시뮬레이션 엔진
- 가상 계좌 관리
- 가상 매수/매도 처리
- 수수료, 세금 계산
"""

import logging
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import uuid

from config.settings import get_settings_manager
from config.database import (
    get_session, VirtualAccount, VirtualHolding, 
    TradeHistory, ItemMst
)
from data.price_fetcher import PriceFetcher

logger = logging.getLogger(__name__)


@dataclass
class OrderResult:
    """주문 결과"""
    success: bool
    order_no: str = ""
    item_cd: str = ""
    item_nm: str = ""
    order_type: str = ""  # 'B' or 'S'
    qty: int = 0
    price: int = 0
    amount: int = 0
    fee: int = 0
    tax: int = 0
    message: str = ""
    
    @property
    def total_amount(self) -> int:
        """총 거래금액 (수수료, 세금 포함)"""
        if self.order_type == 'B':
            return self.amount + self.fee
        else:
            return self.amount - self.fee - self.tax


@dataclass
class HoldingInfo:
    """보유 종목 정보"""
    item_cd: str
    item_nm: str
    qty: int
    avg_price: int
    current_price: int
    eval_amt: int
    profit: int
    profit_rate: float
    buy_date: str


@dataclass
class AccountInfo:
    """계좌 정보"""
    balance: int
    total_eval: int
    total_profit: int
    total_profit_rate: float
    holdings: List[HoldingInfo]


class SimulationEngine:
    """시뮬레이션 엔진"""
    
    def __init__(self):
        self.settings_manager = get_settings_manager()
        self.price_fetcher = PriceFetcher()
        
        # 계좌 초기화
        self._initialize_account()
    
    def _initialize_account(self):
        """가상 계좌 초기화"""
        with get_session() as session:
            account = session.query(VirtualAccount).first()
            
            if not account:
                initial_balance = self.settings_manager.settings.trading.initial_balance
                account = VirtualAccount(
                    balance=initial_balance,
                    total_eval=initial_balance,
                    total_profit=0,
                    total_profit_rate=0.0
                )
                session.add(account)
                logger.info(f"가상 계좌 초기화: {initial_balance:,}원")
    
    def get_account_info(self) -> AccountInfo:
        """계좌 정보 조회"""
        with get_session() as session:
            account = session.query(VirtualAccount).first()
            holdings = session.query(VirtualHolding).all()
            
            holding_list = []
            balance = account.balance if account else 0
            total_eval = balance
            total_cost = 0
            
            for h in holdings:
                # 현재가 업데이트
                price_info = self.price_fetcher.get_current_price(h.item_cd)
                if price_info:
                    h.current_price = price_info['price']
                    h.eval_amt = h.qty * h.current_price
                    cost = h.qty * h.avg_price
                    h.profit = h.eval_amt - cost
                    h.profit_rate = (h.profit / cost * 100) if cost else 0
                    total_cost += cost
                
                holding_list.append(HoldingInfo(
                    item_cd=h.item_cd,
                    item_nm=h.item_nm or h.item_cd,
                    qty=h.qty,
                    avg_price=h.avg_price,
                    current_price=h.current_price or 0,
                    eval_amt=h.eval_amt or 0,
                    profit=h.profit or 0,
                    profit_rate=h.profit_rate or 0.0,
                    buy_date=h.buy_date or ''
                ))
                
                total_eval += h.eval_amt or 0
            
            # 총손익 계산
            initial_balance = self.settings_manager.settings.trading.initial_balance
            total_profit = total_eval - initial_balance
            total_profit_rate = (total_profit / initial_balance * 100) if initial_balance else 0
            
            return AccountInfo(
                balance=balance,
                total_eval=total_eval,
                total_profit=total_profit,
                total_profit_rate=total_profit_rate,
                holdings=holding_list
            )
    
    def get_balance(self) -> int:
        """예수금 잔고 조회"""
        with get_session() as session:
            account = session.query(VirtualAccount).first()
            return account.balance if account else 0
    
    def reset_account(self):
        """계좌 초기화 (리셋)"""
        initial_balance = self.settings_manager.settings.trading.initial_balance
        
        with get_session() as session:
            # 보유 종목 삭제
            session.query(VirtualHolding).delete()
            
            # 계좌 초기화
            account = session.query(VirtualAccount).first()
            if account:
                account.balance = initial_balance
                account.total_eval = initial_balance
                account.total_profit = 0
                account.total_profit_rate = 0
            else:
                account = VirtualAccount(
                    balance=initial_balance,
                    total_eval=initial_balance,
                    total_profit=0,
                    total_profit_rate=0.0
                )
                session.add(account)
        
        logger.info(f"계좌 초기화 완료: {initial_balance:,}원")
    
    def calculate_fee(self, amount: int) -> int:
        """수수료 계산"""
        settings = self.settings_manager.settings.trading
        if settings.apply_fee:
            return int(amount * settings.fee_rate)
        return 0
    
    def calculate_tax(self, amount: int) -> int:
        """세금 계산 (매도 시에만)"""
        settings = self.settings_manager.settings.trading
        if settings.apply_fee:
            return int(amount * settings.tax_rate)
        return 0
    
    def buy(self, item_cd: str, qty: int, price: int = 0) -> OrderResult:
        """
        매수 주문
        
        Args:
            item_cd: 종목코드
            qty: 매수 수량
            price: 매수 가격 (0이면 현재가)
        
        Returns:
            OrderResult
        """
        result = OrderResult(
            success=False,
            item_cd=item_cd,
            order_type='B'
        )
        
        try:
            # 1. 현재가 조회
            if price == 0:
                price_info = self.price_fetcher.get_current_price(item_cd)
                if not price_info:
                    result.message = "현재가 조회 실패"
                    return result
                price = price_info['price']
            
            result.price = price
            result.qty = qty
            result.amount = price * qty
            result.fee = self.calculate_fee(result.amount)
            
            total_cost = result.amount + result.fee
            
            # 2. 잔고 확인
            with get_session() as session:
                account = session.query(VirtualAccount).first()
                
                if not account or account.balance < total_cost:
                    result.message = f"잔고 부족 (필요: {total_cost:,}, 보유: {account.balance if account else 0:,})"
                    return result
                
                # 3. 종목명 조회
                item = session.query(ItemMst).filter(
                    ItemMst.item_cd == item_cd
                ).first()
                item_nm = item.itms_nm if item else item_cd
                result.item_nm = item_nm
                
                # 4. 잔고 차감
                account.balance -= total_cost
                
                # 5. 보유 종목 업데이트
                holding = session.query(VirtualHolding).filter(
                    VirtualHolding.item_cd == item_cd
                ).first()
                
                today = date.today().strftime('%Y%m%d')
                
                if holding:
                    # 기존 보유 종목 - 평균 매입가 계산
                    total_qty = holding.qty + qty
                    total_cost_old = holding.qty * holding.avg_price
                    total_cost_new = result.amount
                    holding.avg_price = int((total_cost_old + total_cost_new) / total_qty)
                    holding.qty = total_qty
                    holding.current_price = price
                    holding.eval_amt = total_qty * price
                else:
                    # 신규 보유
                    holding = VirtualHolding(
                        item_cd=item_cd,
                        item_nm=item_nm,
                        qty=qty,
                        avg_price=price,
                        current_price=price,
                        eval_amt=result.amount,
                        profit=0,
                        profit_rate=0.0,
                        buy_date=today
                    )
                    session.add(holding)
                
                # 6. 거래 이력 저장
                order_no = f"SIM{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
                
                history = TradeHistory(
                    item_cd=item_cd,
                    trade_date=today,
                    trade_time=datetime.now().strftime('%H%M%S'),
                    trade_type='B',
                    qty=qty,
                    price=price,
                    fee=result.fee,
                    tax=0,
                    rmk=f"시뮬레이션 매수: {item_nm}"
                )
                session.add(history)
                
                result.success = True
                result.order_no = order_no
                result.message = f"매수 완료: {item_nm} {qty}주 @ {price:,}원"
                
                logger.info(result.message)
                
        except Exception as e:
            result.message = f"매수 처리 오류: {str(e)}"
            logger.error(result.message)
        
        return result
    
    def sell(self, item_cd: str, qty: int, price: int = 0) -> OrderResult:
        """
        매도 주문
        
        Args:
            item_cd: 종목코드
            qty: 매도 수량 (0이면 전량)
            price: 매도 가격 (0이면 현재가)
        
        Returns:
            OrderResult
        """
        result = OrderResult(
            success=False,
            item_cd=item_cd,
            order_type='S'
        )
        
        try:
            # 1. 보유 종목 확인
            with get_session() as session:
                holding = session.query(VirtualHolding).filter(
                    VirtualHolding.item_cd == item_cd
                ).first()
                
                if not holding:
                    result.message = "보유하지 않은 종목입니다."
                    return result
                
                result.item_nm = holding.item_nm or item_cd
                
                # 전량 매도
                if qty == 0:
                    qty = holding.qty
                
                if qty > holding.qty:
                    result.message = f"보유 수량 부족 (보유: {holding.qty}, 요청: {qty})"
                    return result
                
                # 2. 현재가 조회
                if price == 0:
                    price_info = self.price_fetcher.get_current_price(item_cd)
                    if not price_info:
                        result.message = "현재가 조회 실패"
                        return result
                    price = price_info['price']
                
                result.price = price
                result.qty = qty
                result.amount = price * qty
                result.fee = self.calculate_fee(result.amount)
                result.tax = self.calculate_tax(result.amount)
                
                # 3. 손익 계산
                buy_amount = holding.avg_price * qty
                sell_amount = result.amount - result.fee - result.tax
                profit = sell_amount - buy_amount
                profit_rate = (profit / buy_amount * 100) if buy_amount else 0
                
                # 4. 계좌 잔고 업데이트
                account = session.query(VirtualAccount).first()
                account.balance += sell_amount
                
                # 5. 보유 종목 업데이트
                today = date.today().strftime('%Y%m%d')
                
                if qty >= holding.qty:
                    # 전량 매도 - 보유 종목 삭제
                    session.delete(holding)
                else:
                    # 일부 매도
                    holding.qty -= qty
                    holding.eval_amt = holding.qty * price
                
                # 6. 거래 이력 저장
                order_no = f"SIM{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
                
                history = TradeHistory(
                    item_cd=item_cd,
                    trade_date=today,
                    trade_time=datetime.now().strftime('%H%M%S'),
                    trade_type='S',
                    qty=qty,
                    price=price,
                    fee=result.fee,
                    tax=result.tax,
                    profit=profit,
                    profit_rate=round(profit_rate, 2),
                    rmk=f"시뮬레이션 매도: {holding.item_nm or item_cd} (손익: {profit:+,}원, {profit_rate:+.2f}%)"
                )
                session.add(history)
                
                result.success = True
                result.order_no = order_no
                result.message = f"매도 완료: {holding.item_nm} {qty}주 @ {price:,}원 (손익: {profit:+,}원)"
                
                logger.info(result.message)
                
        except Exception as e:
            result.message = f"매도 처리 오류: {str(e)}"
            logger.error(result.message)
        
        return result
    
    def get_holding(self, item_cd: str) -> Optional[HoldingInfo]:
        """특정 종목 보유 정보 조회"""
        with get_session() as session:
            holding = session.query(VirtualHolding).filter(
                VirtualHolding.item_cd == item_cd
            ).first()
            
            if not holding:
                return None
            
            # 현재가 업데이트
            price_info = self.price_fetcher.get_current_price(item_cd)
            if price_info:
                holding.current_price = price_info['price']
                holding.eval_amt = holding.qty * holding.current_price
                cost = holding.qty * holding.avg_price
                holding.profit = holding.eval_amt - cost
                holding.profit_rate = (holding.profit / cost * 100) if cost else 0
            
            return HoldingInfo(
                item_cd=holding.item_cd,
                item_nm=holding.item_nm or holding.item_cd,
                qty=holding.qty,
                avg_price=holding.avg_price,
                current_price=holding.current_price or 0,
                eval_amt=holding.eval_amt or 0,
                profit=holding.profit or 0,
                profit_rate=holding.profit_rate or 0.0,
                buy_date=holding.buy_date or ''
            )
    
    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        """거래 이력 조회"""
        with get_session() as session:
            histories = session.query(TradeHistory).order_by(
                TradeHistory.trade_date.desc(),
                TradeHistory.trade_time.desc()
            ).limit(limit).all()
            
            return [
                {
                    'id': h.id,
                    'item_cd': h.item_cd,
                    'trade_date': h.trade_date,
                    'trade_time': h.trade_time,
                    'trade_type': '매수' if h.trade_type == 'B' else '매도',
                    'qty': h.qty,
                    'price': h.price,
                    'amount': h.qty * h.price if h.qty and h.price else 0,
                    'fee': h.fee or 0,
                    'tax': h.tax or 0,
                    'profit': h.profit or 0,
                    'profit_rate': h.profit_rate or 0,
                    'rmk': h.rmk or ''
                }
                for h in histories
            ]
