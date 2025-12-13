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
@Table(name = "item_price")
@ToString()
@Data
@EqualsAndHashCode(callSuper = false)
public class ItemPrice {
    @EmbeddedId
    private ItemPricePK id;
    private Integer stck_clpr;			//종가
    private Integer stck_oprc;			//주식 시가
    private Integer stck_hgpr;			//주식 최고가
    private Integer stck_lwpr;			//주식 최저가
    private Integer acml_vol;			//거래량
    @Column(precision = 23, scale = 2)
    private BigDecimal acml_tr_pbmn;		//거래 대금
    private Integer prdy_vrss;			//전일 대비
    private Integer prdy_vrss_sign;		//전일 대비 부호 (3<:red, 3>:blue, 3=3:black)
    private Double ma5;                // 5일 이동평균선
    private Double ma10;               // 10일 이동평균선
    private Double ma20;               // 20일 이동평균선
    private Double ma30;               // 30일 이동평균선
    private Double ma60;               // 60일 이동평균선
    private Double ma120;              // 120일 이동평균선
    private Double ma200;              // 200일 이동평균선
    private Double ma240;              // 240일 이동평균선
}
