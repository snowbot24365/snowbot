package me.project.snowbot.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import me.project.snowbot.entity.TradeStatus;

public interface TradeStatusRepository extends JpaRepository<TradeStatus, Long> {

    @Query(value = "select e from TradeStatus e where e.itemCd = :item_cd and e.tradeDate = :date")
    TradeStatus findByStatus(@Param("item_cd") String item_cd, @Param("date") String date);

    @Query(value = "select e from TradeStatus e where e.tradeDate = :date and e.tradeType = 'BS'")
    List<TradeStatus> findByBuySWId(@Param("date") String date);
}
