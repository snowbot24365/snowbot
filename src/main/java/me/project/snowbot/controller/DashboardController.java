package me.project.snowbot.controller;

import java.util.List;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

import lombok.Builder;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import me.project.snowbot.entity.ItemMst;
import me.project.snowbot.entity.ItemTradeInfo;
import me.project.snowbot.entity.SwingScore;
import me.project.snowbot.entity.TradeStatus;
import me.project.snowbot.service.ItemMstService;
import me.project.snowbot.service.ItemTradeInfoService;
import me.project.snowbot.service.SwingService;
import me.project.snowbot.service.TradeStatusService;
import me.project.snowbot.service.WorkerService;
import me.project.snowbot.util.CustomDateUtils;

@Slf4j
@Controller
@RequestMapping("/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final SwingService swingService;
    private final ItemMstService itemMstService;
    private final ItemTradeInfoService itemTradeInfoService;
    private final TradeStatusService tradeStatusService;
    private final WorkerService workerService;

    // --- Settings 값 주입 ---
    @Value("${snowbot.trading.contract-rate}") private double contractRate;
    @Value("${snowbot.trading.limit-price}") private long limitPrice;
    @Value("${snowbot.trading.limit-cnt}") private int limitCnt;
    @Value("${snowbot.trading.buy.use-yn}") private String buyUseYn;
    @Value("${snowbot.trading.buy.test-force-buy}") private String testForceBuy;
    @Value("${snowbot.trading.sell.up-rate}") private double sellUpRate;
    @Value("${snowbot.trading.sell.down-rate}") private double sellDownRate;
    @Value("${snowbot.trading.sell.use-loss-cut}") private String useLossCut;
    @Value("${snowbot.trading.sell.hold-rate}") private double sellHoldRate;
    @Value("${snowbot.trading.sell.test-force-sell}") private String testForceSell;

    @GetMapping
    public String dashboard(Model model) {
        String today = CustomDateUtils.getStringToday();

        // 1. 매수 대상 종목 (Scoring Result)
        List<SwingScore> rawScores = swingService.findByDate(today);
        List<ScoringDto> scoringList = rawScores.stream().map(score -> {
            String itemCd = score.getId().getItem_cd();
            ItemMst mst = itemMstService.findByItem(itemCd);
            // 현재가 정보 조회를 위해 ItemTradeInfo 혹은 ItemPrice 접근 (여기서는 TradeInfo 활용)
            ItemTradeInfo info = itemTradeInfoService.getItemTradeInfo(itemCd, today);
            int currentPrice = (info != null && info.getStck_prpr() != null) ? info.getStck_prpr() : 0;
            
            return ScoringDto.builder()
                    .itemCd(itemCd)
                    .itemNm(mst != null ? mst.getItmsNm() : itemCd)
                    .totalScore(score.getTotalScore())
                    .currentPrice(currentPrice)
                    .date(score.getId().getStckBsopDate())
                    .build();
        }).collect(Collectors.toList());

        // 2. 현재 분할 매수 진행 종목 (Buying Process - 후보군 중 아직 보유하지 않은 것 or 일부 매수)
        // 여기서는 '매수 가능성(Y)' 상태인 종목들을 후보군으로 봅니다.
        List<ItemTradeInfo> buyCandidates = itemTradeInfoService.getBuySWItems(today);
        List<BuyingProcessDto> buyingList = buyCandidates.stream().map(info -> {
            String itemCd = info.getId().getItem_cd();
            ItemMst mst = itemMstService.findByItem(itemCd);
            
            // 보유 수량 확인 (TradeStatus)
            TradeStatus status = tradeStatusService.getTradeStatus(itemCd, today);
            int currentQty = (status != null) ? status.getQty() : 0;
            
            // 목표 수량 계산 (예상: 한도금액 / 현재가)
            int price = (info.getStck_prpr() != null && info.getStck_prpr() > 0) ? info.getStck_prpr() : 1;
            int targetQty = (int) (limitPrice / price); 
            double progress = (targetQty > 0) ? ((double) currentQty / targetQty) * 100.0 : 0.0;

            return BuyingProcessDto.builder()
                    .itemCd(itemCd)
                    .itemNm(mst != null ? mst.getItmsNm() : itemCd)
                    .currentQty(currentQty)
                    .targetQty(targetQty)
                    .progress(Math.min(progress, 100.0)) // 최대 100%
                    .build();
        }).collect(Collectors.toList());

        // 3. 보유 현황 및 수익률 (Portfolio)
        List<TradeStatus> holdings = tradeStatusService.getBoughtSWItem(today);
        List<PortfolioDto> portfolioList = holdings.stream().map(status -> {
            String itemCd = status.getItemCd();
            ItemMst mst = itemMstService.findByItem(itemCd);
            
            // 현재가 조회 (실시간성을 위해 WorkerService를 통하거나 TradeInfoService 업데이트값 사용)
            // 여기서는 TradeInfoService에 저장된 최신가를 사용한다고 가정
            ItemTradeInfo info = itemTradeInfoService.getItemTradeInfo(itemCd, today);
            int currentPrice = (info != null && info.getStck_prpr() != null) ? info.getStck_prpr() : status.getTradePrice();
            
            int buyPrice = status.getTradePrice();
            int qty = status.getQty();
            
            // 수익률 및 평가손익 계산
            double profitRate = 0.0;
            int profitAmt = 0;
            if (buyPrice > 0) {
                profitRate = ((double) (currentPrice - buyPrice) / buyPrice) * 100.0;
                profitAmt = (currentPrice - buyPrice) * qty;
            }

            return PortfolioDto.builder()
                    .itemCd(itemCd)
                    .itemNm(mst != null ? mst.getItmsNm() : itemCd)
                    .avgPrice(buyPrice)
                    .currentPrice(currentPrice)
                    .qty(qty)
                    .profitAmt(profitAmt)
                    .profitRate(profitRate)
                    .build();
        }).collect(Collectors.toList());

        // 4. Settings DTO 생성
        SettingsDto settings = SettingsDto.builder()
                .contractRate(contractRate).limitPrice(limitPrice).limitCnt(limitCnt)
                .buyUseYn(buyUseYn).testForceBuy(testForceBuy)
                .sellUpRate(sellUpRate).sellDownRate(sellDownRate)
                .useLossCut(useLossCut).sellHoldRate(sellHoldRate).testForceSell(testForceSell)
                .build();

        model.addAttribute("scoringList", scoringList);
        model.addAttribute("buyingList", buyingList);
        model.addAttribute("portfolioList", portfolioList);
        model.addAttribute("settings", settings);
        
        // 계좌 잔고 요약 정보 추가
        int accountBalance = workerService.getAccountBalance();
        model.addAttribute("accountBalance", accountBalance);

        return "dashboard"; // dashboard.html
    }

    // --- DTO Classes ---
    @Data @Builder
    public static class ScoringDto {
        private String itemCd;
        private String itemNm;
        private int totalScore;
        private int currentPrice;
        private String date;
    }

    @Data @Builder
    public static class BuyingProcessDto {
        private String itemCd;
        private String itemNm;
        private int currentQty;
        private int targetQty;
        private double progress;
    }

    @Data @Builder
    public static class PortfolioDto {
        private String itemCd;
        private String itemNm;
        private int avgPrice;
        private int currentPrice;
        private int qty;
        private int profitAmt;
        private double profitRate;
    }

    @Data @Builder
    public static class SettingsDto {
        private double contractRate;
        private long limitPrice;
        private int limitCnt;
        private String buyUseYn;
        private String testForceBuy;
        private double sellUpRate;
        private double sellDownRate;
        private String useLossCut;
        private double sellHoldRate;
        private String testForceSell;
    }
}