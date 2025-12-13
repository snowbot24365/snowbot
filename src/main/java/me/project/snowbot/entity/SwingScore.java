package me.project.snowbot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "swing_score")
public class SwingScore {
    @EmbeddedId
    private SwingScorePK id;

    @Column(name = "sheet_score")
    private Integer sheetScore;

    @Column(name = "trend_score")
    private Integer trendScore;

    @Column(name = "price_score")
    private Integer priceScore;

    @Column(name = "kpi_score")
    private Integer kpiScore;

    @Column(name = "buy_score")
    private Integer buyScore;

    @Column(name = "avls_score")
    private Integer avlsScore;

    @Column(name = "per_score")
    private Integer perScore;

    @Column(name = "pbr_score")
    private Integer pbrScore;

    @Column(name = "total_score")
    private Integer totalScore;
}
