package me.project.snowbot.entity;

import java.math.BigDecimal;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;
import lombok.ToString;

@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "etc_sheet")
@ToString()
@Data
@EqualsAndHashCode(callSuper = false)
public class EtcSheet {
    @EmbeddedId
    private SheetPK id;

    @Column(precision = 23, scale = 2)
    private BigDecimal ebitda;	//EBITDA
    @Column(precision = 23, scale = 2)
    private BigDecimal ev_ebitda;	//EV_EBITDA
}
