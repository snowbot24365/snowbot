package me.project.snowbot.worker;

import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.entity.ItemMst;
import me.project.snowbot.entity.ItemTradeInfo;
import me.project.snowbot.entity.TradeStatus;
import me.project.snowbot.service.ItemMstService;
import me.project.snowbot.service.ItemTradeInfoService;
import me.project.snowbot.service.TradeStatusService;
import me.project.snowbot.service.WorkerService;
import me.project.snowbot.service.WorkerService.CurrentPriceInfo;
import me.project.snowbot.util.CustomDateUtils;
import me.project.snowbot.util.CustomTypeConvert;

/**
 * 정해진 스케줄에 따라 보유 종목의 매도(익절/손절) 로직을 수행하는 스케줄러 컴포넌트이다.
 * 
 * 현재가 조회, 수익률 계산, 지지/저항선 이탈 여부를 판단하여 매도 주문을 실행한다.
 */
@Slf4j
@RequiredArgsConstructor
@Component
public class SellTask {

    private final WorkerService workerService;
    private final ItemTradeInfoService itemTradeInfoService;
    private final TradeStatusService tradeStatusService;
    private final ItemMstService itemMstService;

    // --- 설정 파일에서 주입받는 매도 전략 변수 ---
    
    @Value("${snowbot.trading.sell.up-rate:10.0}")
    private double upRate;        // 익절 기준 수익률 (예: 10%)

    @Value("${snowbot.trading.sell.down-rate:-20.0}")
    private double downRate;      // 손절 기준 수익률 (예: -20%)

    @Value("${snowbot.trading.sell.use-loss-cut:N}")
    private String useLossCut;    // 손절 기능 사용 여부 (Y/N)

    @Value("${snowbot.trading.limit-price:1000000}")
    private long limitPrice;      // 종목당 최대 매수 한도

    @Value("${snowbot.trading.sell.hold-rate:0.8}")
    private double sellHoldRate;  // 매도 보류 비율 (목표 매수 금액 대비 현재 보유량이 적으면 매도 보류)

    // 강제 매도 테스트 플래그 (Y일 경우 조건 무시하고 매도)
    @Value("${snowbot.trading.sell.test-force-sell:N}")
    private String testForceSell;

    /**
     * 매일 장 운영 시간(09:00 ~ 15:59) 동안 30초 간격으로 매도 조건을 점검한다.
     */
    // @Scheduled(cron = "*/30 0-59 9-15 * * *", zone = "Asia/Seoul")
    public void execSellTask() {
        // 1. 현재 보유 중인 스윙(SW) 종목 리스트를 조회한다.
        List<TradeStatus> tradeStatusList = tradeStatusService.getBoughtSWItem(CustomDateUtils.getStringToday());
        
        if (tradeStatusList == null || tradeStatusList.isEmpty()) {
            log.debug("No sell items found.");
            return;
        }

        // 2. 각 보유 종목에 대해 매도 로직을 수행한다.
        tradeStatusList.forEach(tradeStatus -> {
            try {
                processSingleSellItem(tradeStatus);
            } catch (Exception e) {
                log.error("Error processing sell item: {}", tradeStatus.getItemCd(), e);
            }
        });
    }

    /**
     * 단일 보유 종목에 대해 수익률을 계산하고 매도 여부를 결정한다.
     */
    private void processSingleSellItem(TradeStatus tradeStatus) {
        String date = CustomDateUtils.getStringToday();
        String itemCd = tradeStatus.getItemCd();
        int boughtPrice = tradeStatus.getTradePrice(); // 평균 매입가
        int boughtQty = tradeStatus.getQty();          // 보유 수량

        // 1. 종목명 조회 (로그용)
        ItemMst itemMst = itemMstService.findByItem(itemCd);
        String itemNm = Optional.ofNullable(itemMst).map(ItemMst::getItmsNm).orElse(itemCd);

        // 2. 현재가 조회
        CurrentPriceInfo currentPriceInfo = workerService.getCurrentPriceInfo(itemCd);
        int currentPrice = currentPriceInfo.stckPrpr();
        
        if (currentPrice == 0) return; // 현재가 조회 실패 시 중단

        // 3. 수익률 계산 및 DB 현재가 업데이트
        double profitRate = calculateProfit(boughtPrice, currentPrice);
        itemTradeInfoService.updateTradeInfoPrpr(itemCd, date, currentPrice, currentPriceInfo.stckOprc());

        // 현재 매수 종목 정보 로그 출력
        log.info("Sell Check Info: Item={} ({}), Bought={} (Qty={}), Current={}, Profit={}%", 
                itemNm, itemCd, boughtPrice, boughtQty, currentPrice, profitRate);

        // 테스트 플래그가 'Y'이면 조건 체크(4, 5번)를 건너뜀
        if (!"Y".equals(testForceSell)) {
            
            // 4. [매집 구간 체크]
            if ((long) boughtQty * boughtPrice < limitPrice * sellHoldRate) {
                return;
            }

            // 5. 매도 조건(익절/손절) 체크
            if (!isProfitableToSell(itemCd, itemNm, profitRate, currentPrice)) {
                return;
            }
        } else {
            log.warn("[TEST MODE] Force Sell Triggered for {} ({}) - Skipping validation checks.", itemNm, itemCd);
        }

        // 6. 조건을 충족하면 시장가로 전량 매도 주문을 실행한다.
        log.info("Executing Sell Order: {} ({}), Profit: {}%", itemNm, itemCd, profitRate);
        workerService.handleOrder(itemCd, boughtQty, currentPrice, "S");
    }

    /**
     * 현재 수익률과 차트 위치(지지선 이탈 여부)를 기반으로 매도 여부를 판단한다.
     * 
     * * @param itemCd 종목코드
     * @param itemNm 종목명
     * @param profitRate 수익률
     * @param currentPrice 현재가
     * @return 매도 실행 여부 (true: 매도, false: 홀딩)
     */
    private boolean isProfitableToSell(String itemCd, String itemNm, double profitRate, int currentPrice) {
        // 금일의 전략 정보(지지/저항선)를 조회한다.
        ItemTradeInfo itemTradeInfo = itemTradeInfoService.getItemTradeInfo(itemCd, CustomDateUtils.getStringToday());
        
        // 1차 지지선(S1)을 매도 기준가(Trailing Stop Line)로 설정한다.
        // S1이 없으면 S2, S3의 평균을 사용한다.
        int stopLinePrice = calculateStopLinePrice(itemTradeInfo.getS1(), itemTradeInfo.getS2(), itemTradeInfo.getS3());

        // [방어 로직] 설정값 유효성 체크
        if ((profitRate < 0 && downRate > 0) || (profitRate > 0 && upRate < 0)) {
            return false; 
        }

        // 1. [익절 조건] 수익률이 목표치(upRate)를 초과했을 때
        if (profitRate >= upRate) {
            // 지지선(S1) 정보가 없으면 즉시 익절한다.
            if (stopLinePrice == 0) return true;

            // 트레일링 스탑: 수익 구간이지만, 주가가 지지선(S1) 아래로 내려가면 이익 실현한다.
            // (주가가 계속 오르면 매도하지 않고 수익을 극대화한다.)
            if (currentPrice < stopLinePrice) {
                log.info("Trailing Stop Triggered: {} profit={}%, current={}, stopLine={}", itemNm, profitRate, currentPrice, stopLinePrice);
                return true;
            }
            return false;
        }

        // 2. [손절 조건] 수익률이 손절선(downRate) 미만으로 떨어졌을 때
        if ("Y".equals(useLossCut) && profitRate <= downRate) {
            log.info("Loss Cut Triggered: {} profit={}%, limit={}%", itemNm, profitRate, downRate);
            return true;
        }

        return false;
    }

    /**
     * 매도 기준선(Stop Line)을 계산한다.
     * 기본적으로 1차 지지선(S1)을 사용하며, S1이 없을 경우 다른 지지선들의 평균을 사용한다.
     */
    private int calculateStopLinePrice(Integer priorityPrice, Integer... otherPrices) {
        // 최우선 기준가(S1)가 존재하면 해당 값을 사용한다.
        if (priorityPrice != null && priorityPrice > 0) {
            return priorityPrice;
        }

        // S1이 없으면 나머지 지지선들의 평균을 계산한다.
        return (int) Arrays.stream(otherPrices)
                .filter(Objects::nonNull)
                .mapToInt(Integer::intValue)
                .average()
                .orElse(0);
    }

    /**
     * 수익률을 계산한다. (소수점 둘째 자리 반올림)
     */
    private double calculateProfit(double boughtPrice, double currentPrice) {
        if (boughtPrice == 0) return 0.0;
        
        double profit = ((currentPrice - boughtPrice) / boughtPrice) * 100;
        return Math.round(profit * 100.0) / 100.0;
    }
}