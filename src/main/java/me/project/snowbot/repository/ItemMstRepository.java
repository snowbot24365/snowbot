package me.project.snowbot.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import me.project.snowbot.entity.ItemMst;

public interface ItemMstRepository extends JpaRepository<ItemMst, String> {

    @Query(value = "select e.itemCd from ItemMst e where e.itmsNm NOT LIKE '%스팩%' group by e.itemCd")
    List<String> findByAllItemCds();

    @Query(value = "select e from ItemMst e where e.mrktCtg = :mrktCtg AND e.itmsNm NOT LIKE '%스팩%' order by e.itemCd asc")
    List<ItemMst> findByMarketItems(@Param("mrktCtg") String mrktCtg);

    @Query(value = "select e from ItemMst e where e.itemCd = :id")
    ItemMst findByOne(@Param("id") String id);
}
