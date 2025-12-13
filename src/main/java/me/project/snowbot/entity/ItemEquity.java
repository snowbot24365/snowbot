package me.project.snowbot.entity;

import java.math.BigDecimal;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;
import lombok.ToString;

@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "item_equity")
@ToString()
@Data
@EqualsAndHashCode(callSuper = false)
public class ItemEquity {
    @Id
    @Column(name = "item_cd")
    private String itemCd;				//종목코드, pk

    @Column(length = 100)
    private String bstp_kor_isnm; 		//업종
    @Column(length = 3)
    private String iscd_stat_cls_code;	//종목 상태 구분 코드
    @Column(precision = 23, scale = 2)
    private BigDecimal stck_sdpr;			//주식 기준가
    @Column(precision = 23, scale = 2)
    private BigDecimal wghn_avrg_stck_prc;	//가중 평균 주식 가격
    @Column(precision = 23, scale = 2)
    private BigDecimal hts_frgn_ehrt;		//HTS 외국인 소진율
    @Column(precision = 23, scale = 2)
    private BigDecimal frgn_ntby_qty;		//외국인 순매수 수량
    @Column(precision = 23, scale = 2)
    private BigDecimal pgtr_ntby_qty;		//프로그램매매 순매수 수량
    @Column(precision = 23, scale = 2)
    private BigDecimal cpfn;				//자본금
    @Column(precision = 23, scale = 2)
    private BigDecimal rstc_wdth_prc;		//제한 폭 가격
    @Column(precision = 23, scale = 2)
    private BigDecimal stck_fcam;			//주식 액면가
    @Column(precision = 23, scale = 2)
    private BigDecimal stck_sspr;			//주식 대용가
    @Column(precision = 23, scale = 2)
    private BigDecimal aspr_unit;			//호가단위
    @Column(precision = 23, scale = 2)
    private BigDecimal hts_deal_qty_unit_val;	//HTS 매매 수량 단위 값
    @Column(precision = 23, scale = 2)
    private BigDecimal lstn_stcn;			//상장 주수
    @Column(precision = 23, scale = 2)
    private BigDecimal hts_avls;			//HTS 시가총액
    @Column(precision = 23, scale = 2)
    private BigDecimal vol_tnrt;			//거래량 회전율
    @Column(precision = 23, scale = 2)
    private BigDecimal d250_hgpr;			//250일 최고가
    @Column(length = 8)
    private String d250_hgpr_date;		//250일 최고가 일자
    @Column(precision = 23, scale = 2)
    private BigDecimal d250_hgpr_vrss_prpr_rate;	//250일 최고가 대비 현재가 비율
    @Column(precision = 23, scale = 2)
    private BigDecimal d250_lwpr;			//250일 최저가
    @Column(length = 8)
    private String d250_lwpr_date;		//250일 최저가 일자
    @Column(precision = 23, scale = 2)
    private BigDecimal d250_lwpr_vrss_prpr_rate;	//250일 최저가 대비 현재가 비율
    @Column(precision = 23, scale = 2)
    private BigDecimal stck_dryy_hgpr;		//주식 연중 최고가
    @Column(precision = 23, scale = 2)
    private BigDecimal dryy_hgpr_vrss_prpr_rate;	//연중 최고가 대비 현재가 비율
    @Column(length = 8)
    private String dryy_hgpr_date;		//연중 최고가 일자
    @Column(precision = 23, scale = 2)
    private BigDecimal stck_dryy_lwpr;		//주식 연중 최저가
    @Column(precision = 23, scale = 2)
    private BigDecimal dryy_lwpr_vrss_prpr_rate;	//연중 최저가 대비 현재가 비율
    @Column(length = 8)
    private String dryy_lwpr_date;		//연중 최저가 일자
    @Column(precision = 23, scale = 2)
    private BigDecimal w52_hgpr;			//52주일 최고가
    @Column(precision = 23, scale = 2)
    private BigDecimal w52_hgpr_vrss_prpr_ctrt;	//52주일 최고가 대비 현재가 대비
    @Column(length = 8)
    private String w52_hgpr_date;		//52주일 최고가 일자
    @Column(precision = 23, scale = 2)
    private BigDecimal w52_lwpr;			//52주일 최저가
    @Column(precision = 23, scale = 2)
    private BigDecimal w52_lwpr_vrss_prpr_ctrt;	//52주일 최저가 대비 현재가 대비
    @Column(length = 8)
    private String w52_lwpr_date;		//52주일 최저가 일자
    @Column(precision = 23, scale = 2)
    private BigDecimal whol_loan_rmnd_rate;	//전체 융자 잔고 비율
    @Column(length = 10)
    private String ssts_yn;				//공매도가능여부
    @Column(length = 50)
    private String fcam_cnnm;			//액면가 통화명
    @Column(length = 50)
    private String cpfn_cnnm;			//자본금 통화명
    @Column(precision = 23, scale = 2)
    private BigDecimal last_ssts_cntg_qty;	//최종 공매도 체결 수량
    @Column(precision = 23, scale = 2)
    private BigDecimal frgn_hldn_qty;		//외국인 보유 수량
    @Column(precision = 23, scale = 2)
    private BigDecimal per;					//PER
    @Column(precision = 23, scale = 2)
    private BigDecimal eps;					//EPS
    @Column(precision = 23, scale = 2)
    private BigDecimal pbr;					//PBR
    @Column(precision = 23, scale = 2)
    private BigDecimal bps;					//BPS
    @Column(precision = 23, scale = 2)
    private BigDecimal stck_mxpr;			//주식 상한가
    @Column(precision = 23, scale = 2)
    private BigDecimal stck_llam;			//주식 하한가
}
