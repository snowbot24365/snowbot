package me.project.snowbot.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 트레이딩 설정 DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TradingSettingsDto {
    // 기본 설정
    private Double contractRate;    // 1회 매수 시 예수금 대비 비율
    private Integer limitPrice;     // 종목당 최대 보유 한도 금액
    private Integer limitCnt;       // 최대 보유 종목 수

    // 매수 설정
    private String buyUseYn;        // 매수 로직 동작 여부 (Y/N)
    private String testForceBuy;    // 강제 매수 테스트 플래그

    // 매도 설정
    private Double sellUpRate;      // 익절 기준 수익률 (%)
    private Double sellDownRate;    // 손절 기준 수익률 (%)
    private String useLossCut;      // 손절 기능 사용 여부 (Y/N)
    private Double holdRate;        // 매도 보류 비율
    private String testForceSell;   // 강제 매도 테스트 플래그
}
