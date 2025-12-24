package me.project.snowbot.worker;

import java.util.Arrays;
import java.util.List;
import java.util.Objects;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.entity.ItemTradeInfo;
import me.project.snowbot.entity.TradeHistory;
import me.project.snowbot.entity.TradeStatus;
import me.project.snowbot.service.ItemTradeInfoService;
import me.project.snowbot.service.TradeHistoryService;
import me.project.snowbot.service.TradeStatusService;
import me.project.snowbot.service.WorkerService;
import me.project.snowbot.service.WorkerService.CurrentPriceInfo;
import me.project.snowbot.util.CustomDateUtils;

/**
 * 정해진 스케줄에 따라 매수 로직을 수행하는 스케줄러 컴포넌트이다.
 * 
 * 계좌 잔고 확인, 보유 종목 동기화, 매수 대상 선정, 가격 분석, 주문 실행의 단계를 거친다.
 */
@Slf4j
@RequiredArgsConstructor
@Component
public class BuyTask {

    private final WorkerService workerService;
    private final ItemTradeInfoService itemTradeInfoService;
    private final TradeStatusService tradeStatusService;
    private final TradeHistoryService tradeHistoryService;

    // 설정 파일(application.yml)에서 값을 주입받아 유연하게 관리한다.
    @Value("${snowbot.trading.contract-rate}")
    private double contractRate; // 1회 매수 시 예수금 대비 비율 (예: 10%)

    @Value("${snowbot.trading.limit-price}")
    private long limitPrice;     // 종목당 최대 매수 한도 금액

    @Value("${snowbot.trading.limit-cnt}")
    private int limitCnt;        // 최대 보유 종목 수

    @Value("${snowbot.trading.buy.use-yn}")
    private String useYn;        // 매수 로직 사용 여부

    // 강제 매도 테스트 플래그 (Y일 경우 조건 무시하고 매도)
    @Value("${snowbot.trading.buy.test-force-buy:N}")
    private String testForceBuy;

    /**
     * 매일 오전 9시부터 오후 3시 59분 59초까지, 30초 간격으로 매수 작업을 실행한다.
     * 장 운영 시간(09:00 ~ 15:30)을 커버하며, 장 마감 직후 데이터 정리까지 고려된 시간이다.
     */
    // @Scheduled(cron = "*/30 0-59 9-15 * * *", zone = "Asia/Seoul")
    public void execBuyTask() {
        // 1. 계좌의 예수금 잔고를 확인한다. 잔고가 없으면 로직을 수행하지 않는다.
        int currentBalance = workerService.getAccountBalance();
        if (currentBalance == 0) {
            log.warn("No available account with balance to trade.");
            return;
        }

        // 2. 현재 보유 중인 종목 정보를 증권사 API와 동기화(현행화)한다.
        workerService.updateHoldSwingItems(CustomDateUtils.getStringToday(), limitPrice);

        // 3. 매수 기능 사용 여부(USE_YN)를 확인하고 로직을 진행한다.
        if ("Y".equals(useYn)) {
            processBuyItems(currentBalance);
        } else {
            log.info("Buy Task is disabled via configuration.");
        }
    }

    /**
     * 매수 대상 종목 리스트를 조회하고, 각 종목에 대해 개별 매수 프로세스를 수행한다.
     *
     * @param currentBalance 현재 예수금 잔고
     */
    private void processBuyItems(int currentBalance) {
        // DB에 저장된 매수 후보 종목(SW 전략)을 조회한다.
        List<ItemTradeInfo> itemTradeInfoList = itemTradeInfoService.getBuySWItems(CustomDateUtils.getStringToday());

        if (itemTradeInfoList == null || itemTradeInfoList.isEmpty()) {
            log.debug("No buy targets found for today.");
            return;
        }

        // 각 종목별로 예외가 발생하더라도 다른 종목 처리에 영향을 주지 않도록 개별 try-catch로 감싼다.
        itemTradeInfoList.forEach(itemTradeInfo -> {
            try {
                processSingleBuyItem(itemTradeInfo, currentBalance);
            } catch (Exception e) {
                log.error("Error processing buy item: {}", itemTradeInfo.getId().getItem_cd(), e);
            }
        });
    }

    /**
     * 단일 종목에 대해 매수 가능 여부를 판단하고 주문을 실행한다.
     * 보유 한도 체크 -> 현재가 조회 -> 지표 업데이트 -> 수익성 판단 -> 주문 실행 순으로 진행된다.
     */
    private void processSingleBuyItem(ItemTradeInfo itemTradeInfo, int currentBalance) {
        String itemId = itemTradeInfo.getId().getItem_cd();
        String type = itemTradeInfo.getCd_type() != null ? itemTradeInfo.getCd_type() : "SW";

        // 1. 최대 보유 종목 수 제한을 체크한다. (이미 보유 중이거나 한도 초과 시 스킵)
        if (!isValidItemForBuying(itemId)) {
            log.info("Skipping item {}: Holding limit reached ({})", itemId, limitCnt);
            return;
        }

        // 2. 실시간 현재가를 조회한다. 장전/장후 등 시세가 없는 경우 중단한다.
        CurrentPriceInfo currentPriceInfo = workerService.getCurrentPriceInfo(itemId);
        if (currentPriceInfo.stckPrpr() == 0) {
            return;
        }

        String today = CustomDateUtils.getStringToday();

        // 3. DB에 현재가 정보를 업데이트한다.
        itemTradeInfoService.updateTradeInfoPrpr(
                itemId,
                today,
                currentPriceInfo.stckPrpr(),
                currentPriceInfo.stckOprc()
        );

        // 4. 피벗(Pivot), 지지(S), 저항(R) 라인을 재계산하여 업데이트한다.
        // 장중 고가/저가 변동에 따라 지표가 달라질 수 있기 때문이다.
        itemTradeInfoService.updateTradeInfoPoint(
                itemId,
                today,
                currentPriceInfo.stckOprc(),
                currentPriceInfo.stckHgpr(),
                currentPriceInfo.stckLwpr(),
                type
        );

        // 과거 매수 기록 있어도 조건 만족시 당일 추가 매수
        // 단, 당일 매매 기록 있으면 skip
        TradeHistory tradeHistory = tradeHistoryService.getBoughtItemInfo(itemId, CustomDateUtils.getStringToday());
        if (tradeHistory != null) {
            return;
        }

        if (!"Y".equals(testForceBuy)) {
            // 5. 현재 가격이 매수 목표가(지지선 평균) 이하인지 확인한다.
            if (!isProfitableToBuy(currentPriceInfo, itemTradeInfo, itemId)) {
                return;
            }
        } else {
            log.warn("[TEST MODE] Force Buy Triggered for {} - Skipping validation checks.", itemId);
        }

        // 6. 모든 조건을 만족하면 매수 주문을 실행한다.
        executeBuyOrder(itemId, currentBalance, currentPriceInfo);
    }

    /**
     * 신규 매수가 가능한 상태인지 검증한다.
     * 현재 보유 종목 수가 제한(LIMIT_CNT)에 도달했는지 확인하되, 이미 보유 중인 종목이라면 추가 매수를 허용한다.
     */
    private boolean isValidItemForBuying(String itemId) {
        // DB에서 현재 보유 중인 종목 리스트를 조회한다.
        List<TradeStatus> tradeStatusList = tradeStatusService.getBoughtSWItem(CustomDateUtils.getStringToday());
        
        if (tradeStatusList.size() >= limitCnt) {
            // 보유 한도가 꽉 찼을 때, 해당 종목이 이미 보유 리스트에 있다면(추가매수) true, 아니면 false
            return tradeStatusList.stream()
                    .anyMatch(tradeStatus -> itemId.equals(tradeStatus.getItemCd()));
        }
        return true;
    }

    /**
     * 현재 가격이 매수 전략에 부합하는지 판단한다.
     * 전략: 현재가가 지지선(S1, S2, S3)들의 평균값보다 낮을 때 매수한다. (눌림목 매수)
     */
    private boolean isProfitableToBuy(CurrentPriceInfo currentPriceInfo, ItemTradeInfo itemTradeInfo, String itemId) {
        int buyTargetPriceS = calculateAveragePrice(itemTradeInfo.getS1(), itemTradeInfo.getS2(), itemTradeInfo.getS3());
        int buyTargetPriceR = calculateAveragePrice(itemTradeInfo.getR1(), itemTradeInfo.getR2(), itemTradeInfo.getR3());

        log.info("SnowBot-Swing-Buy Analysis : item={}, current={}, target(S_Avg)={}, target(R_Avg)={}",
                itemId, currentPriceInfo.stckPrpr(), buyTargetPriceS, buyTargetPriceR);

        // 지지선이 계산되지 않은 경우(0 이하) 매수하지 않는다.
        if (buyTargetPriceS <= 0) return false;

        // 현재가가 지지선 평균보다 낮으면 매수 기회로 판단한다.
        return currentPriceInfo.stckPrpr() < buyTargetPriceS;
    }

    /**
     * 가변 인자로 받은 가격들의 평균을 계산한다. Null 값은 제외한다.
     */
    private int calculateAveragePrice(Integer... values) {
        return (int) Arrays.stream(values)
                .filter(Objects::nonNull)
                .mapToInt(Integer::intValue)
                .average()
                .orElse(0);
    }

    /**
     * 매수 수량을 계산하고 주문을 요청한다.
     * 예수금의 일정 비율(CONTRACT_RATE)만큼을 할당하여 주문 수량을 산출한다.
     */
    private void executeBuyOrder(String itemId, int currentBalance, CurrentPriceInfo currentPriceInfo) {
        int allocatePrice = (int) (currentBalance * contractRate); // 할당 금액
        int buyPrice = currentPriceInfo.stckPrpr();                // 현재가(주문가)
        
        if (buyPrice == 0) return; // 방어 로직

        int buyCount = allocatePrice / buyPrice;

        // 할당 금액이 1주 가격보다 적을 경우
        if (buyCount == 0) {
            // 전체 잔고가 1주를 살 수 있는 금액이라면 1주만 매수 시도한다.
            if (currentBalance >= buyPrice) {
                buyCount = 1;
            } else {
                return; // 잔고 부족으로 매수 불가
            }
        }

        if (buyCount > 0) {
            workerService.handleOrder(itemId, buyCount, buyPrice, "B");  // 시장가 매수 주문
        }
    }
}