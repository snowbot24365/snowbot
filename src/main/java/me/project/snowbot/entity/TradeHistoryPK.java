package me.project.snowbot.entity;

import java.io.Serializable;

import jakarta.persistence.Embeddable;
import lombok.Data;

@Embeddable
@Data
public class TradeHistoryPK implements Serializable {
    private String itemCd;
    private String tradeDate;
    private String tradeHour;
    private String tradeType;
}