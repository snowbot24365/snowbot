package me.project.snowbot.service;

import java.util.Arrays;
import java.util.Collections;
import java.util.Map;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.Body;
import me.project.snowbot.dto.SheetData;
import me.project.snowbot.dto.TwoArrData;
import me.project.snowbot.entity.ItemMst;
import me.project.snowbot.entity.TradeStatus;
import me.project.snowbot.util.CustomDateUtils;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 주식 잔고 조회, 현재가 조회, 보유 종목 현행화, 주문 처리 등 실제 매매 보조 업무를 수행하는 워커 서비스이다.
 * KIS API 호출 결과를 가공하여 비즈니스 로직에 맞게 데이터를 제공하고 DB 상태를 동기화한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class WorkerService {

    private final KisService kisService;
    private final TradeStatusService tradeStatusService;
    private final ItemTradeInfoService itemTradeInfoService;
    private final ItemMstService itemMstService;
    private final SlackService slackService;
    private final TradeHistoryService tradeHistoryService;

    @Value("${kis.account-no}")
    private String accountNo;

    @Value("${kis.account-cd}")
    private String accountCd;

    // --- 상수 정의 ---
    private static final String TRADE_TYPE_BUY_STOP = "BS";  // 매수
    private static final String TRADE_TYPE_SELL_STOP = "SS"; // 매도
    private static final String STRATEGY_SWING = "SW";       // 스윙 전략
    private static final String YES = "Y";
    private static final String NO = "N";

    /**
     * 계좌의 예수금 정보를 조회하여 반환하는 메서드이다.
     * API 응답(`TwoArrData`)의 `output2` 배열에서 데이터를 추출하며, 가수금 여부를 확인하여 실질적인 주문 가능 금액을 계산한다.
     *
     * @return 계산된 예수금 금액이다.
     */
    public int getAccountBalance() {
        TwoArrData twoArrData = kisService.getAccountBalance(accountNo, accountCd, "01");
        
        // output2는 Object[] 타입이므로 배열 처리 헬퍼 메서드를 사용하여 첫 번째 데이터를 맵으로 변환한다.
        return extractFirstMapFromArray(twoArrData != null ? twoArrData.getOutput2() : null)
                .map(output2 -> {
                    // 가수금(prvs_rcdl_excc_amt)이 있으면 우선 사용하고, 없으면 예수금총액(dnca_tot_amt)을 사용한다.
                    int prvsRcdl = CustomTypeConvert.convInteger(output2.get("prvs_rcdl_excc_amt"));
                    return prvsRcdl > 0 ? prvsRcdl : CustomTypeConvert.convInteger(output2.get("dnca_tot_amt"));
                })
                .orElse(0);
    }

    /**
     * 특정 종목의 시가, 고가, 저가, 현재가 정보를 조회하여 `CurrentPriceInfo` DTO 객체로 반환한다.
     * 데이터가 없거나 오류 발생 시 0으로 초기화된 객체를 반환한다.
     *
     * @param itemId 종목 코드이다.
     * @return 현재가 정보가 담긴 Record 객체이다.
     */
    public CurrentPriceInfo getCurrentPriceInfo(String itemId) {
        Map<String, Object> infoMap = getCurrentPriceInfoMap(itemId);
        
        if (infoMap == null || infoMap.isEmpty()) {
            return new CurrentPriceInfo(0, 0, 0, 0);
        }

        return new CurrentPriceInfo(
                CustomTypeConvert.convInteger(infoMap.get("stck_oprc")),
                CustomTypeConvert.convInteger(infoMap.get("stck_hgpr")),
                CustomTypeConvert.convInteger(infoMap.get("stck_lwpr")),
                CustomTypeConvert.convInteger(infoMap.get("stck_prpr"))
        );
    }

    public record CurrentPriceInfo(int stckOprc, int stckHgpr, int stckLwpr, int stckPrpr) {}

    /**
     * 특정 종목의 현재가 상세 정보를 조회하여 Map 형태로 반환한다.
     * 특히 장 시작 전이나 일시적인 데이터 오류로 시가(Open Price)가 0인 경우, 
     * 일별 시세 데이터를 추가로 조회하여 보정하는 로직을 포함한다.
     *
     * @param id 종목 코드이다.
     * @return 현재가 정보 Map이다. (stck_prpr, stck_oprc, stck_hgpr, stck_lwpr, orpr_rate)
     */
    public Map<String, Object> getCurrentPriceInfoMap(String id) {
        try {
            Body body = kisService.getEquities(id);
            if (body == null || body.getOutput() == null) {
                return Collections.emptyMap();
            }

            Map<String, Object> output = (Map<String, Object>) body.getOutput();

            int prpr = CustomTypeConvert.convInteger(output.get("stck_prpr")); // 현재가
            int hgpr = CustomTypeConvert.convInteger(output.get("stck_hgpr")); // 고가
            int lwpr = CustomTypeConvert.convInteger(output.get("stck_lwpr")); // 저가
            
            // 시가 보정 로직: 시가가 0이면 과거 데이터(Daily Price)에서 가져온다.
            int oprc = CustomTypeConvert.convInteger(output.get("stck_oprc"));
            if (oprc == 0) {
                oprc = getFallbackOpenPrice(id);
            }

            // 시가 대비 현재가 등락률 계산
            double orprRate = calculateRateOfChange(oprc, prpr);

            return Map.of(
                    "stck_prpr", prpr,
                    "stck_oprc", oprc,
                    "stck_hgpr", hgpr,
                    "stck_lwpr", lwpr,
                    "orpr_rate", orprRate
            );

        } catch (Exception e) {
            log.error("Error fetching price info for item: {}", id, e);
            return Collections.emptyMap();
        }
    }

    /**
     * 현재 증권사 계좌에 보유 중인 종목 리스트를 조회하여, 로컬 데이터베이스의 매매 상태(TradeStatus)와 전략 정보(ItemTradeInfo)를 동기화(현행화)한다.
     * `TwoArrData.output1` 배열을 스트림으로 순회하며 처리한다.
     *
     * @param date 기준 날짜
     * @param limitPrice 종목당 최대 매수 한도 금액
     */
    public void updateHoldSwingItems(String date, long limitPrice) {
        TwoArrData twoArrData = kisService.getAccountBalance(accountNo, accountCd, "01");

        if (twoArrData == null || twoArrData.getOutput1() == null) {
            return;
        }

        // Object[] 배열을 스트림으로 변환하여 각 보유 종목을 처리한다.
        Arrays.stream(twoArrData.getOutput1())
                .map(obj -> (Map<String, Object>) obj)
                .forEach(output -> processHoldItem(output, date, limitPrice));
    }

    /**
     * 특정 종목에 대한 매수 또는 매도 주문을 실행하는 메서드이다.
     * KIS API를 통해 주문을 전송하고, 주문 유형(B/S)에 따라 결과를 처리하는 로직으로 연결된다.
     *
     * @param itemId 종목 코드
     * @param qty 주문 수량
     * @param price 주문 단가
     * @param orderType 주문 유형 ("B": 매수, "S": 매도)
     */
    public void handleOrder(String itemId, int qty, int price, String orderType) {
        // "00"은 지정가 주문을 의미한다.
        Body orderResult = kisService.orderItem(orderType, itemId, accountNo, "00", qty, price);
        
        // 주문 결과 처리를 위해 orderType을 함께 전달한다.
        handleOrderResult(orderResult, itemId, qty, price, orderType);
    }

    // --- Private Helper Methods ---

    /**
     * 주문 요청에 대한 응답 결과를 분석하여 후속 처리를 수행하는 내부 메서드이다.
     * 주문 유형(B/S)에 따라 매매 상태(TradeStatus)를 'BS(매수 후 보유)' 또는 'SS(매도 후 관망)'으로 업데이트하고,
     * 적절한 슬랙 알림 메시지를 생성하여 발송한다.
     *
     * @param orderResult API 응답 Body
     * @param itemId 종목 코드
     * @param qty 주문 수량
     * @param price 주문 단가
     * @param orderType 주문 유형
     */
    @SuppressWarnings("unchecked")
    private void handleOrderResult(Body orderResult, String itemId, int qty, int price, String orderType) {
        // 1. 주문 유형에 따른 상태값 및 메시지 텍스트를 결정한다.
        boolean isBuy = "B".equals(orderType);
        String targetStatus = isBuy ? TRADE_TYPE_BUY_STOP : TRADE_TYPE_SELL_STOP; // "B" -> "BS", "S" -> "SS"
        String actionName = isBuy ? "매수" : "매도";
        String logPrefix = isBuy ? "SnowBot-Swing-Buy" : "SnowBot-Swing-Sell";

        // 2. 결과 코드(rt_cd)가 "0"이면 주문 성공이다.
        if ("0".equals(orderResult.getRt_cd())) {
            Map<String, Object> output = (Map<String, Object>) orderResult.getOutput();
            if (output != null) {
                ItemMst itemMst = itemMstService.findByItem(itemId);
                String oOdno = String.valueOf(output.get("ODNO"));   // 주문번호 추출

                // 3. 결정된 상태값(targetStatus)으로 DB를 업데이트한다.
                tradeStatusService.updateTradeStatus(itemId, CustomDateUtils.getStringToday(), targetStatus, oOdno, qty, 0, price);
                
                // 4. 결정된 행동 명칭(actionName)으로 슬랙 메시지를 발송한다.
                String result = String.format("%s %s (%s-%s) %s 했습니다. 수량은 %d 이고, 단가는 %d원 입니다.", 
                        logPrefix, itemMst.getItmsNm(), itemId, STRATEGY_SWING, actionName, qty, price);
                slackService.sendMessage(result);

                // 5. trade 히스토리 추가
                tradeHistoryService.saveHistory(itemId, CustomDateUtils.getStringToday(), CustomDateUtils.getTime(), orderType, qty, price, result);
            } else {
                String result = String.format("%s Result (Swing) = order item error!! : %s, %s", logPrefix, itemId, orderResult.getMsg1());
                log.error(result);
            }
        } else {
            // 주문 실패 (예수금 부족, 잔고 부족 등)
            log.warn("{} Result (Swing) = Insufficient amount or API Error!! msg: {}", logPrefix, orderResult.getMsg1());
        }
    }

    /**
     * 개별 보유 종목의 매입 금액, 수량 등을 분석하여 매수 중지(Buy Stop) 또는 매도 중지(Sell Stop) 상태를 업데이트한다.
     * 또한 매입 금액이 설정된 한도를 초과했는지 여부를 판단하여 전략 정보(ItemTradeInfo)에 반영한다.
     */
    private void processHoldItem(Map<String, Object> output, String date, long limitPrice) {
        String pdno = String.valueOf(output.get("pdno"));       // 종목번호
        String pdnm = String.valueOf(output.get("prdt_name"));  // 종목명
        double pchsAmt = CustomTypeConvert.convDouble(output.get("pchs_amt")); // 매입금액
        double boughtPrice = CustomTypeConvert.convDouble(output.get("pchs_avg_pric")); // 매입평균가
        double boughtCount = CustomTypeConvert.convDouble(output.get("hldg_qty"));      // 보유수량

        TradeStatus currentStatus = tradeStatusService.getTradeStatus(pdno, date);

        // 이미 오늘 'SS'(매도) 처리가 된 종목이라면, API 잔고에 남아있더라도 건너뛴다.
        // (매도 주문 직후에는 잔고에 일시적으로 남아있을 수 있기 때문)
        if (currentStatus != null && TRADE_TYPE_SELL_STOP.equals(currentStatus.getTradeType())) {
            log.debug("Skipping updateHoldSwingItems for sold item: {}", pdno);
            return;
        }

        // 실제 매입금액이 존재하는 경우 (보유 중)
        if (pchsAmt > 0) {
            tradeStatusService.updateTradeStatus(pdno, date, TRADE_TYPE_BUY_STOP, "", (int) boughtCount, 0, (int) boughtPrice);

            // 총 평가 금액이 한도를 넘으면 추가 매수 금지(N), 넘지 않으면 가능(Y)으로 설정
            double totalValue = boughtCount * boughtPrice;
            String possibility = (totalValue > limitPrice) ? NO : YES;
            String remark = (totalValue > limitPrice) ? "swing bought item(buy-stop)" : "swing bought item";

            itemTradeInfoService.saveItemTradeInfoByLast(pdno, date, possibility, STRATEGY_SWING, remark);

            log.info("OrderTask Result (Swing) = 보유종목 현행화 item : {} ({})", pdno, pdnm);
        } else {
            // 잔고에는 있으나 매입금액이 0인 경우 (전량 매도 후 등)
            tradeStatusService.updateTradeStatus(pdno, date, TRADE_TYPE_SELL_STOP, "", (int) boughtCount, 0, (int) boughtPrice);
        }
    }

    /**
     * 시가가 0으로 조회될 때, 과거 일별 시세 데이터에서 가장 최근의 시가를 조회하여 반환한다.
     * SheetData의 `output` 필드도 `Object[]` 배열이므로 헬퍼 메서드를 사용한다.
     */
    private int getFallbackOpenPrice(String id) {
        SheetData sheetData = kisService.getDailyPrice(id);
        
        return extractFirstMapFromArray(sheetData != null ? sheetData.getOutput() : null)
                .map(map -> CustomTypeConvert.convInteger(map.get("stck_oprc")))
                .orElse(0);
    }

    /**
     * `Object[]` 배열 형태의 API 응답 데이터에서 첫 번째 요소를 안전하게 추출하여 `Map`으로 변환한다.
     * `TwoArrData.output1`, `TwoArrData.output2`, `SheetData.output` 등 모든 배열형 필드 처리에 사용된다.
     *
     * @param outputArray 변환할 Object 배열
     * @return 첫 번째 요소의 Map Optional 객체
     */
    @SuppressWarnings("unchecked")
    private Optional<Map<String, Object>> extractFirstMapFromArray(Object[] outputArray) {
        if (outputArray == null || outputArray.length == 0) {
            return Optional.empty();
        }
        return Optional.ofNullable((Map<String, Object>) outputArray[0]);
    }

    /**
     * 시가 대비 현재가의 등락률을 계산하는 메서드이다.
     */
    private double calculateRateOfChange(double startPrice, double currentPrice) {
        if (startPrice == 0) {
            return 0.0;
        }
        return ((currentPrice - startPrice) / startPrice) * 100;
    }
}