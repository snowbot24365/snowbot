package me.project.snowbot.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import me.project.snowbot.entity.ItemTradeInfo;
import me.project.snowbot.entity.ItemTradeInfoPK;

/**
 * 종목별 매매 정보(ItemTradeInfo) 엔티티의 데이터베이스 접근을 담당하는 리포지토리 인터페이스이다.
 * 복합키(SwingScorePK)를 사용하며, JPQL을 통해 다양한 조건의 조회 메서드를 제공한다.
 */
public interface ItemTradeInfoRepository extends JpaRepository<ItemTradeInfo, ItemTradeInfoPK> {

    /**
     * 특정 종목(itemId)과 날짜(date)에 해당하는 데이터의 개수를 조회한다.
     * 데이터의 존재 여부를 확인하는 용도로 사용한다.
     */
    @Query("SELECT COUNT(d) FROM ItemTradeInfo d WHERE d.id.item_cd = :itemId AND d.id.stckBsopDate = :date")
    int countByIdAndDate(@Param("itemId") String itemId, @Param("date") String date);

    /**
     * 특정 날짜와 분석 유형(type)에 해당하는 모든 매매 정보를 종목 코드 순으로 조회한다.
     */
    @Query("SELECT e FROM ItemTradeInfo e WHERE e.id.stckBsopDate = :date and e.cd_type = :type order by e.id.item_cd")
    List<ItemTradeInfo> findByDateAndType(@Param("date") String date, @Param("type") String type);

    /**
     * 특정 날짜와 유형의 데이터 중, 매수 가능성이 없는('N') 종목을 제외하고 유효한 종목만 조회한다.
     */
    @Query("SELECT e FROM ItemTradeInfo e WHERE e.id.stckBsopDate = :date and e.cd_type = :type and e.yn_possibility <> 'N' order by e.id.item_cd")
    List<ItemTradeInfo> findByDateAndTypeAndYn_possibility(@Param("date") String date, @Param("type") String type);

    /**
     * 종목 코드와 날짜를 기준으로 특정 매매 정보를 단건 조회한다.
     */
    @Query("SELECT e FROM ItemTradeInfo e WHERE e.id.item_cd = :itemId AND e.id.stckBsopDate = :date order by e.id.item_cd")
    ItemTradeInfo findByKey(@Param("itemId") String itemId, @Param("date") String date);

    /**
     * 특정 날짜의 데이터 중 매수 가능성(yn_possibility)이 'Y'인 종목 리스트를 조회한다.
     */
    @Query("SELECT e FROM ItemTradeInfo e WHERE e.id.stckBsopDate = :date and e.yn_possibility = 'Y' order by e.id.item_cd")
    List<ItemTradeInfo> findByPossibleOpt(@Param("date") String date);

    /**
     * 데이터베이스에 저장된 영업일 중 가장 최근 날짜를 조회한다.
     * (날짜 역순 정렬 후 첫 번째 데이터를 반환한다.)
     */
    @Query("SELECT e.id.stckBsopDate FROM ItemTradeInfo e GROUP BY e.id.stckBsopDate ORDER BY e.id.stckBsopDate DESC LIMIT 1")
    String findFirstDate();

    /**
     * 특정 종목에 대해 가장 최근 날짜의 매매 정보를 조회한다.
     */
    @Query("SELECT e FROM ItemTradeInfo e WHERE e.id.item_cd = :itemId ORDER BY e.id.stckBsopDate DESC LIMIT 1")
    ItemTradeInfo findLastInfo(@Param("itemId") String itemId);
}
