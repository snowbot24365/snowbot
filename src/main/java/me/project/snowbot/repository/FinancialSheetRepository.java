package me.project.snowbot.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import me.project.snowbot.entity.FinancialSheet;
import me.project.snowbot.entity.SheetPK;

public interface FinancialSheetRepository extends JpaRepository<FinancialSheet, SheetPK> {
    @Query(value = "select e from FinancialSheet e where e.id.item_cd = :id and e.id.sheet_cl = :cl and e.id.stac_yymm = :ym order by e.id.item_cd, e.id.sheet_cl, e.id.stac_yymm desc")
    FinancialSheet findByKeys(@Param("id") String id, @Param("cl") String cl, @Param("ym") String ym);

    @Query(value = "select e from FinancialSheet e where e.id.item_cd = :id order by e.id.item_cd, e.id.sheet_cl, e.id.stac_yymm desc")
    List<FinancialSheet> findByIdAll(@Param("id") String id);

    @Query(value = "select e from FinancialSheet e where e.id.item_cd = :id and e.id.sheet_cl = '0' order by e.id.stac_yymm desc")
    List<FinancialSheet> findByIdYear(@Param("id") String id);

    @Query(value = "SELECT " +
            "MST.MRKT_CTG, " +
            "IE.BSTP_KOR_ISNM, " +
            "FS.ITEM_CD, " +
            "MST.ITMS_NM, " +
            "FS.GRS, " +              // 매출액 증가율(YOY)
            "FS.BSOP_PRFI_INRT, " +   // 영업이익 증가율(YOY)
            "FS.RSRV_RATE, " +        // 유보비율
            "FS.LBLT_RATE, " +        // 부채비율
            "IP.STCK_CLPR, " +        // 종가
            "IE.STCK_DRYY_HGPR, " +   // 주식 연중 최고가
            "IE.DRYY_HGPR_VRSS_PRPR_RATE, " + // 연중 최고가 대비 현재가 비율
            "IP.MA5, " +
            "IP.MA10, " +
            "IP.MA20, " +
            "IP.MA30, " +
            "IP.MA60, " +
            "IP.MA120, " +
            "IP.MA240, " +
            "IE.FRGN_NTBY_QTY, " +    // 외국인순매수수량(F)
            "IE.PGTR_NTBY_QTY, " +    // 프로그램매매 순매수 수량(P)
            "IP.ACML_VOL, " +         // 거래량 (F와 P중 큰 값 대비 거래량)
            "IE.FRGN_HLDN_QTY, " +    // 외국인보유량
            "IE.LSTN_STCN, " +         // 주식수 (외국인보유량 대비 주식수)
            "IE.PER, " +
            "IE.PBR, " +
            "IE.STCK_DRYY_LWPR, " +         //연중 최저가
            "IE.DRYY_LWPR_VRSS_PRPR_RATE, " +    //연중 최저가대비 현재가 비율
            "IE.EPS, " +
            "IE.BPS " +
            "FROM FINANCIAL_SHEET FS " +
            "INNER JOIN (" +
            "    SELECT ITEM_CD, MAX(STAC_YYMM) AS STAC_YYMM " +
            "    FROM FINANCIAL_SHEET " +
            "    GROUP BY ITEM_CD" +
            ") IFS " +
            "ON FS.ITEM_CD = IFS.ITEM_CD " +
            "AND FS.STAC_YYMM = IFS.STAC_YYMM " +
            "INNER JOIN ITEM_MST MST " +
            "ON FS.ITEM_CD = MST.ITEM_CD " +
            "INNER JOIN ITEM_EQUITY IE " +
            "ON FS.ITEM_CD = IE.ITEM_CD " +
            "INNER JOIN (" +
            "    SELECT * FROM ITEM_PRICE " +
            "    WHERE STCK_BSOP_DATE IN ( " +
            "SELECT MAX(STCK_BSOP_DATE) FROM ITEM_PRICE " +
            "WHERE STCK_BSOP_DATE <= TO_CHAR((SYSDATE - 1), 'YYYYMMDD')) " +
            ") IP " +
            "ON FS.ITEM_CD = IP.ITEM_CD " +
            "WHERE FS.SHEET_CL = '0' " +
            "ORDER BY MST.MRKT_CTG, IE.BSTP_KOR_ISNM, FS.ITEM_CD",
            nativeQuery = true)
    List<Object[]> findFilteredFinancialSheets();
}
