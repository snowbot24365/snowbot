package me.project.snowbot.entity;

import java.io.Serializable;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import lombok.Data;

@Data
@Entity
@Table(name = "trade_history")
@IdClass(TradeHistoryPK.class)
public class TradeHistory implements Serializable {
    @Id
    @Column(name = "item_cd", length = 6, nullable = false)
    private String itemCd;

    @Id
    @Column(name = "trade_date", length = 8, nullable = false)
    private String tradeDate;

    @Id
    @Column(name = "trade_hour", length = 6, nullable = false)
    private String tradeHour;

    @Id
    @Column(name = "trade_type", length = 1, nullable = false)
    private String tradeType;

    @Column(name = "trade_count")
    private Integer tradeCount;

    @Column(name = "trade_price")
    private Integer tradePrice;


    @Column(name = "rmk")
    private String rmk;
}
