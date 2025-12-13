package me.project.snowbot.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import me.project.snowbot.entity.TradeHistory;
import me.project.snowbot.entity.TradeHistoryPK;

public interface TradeHistoryRepository extends JpaRepository<TradeHistory, TradeHistoryPK> {
    
    @Query(value = "select e from TradeHistory e where e.itemCd = :item_cd and e.tradeDate = :date and e.tradeType = 'B' order by e.tradeHour desc LIMIT 1")
    TradeHistory findBoungtItemInfo(@Param("item_cd") String item_cd, @Param("date") String date);
    
    @Query(value = "select e from TradeHistory e where e.itemCd = :item_cd and e.tradeDate = :date and e.tradeType = 'B'")
    List<TradeHistory> findBoungtItemInfos(@Param("item_cd") String item_cd, @Param("date") String date);

    @Query(value = "select e from TradeHistory e where e.itemCd = :item_cd and e.tradeDate = :date and e.tradeType = 'SS'")
    TradeHistory findSellSWItemInfo(@Param("item_cd") String item_cd, @Param("date") String date);

    @Query(value = "select e from TradeHistory e where e.itemCd = :item_cd and e.tradeType = 'SS'")
    List<TradeHistory> findSellSWItemInfos(@Param("item_cd") String item_cd);

    @Query(value = "select e from TradeHistory e where e.tradeType = 'SS'")
    List<TradeHistory> findAllSWSellHistory();

    @Query(value = "select e from TradeHistory e where e.itemCd = :item_cd and e.tradeType = 'SS'")
    List<TradeHistory> findSWSellHistoryByItemId(@Param("item_cd") String item_cd);

}