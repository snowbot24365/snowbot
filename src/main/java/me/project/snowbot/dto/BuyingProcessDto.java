package me.project.snowbot.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 현재 분할 매수 진행 종목 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BuyingProcessDto {
    private String itemCd;          // 종목코드
    private String itemNm;          // 종목명
    private Integer currentQty;     // 현재 모은 수량
    private Integer targetQty;      // 목표 수량
    private Double progressRate;    // 진행률(%)
    private Integer avgPrice;       // 평균 매수 단가
    private Integer currentPrice;   // 현재가
}
