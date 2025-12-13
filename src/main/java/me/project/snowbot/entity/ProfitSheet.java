package me.project.snowbot.entity;

import java.math.BigDecimal;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;
import lombok.ToString;

@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "profit_sheet")
@ToString()
@Data
@EqualsAndHashCode(callSuper = false)
public class ProfitSheet {
    @EmbeddedId
    private SheetPK id;

    @Column(precision = 23, scale = 2)
    private BigDecimal cptl_ntin_rate;	//총자본 순이익율
    @Column(precision = 23, scale = 2)
    private BigDecimal self_cptl_ntin_inrt;	//자기자본 순이익율
    @Column(precision = 23, scale = 2)
    private BigDecimal sale_ntin_rate;	//매출액 순이익율
    @Column(precision = 23, scale = 2)
    private BigDecimal sale_totl_rate;	//매출액 총이익율
}
