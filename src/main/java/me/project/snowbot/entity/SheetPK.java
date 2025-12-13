package me.project.snowbot.entity;

import java.io.Serializable;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.Data;

@Embeddable
@Data
public class SheetPK implements Serializable {
    private String item_cd;
    @Column(length = 1)
    private String sheet_cl;			//시트구분(년도-0/분기-1), pk
    @Column(length = 6)
    private String stac_yymm;			//결산년월, pk
}
