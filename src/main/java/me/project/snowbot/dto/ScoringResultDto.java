package me.project.snowbot.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 매수 대상 종목 조회(Scoring Result) DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ScoringResultDto {
    private String itemCd;          // 종목코드
    private String itemNm;          // 종목명
    private Integer totalScore;     // 스코어링 점수
    private Integer currentPrice;   // 현재가
    private String selectDate;      // 선정 일자
    private Integer rank;           // 순위
}
