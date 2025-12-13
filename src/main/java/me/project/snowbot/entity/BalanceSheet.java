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
@Table(name = "balance_sheet")
@ToString()
@Data
@EqualsAndHashCode(callSuper = false)
public class BalanceSheet {
    @EmbeddedId
    private SheetPK id;
    @Column(precision = 23, scale = 2)
    private BigDecimal cras;				//유동자산
    @Column(precision = 23, scale = 2)
    private BigDecimal fxas;				//고정자산
    @Column(precision = 23, scale = 2)
    private BigDecimal total_aset;			//자산총계
    @Column(precision = 23, scale = 2)
    private BigDecimal flow_lblt;			//유동부채
    @Column(precision = 23, scale = 2)
    private BigDecimal fix_lblt;			//고정부채
    @Column(precision = 23, scale = 2)
    private BigDecimal total_lblt;			//부채총계
    @Column(precision = 23, scale = 2)
    private BigDecimal cpfn;				//자본금
    @Column(precision = 23, scale = 2)
    private BigDecimal cfp_surp;			//자본 잉여금
    @Column(precision = 23, scale = 2)
    private BigDecimal prfi_surp;			//이익 잉여금
    @Column(precision = 23, scale = 2)
    private BigDecimal total_cptl;			//자본총계
}
