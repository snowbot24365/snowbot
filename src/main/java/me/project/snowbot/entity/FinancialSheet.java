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
@Table(name = "financial_sheet")
@ToString()
@EqualsAndHashCode(callSuper = false)
@Data
public class FinancialSheet {
    @EmbeddedId
    private SheetPK id;

    @Column(precision = 23, scale = 2)
    private BigDecimal grs;	//매출액 증가율
    @Column(precision = 23, scale = 2)
    private BigDecimal bsop_prfi_inrt;	//영업 이익 증가율
    @Column(precision = 23, scale = 2)
    private BigDecimal ntin_inrt;	//순이익 증가율
    @Column(precision = 23, scale = 2)
    private BigDecimal roe_val;	//ROE 값
    @Column(precision = 23, scale = 2)
    private BigDecimal eps;	//EPS
    @Column(precision = 23, scale = 2)
    private BigDecimal sps;	//주당매출액
    @Column(precision = 23, scale = 2)
    private BigDecimal bps;	//BPS
    @Column(precision = 23, scale = 2)
    private BigDecimal rsrv_rate;	//유보 비율
    @Column(precision = 23, scale = 2)
    private BigDecimal lblt_rate;	//부채 비율
}
