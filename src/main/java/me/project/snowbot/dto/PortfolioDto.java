package me.project.snowbot.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 보유 현황 및 수익률 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PortfolioDto {
    private String itemCd;          // 종목코드
    private String itemNm;          // 종목명
    private Integer avgPrice;       // 평균 단가
    private Integer currentPrice;   // 현재가
    private Integer qty;            // 보유 수량
    private Long evaluationAmt;     // 평가 금액
    private Long profitLossAmt;     // 평가 손익 (금액)
    private Double profitLossRate;  // 수익률 (%)
    private String buyDate;         // 최초 매수일
}
