package me.project.snowbot.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 통합 대시보드 데이터 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DashboardDto {
    private List<ScoringResultDto> scoringResults;      // 매수 대상 종목
    private List<BuyingProcessDto> buyingProcesses;     // 분할 매수 진행 종목
    private List<PortfolioDto> portfolios;              // 보유 현황
    private TradingSettingsDto tradingSettings;         // 트레이딩 설정

    // 요약 정보
    private Integer totalHoldingCount;      // 총 보유 종목 수
    private Long totalEvaluationAmt;        // 총 평가 금액
    private Long totalProfitLossAmt;        // 총 평가 손익
    private Double totalProfitLossRate;     // 총 수익률
}
