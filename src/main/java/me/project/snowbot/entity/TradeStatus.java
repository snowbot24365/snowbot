package me.project.snowbot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;

@Data
@Entity
@Table(name = "trade_status")
public class TradeStatus {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY) // Oracle IDENTITY 컬럼 매핑
    @Column(name = "TRADE_ID")
    private Long tradeId;

    @Column(name = "ITEM_CD", length = 6, nullable = false)
    private String itemCd;

    @Column(name = "TRADE_DATE", length = 8, nullable = false)
    private String tradeDate; // YYYYMMDD

    @Column(name = "TRADE_TYPE", length = 2, nullable = false)
    private String tradeType; // BS: 매수, SS: 매도

    @Column(name = "ODNO", length = 10)
    private String odno;

    @Column(name = "QTY", precision = 8)
    private Integer qty;

    @Column(name = "TRADE_PRICE", precision = 10)
    private Integer tradePrice;

    @Column(name = "TRADE_TIME", length = 6)
    private String tradeTime; // HHMMSS
}
