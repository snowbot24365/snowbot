package me.project.snowbot.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.dto.*;
import me.project.snowbot.entity.*;
import me.project.snowbot.repository.*;
import me.project.snowbot.util.CustomDateUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class DashboardService {

    private final SwingScoreRepository swingScoreRepository;
    private final ItemMstRepository itemMstRepository;
    private final ItemTradeInfoRepository itemTradeInfoRepository;
    private final TradeHistoryRepository tradeHistoryRepository;
    private final TradeStatusRepository tradeStatusRepository;

    // application.yml에서 설정 값 주입
    @Value("${snowbot.trading.contract-rate:0.1}")
    private Double contractRate;

    @Value("${snowbot.trading.limit-price:500000}")
    private Integer limitPrice;

    @Value("${snowbot.trading.limit-cnt:20}")
    private Integer limitCnt;

    @Value("${snowbot.trading.buy.use-yn:Y}")
    private String buyUseYn;

    @Value("${snowbot.trading.buy.test-force-buy:N}")
    private String testForceBuy;

    @Value("${snowbot.trading.sell.up-rate:10.0}")
    private Double sellUpRate;

    @Value("${snowbot.trading.sell.down-rate:-20.0}")
    private Double sellDownRate;

    @Value("${snowbot.trading.sell.use-loss-cut:Y}")
    private String useLossCut;

    @Value("${snowbot.trading.sell.hold-rate:0.8}")
    private Double holdRate;

    @Value("${snowbot.trading.sell.test-force-sell:N}")
    private String testForceSell;

    /**
     * 전체 대시보드 데이터 조회
     */
    public DashboardDto getDashboardData() {
        String today = CustomDateUtils.getToday();

        List<ScoringResultDto> scoringResults = getScoringResults(today);
        List<BuyingProcessDto> buyingProcesses = getBuyingProcesses(today);
        List<PortfolioDto> portfolios = getPortfolios(today);
        TradingSettingsDto tradingSettings = getTradingSettings();

        // 요약 정보 계산
        Integer totalHoldingCount = portfolios.size();
        Long totalEvaluationAmt = portfolios.stream()
                .mapToLong(PortfolioDto::getEvaluationAmt)
                .sum();
        Long totalProfitLossAmt = portfolios.stream()
                .mapToLong(PortfolioDto::getProfitLossAmt)
                .sum();
        Double totalProfitLossRate = totalEvaluationAmt > 0
                ? (totalProfitLossAmt.doubleValue() / (totalEvaluationAmt - totalProfitLossAmt)) * 100
                : 0.0;

        return DashboardDto.builder()
                .scoringResults(scoringResults)
                .buyingProcesses(buyingProcesses)
                .portfolios(portfolios)
                .tradingSettings(tradingSettings)
                .totalHoldingCount(totalHoldingCount)
                .totalEvaluationAmt(totalEvaluationAmt)
                .totalProfitLossAmt(totalProfitLossAmt)
                .totalProfitLossRate(totalProfitLossRate)
                .build();
    }

    /**
     * 1. 매수 대상 종목 조회 (Scoring Result)
     */
    public List<ScoringResultDto> getScoringResults(String date) {
        List<SwingScore> swingScores = swingScoreRepository.findByDate(date);

        List<ScoringResultDto> results = new ArrayList<>();
        int rank = 1;

        for (SwingScore score : swingScores) {
            ItemMst itemMst = itemMstRepository.findById(score.getId().getItem_cd()).orElse(null);
            ItemTradeInfo tradeInfo = itemTradeInfoRepository.findLastInfo(score.getId().getItem_cd());

            if (itemMst != null) {
                results.add(ScoringResultDto.builder()
                        .itemCd(score.getId().getItem_cd())
                        .itemNm(itemMst.getItmsNm())
                        .totalScore(score.getTotalScore())
                        .currentPrice(tradeInfo != null ? tradeInfo.getStck_prpr() : 0)
                        .selectDate(score.getId().getStckBsopDate())
                        .rank(rank++)
                        .build());
            }
        }

        return results;
    }

    /**
     * 2. 현재 분할 매수 진행 종목 (Buying Process)
     */
    public List<BuyingProcessDto> getBuyingProcesses(String date) {
        List<TradeHistory> buyHistories = tradeHistoryRepository.findAll().stream()
                .filter(h -> "B".equals(h.getTradeType()))
                .collect(Collectors.toList());

        // 종목별로 그룹화
        Map<String, List<TradeHistory>> groupedByItem = buyHistories.stream()
                .collect(Collectors.groupingBy(TradeHistory::getItemCd));

        List<BuyingProcessDto> results = new ArrayList<>();

        for (Map.Entry<String, List<TradeHistory>> entry : groupedByItem.entrySet()) {
            String itemCd = entry.getKey();
            List<TradeHistory> histories = entry.getValue();

            // 총 매수 수량과 평균 단가 계산
            int totalQty = histories.stream().mapToInt(TradeHistory::getTradeCount).sum();
            double avgPrice = histories.stream()
                    .mapToDouble(h -> h.getTradePrice() * h.getTradeCount())
                    .sum() / totalQty;

            // 목표 수량 계산 (limitPrice / avgPrice)
            int targetQty = (int) (limitPrice / avgPrice);

            // 진행률 계산 - 목표 수량에 도달하지 않은 경우만 표시
            if (totalQty < targetQty) {
                ItemMst itemMst = itemMstRepository.findById(itemCd).orElse(null);
                ItemTradeInfo tradeInfo = itemTradeInfoRepository.findLastInfo(itemCd);

                if (itemMst != null) {
                    double progressRate = (totalQty * 100.0) / targetQty;

                    results.add(BuyingProcessDto.builder()
                            .itemCd(itemCd)
                            .itemNm(itemMst.getItmsNm())
                            .currentQty(totalQty)
                            .targetQty(targetQty)
                            .progressRate(progressRate)
                            .avgPrice((int) avgPrice)
                            .currentPrice(tradeInfo != null ? tradeInfo.getStck_prpr() : 0)
                            .build());
                }
            }
        }

        return results;
    }

    /**
     * 3. 보유 현황 및 수익률 (Portfolio & Profit)
     */
    public List<PortfolioDto> getPortfolios(String date) {
        List<TradeHistory> buyHistories = tradeHistoryRepository.findAll().stream()
                .filter(h -> "B".equals(h.getTradeType()))
                .collect(Collectors.toList());

        // 종목별로 그룹화
        Map<String, List<TradeHistory>> groupedByItem = buyHistories.stream()
                .collect(Collectors.groupingBy(TradeHistory::getItemCd));

        List<PortfolioDto> results = new ArrayList<>();

        for (Map.Entry<String, List<TradeHistory>> entry : groupedByItem.entrySet()) {
            String itemCd = entry.getKey();
            List<TradeHistory> histories = entry.getValue();

            // 총 매수 수량과 평균 단가 계산
            int totalQty = histories.stream().mapToInt(TradeHistory::getTradeCount).sum();
            int totalAmount = histories.stream()
                    .mapToInt(h -> h.getTradePrice() * h.getTradeCount())
                    .sum();
            int avgPrice = totalAmount / totalQty;

            // 현재가 조회
            ItemMst itemMst = itemMstRepository.findById(itemCd).orElse(null);
            ItemTradeInfo tradeInfo = itemTradeInfoRepository.findLastInfo(itemCd);

            if (itemMst != null && tradeInfo != null) {
                int currentPrice = tradeInfo.getStck_prpr();
                long evaluationAmt = (long) currentPrice * totalQty;
                long profitLossAmt = evaluationAmt - totalAmount;
                double profitLossRate = (profitLossAmt * 100.0) / totalAmount;

                // 최초 매수일
                String buyDate = histories.stream()
                        .map(TradeHistory::getTradeDate)
                        .min(String::compareTo)
                        .orElse("");

                results.add(PortfolioDto.builder()
                        .itemCd(itemCd)
                        .itemNm(itemMst.getItmsNm())
                        .avgPrice(avgPrice)
                        .currentPrice(currentPrice)
                        .qty(totalQty)
                        .evaluationAmt(evaluationAmt)
                        .profitLossAmt(profitLossAmt)
                        .profitLossRate(profitLossRate)
                        .buyDate(buyDate)
                        .build());
            }
        }

        return results;
    }

    /**
     * 4. 트레이딩 설정 조회
     */
    public TradingSettingsDto getTradingSettings() {
        return TradingSettingsDto.builder()
                .contractRate(contractRate)
                .limitPrice(limitPrice)
                .limitCnt(limitCnt)
                .buyUseYn(buyUseYn)
                .testForceBuy(testForceBuy)
                .sellUpRate(sellUpRate)
                .sellDownRate(sellDownRate)
                .useLossCut(useLossCut)
                .holdRate(holdRate)
                .testForceSell(testForceSell)
                .build();
    }
}
