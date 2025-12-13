package me.project.snowbot.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import me.project.snowbot.entity.SwingScore;
import me.project.snowbot.entity.SwingScorePK;

public interface SwingScoreRepository extends JpaRepository<SwingScore, SwingScorePK> {
    @Query(value = "select e from SwingScore e where e.id.stckBsopDate = :date order by e.totalScore desc")
    List<SwingScore> findByDate(@Param("date") String date);

    @Query(value = "select e from SwingScore e where e.id.item_cd = :itemCd and e.id.stckBsopDate = :date")
    SwingScore findByKey(@Param("itemCd") String itemCd, @Param("date") String date);

    @Query(value = "select e from SwingScore e where e.id.item_cd = :itemCd order by e.id.stckBsopDate desc limit 1")
    SwingScore findByLastData(@Param("itemCd") String itemCd);
}
