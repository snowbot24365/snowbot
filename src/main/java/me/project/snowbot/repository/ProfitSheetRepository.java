package me.project.snowbot.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import me.project.snowbot.entity.ProfitSheet;
import me.project.snowbot.entity.SheetPK;

public interface ProfitSheetRepository extends JpaRepository<ProfitSheet, SheetPK> {
    @Query(value = "select e from ProfitSheet e where e.id.item_cd = :id and e.id.sheet_cl = :cl and e.id.stac_yymm = :ym order by e.id.item_cd, e.id.sheet_cl, e.id.stac_yymm desc")
    ProfitSheet findByKeys(@Param("id") String id, @Param("cl") String cl, @Param("ym") String ym);

    @Query(value = "select e from ProfitSheet e where e.id.item_cd = :id order by e.id.item_cd, e.id.sheet_cl, e.id.stac_yymm desc")
    List<ProfitSheet> findByIdAll(@Param("id") String id);
}
