package me.project.snowbot.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import me.project.snowbot.entity.ItemEquity;

/**
 * `ItemEquity` 엔티티의 데이터베이스 접근 및 조작을 담당하는 리포지토리 인터페이스이다.
 * <p>
 * Spring Data JPA의 `JpaRepository`를 상속받아 기본적인 CRUD(생성, 조회, 수정, 삭제) 및
 * 페이징, 정렬 기능을 자동으로 제공받는다. `ItemEquity`의 기본 키(ID) 타입은 `String`이다.
 * </p>
 */
public interface ItemEquityRepository extends JpaRepository<ItemEquity, String> {

    /**
     * 주어진 종목 코드(itemCd)와 일치하는 `ItemEquity` 엔티티를 단건 조회하는 메서드이다.
     * <p>
     * `@Query` 어노테이션을 사용하여 직접 정의한 JPQL 쿼리를 실행한다.
     * 쿼리 내용상 입력받은 `id`와 동일한 `itemCd`를 가진 데이터를 조회하며,
     * `itemCd`를 기준으로 내림차순 정렬하여 결과를 반환한다.
     * (단건 조회이므로 정렬의 의미는 크지 않을 수 있으나 쿼리에 명시되어 있음)
     * </p>
     *
     * @param id 조회할 대상의 종목 코드(itemCd) 값이다. 쿼리의 `:id` 파라미터에 바인딩된다.
     * @return 조회된 `ItemEquity` 엔티티 객체이다. 조건에 맞는 데이터가 없을 경우 `null`이 반환될 수 있다.
     */
    @Query(value = "select e from ItemEquity e where e.itemCd = :id order by e.itemCd desc")
    ItemEquity findByKey(@Param("id") String id);
}