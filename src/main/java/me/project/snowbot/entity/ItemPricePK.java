package me.project.snowbot.entity;

import java.io.Serializable;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.Data;

@Embeddable
@Data
public class ItemPricePK implements Serializable {
    private String item_cd;
    @Column(length = 8)
    private String stck_bsop_date;
}
