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
@Table(name = "income_sheet")
@ToString()
@Data
@EqualsAndHashCode(callSuper = false)
public class IncomeSheet {
    @EmbeddedId
    private SheetPK id;

    @Column(precision = 23, scale = 2)
    private BigDecimal sale_account;	//매출액
    @Column(precision = 23, scale = 2)
    private BigDecimal sale_cost;	//매출 원가
    @Column(precision = 23, scale = 2)
    private BigDecimal sale_totl_prfi;	//매출 총 이익
    @Column(precision = 23, scale = 2)
    private BigDecimal depr_cost;	//감가상각비
    @Column(precision = 23, scale = 2)
    private BigDecimal sell_mang;	//판매 및 관리비
    @Column(precision = 23, scale = 2)
    private BigDecimal bsop_prti;	//영업 이익
    @Column(precision = 23, scale = 2)
    private BigDecimal bsop_non_ernn;	//영업 외 수익
    @Column(precision = 23, scale = 2)
    private BigDecimal bsop_non_expn;	//영업 외 비용
    @Column(precision = 23, scale = 2)
    private BigDecimal op_prfi;	//경상 이익
    @Column(precision = 23, scale = 2)
    private BigDecimal spec_prfi;	//특별 이익
    @Column(precision = 23, scale = 2)
    private BigDecimal spec_loss;	//특별 손실
    @Column(precision = 23, scale = 2)
    private BigDecimal thtr_ntin;	//당기순이익
}
