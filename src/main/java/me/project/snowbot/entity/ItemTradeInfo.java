package me.project.snowbot.entity;

import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "item_trade_info")
@Data
/**
 * 종목별 매매 전략 수립을 위한 핵심 지표(피벗 포인트)와 시세 정보를 관리하는 엔티티 클래스이다.
 * 특정 날짜의 지지/저항선 및 매수 가능 여부를 저장한다.
 */
public class ItemTradeInfo {
    @EmbeddedId
    private ItemTradeInfoPK id;

    // --- 피벗(Pivot) 분석 지표 ---
    /** 피벗(Pivot) 기준선 가격이다. (고가+저가+종가)/3 */
    private Integer pivot;

    /** 1차 저항선(Resistance 1) 가격이다. */
    private Integer r1;

    /** 2차 저항선(Resistance 2) 가격이다. */
    private Integer r2;

    /** 3차 저항선(Resistance 3) 가격이다. */
    private Integer r3;

    /** 1차 지지선(Support 1) 가격이다. */
    private Integer s1;

    /** 2차 지지선(Support 2) 가격이다. */
    private Integer s2;

    /** 3차 지지선(Support 3) 가격이다. */
    private Integer s3;

    // --- 시세 정보 ---
    /** 금일 시가(Open Price)이다. */
    private Integer stck_oprc;

    /** 전일 종가(Previous Close Price)이다. */
    private Integer stck_prdy_clpr;

    /** 현재가(Present Price)이다. */
    private Integer stck_prpr;

    // --- 분석 결과 및 기타 ---
    /** 분석 유형(전략 종류 등)을 구분하는 코드이다. */
    private String cd_type;

    /** 매수 대상 가능성 여부(Y/N)이다. */
    private String yn_possibility;

    /** 비고 사항이다. */
    private String rmk;
}
