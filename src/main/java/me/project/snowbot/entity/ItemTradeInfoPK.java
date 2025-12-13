package me.project.snowbot.entity;

import java.io.Serializable;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.Data;

@Embeddable
@Data
public class ItemTradeInfoPK implements Serializable {
    @Column(length = 6)
    private String item_cd;
    @Column(length = 8)
    private String stckBsopDate;
}
