package me.project.snowbot.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import me.project.snowbot.entity.ItemPrice;
import me.project.snowbot.entity.ItemPricePK;

public interface ItemPriceRepository extends JpaRepository<ItemPrice, ItemPricePK> {
    @Query(value = "select e from ItemPrice e where e.id.item_cd = :id and e.id.stck_bsop_date = :date order by e.id.item_cd, e.id.stck_bsop_date desc")
    ItemPrice findByIdData(@Param("id") String id, @Param("date") String date);

    @Query(value = "select e from ItemPrice e where e.id.item_cd = :id order by e.id.item_cd, e.id.stck_bsop_date desc")
    List<ItemPrice> findByIdAll(@Param("id") String id);

    @Query(value = "SELECT e FROM ItemPrice e WHERE e.id.item_cd = :id ORDER BY e.id.item_cd, e.id.stck_bsop_date DESC LIMIT 1", nativeQuery = false)
    ItemPrice findFirstById(@Param("id") String id);

    @Query(value = "SELECT e FROM ItemPrice e WHERE e.id.item_cd = :id AND e.id.stck_bsop_date < :date ORDER BY e.id.item_cd, e.id.stck_bsop_date DESC LIMIT 1", nativeQuery = false)
    ItemPrice findFirstByIdAndDate(@Param("id") String id, @Param("date") String date);

    @Query(value = "select e from ItemPrice e where  e.id.stck_bsop_date < :date")
    List<ItemPrice> findByDataDel(@Param("date") String date);

    @Query(value = "select e from ItemPrice e where  e.id.stck_bsop_date = :date")
    List<ItemPrice> findByDate(@Param("date") String date);
    
    @Query(value = "select e from ItemPrice e where e.id.item_cd = :id and e.id.stck_bsop_date between :fromDate and :toDate order by e.id.item_cd, e.id.stck_bsop_date asc")
    List<ItemPrice> findByIdAndRangeDate(@Param("id") String id, @Param("fromDate") String fromDate , @Param("toDate") String toDate);
}
