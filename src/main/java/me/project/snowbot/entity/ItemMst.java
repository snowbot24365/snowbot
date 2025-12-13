package me.project.snowbot.entity;

import java.time.LocalDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "item_mst")
@Data
@EqualsAndHashCode(callSuper = false)
public class ItemMst {
    
    @Id
    @Column(name = "item_cd", length = 6)
    private String itemCd;				//종목코드, pk
    @Column(name = "mrkt_ctg", length = 10)
    private String mrktCtg;				//시장구분

    @Column(name = "itms_nm", length = 1000)
    private String itmsNm;				//종목명
    @Column(name = "corp_nm", length = 1000)
    private String corpNm;				//법인명

    @Column(name = "sector", length = 1000)
    private String sector;				//섹터

    @Column(name = "cl_nation", length = 2)
    private String clNation;            //국가구분

    @Column(name = "created_date")
    private LocalDateTime createdDate;
}
