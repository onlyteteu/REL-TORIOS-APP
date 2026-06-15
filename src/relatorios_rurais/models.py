from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .formatters import ALQUEIRE_GOIANO_HECTARES, format_area_alqueire, quantize_2


MissingText = "Não informado"


class AreaInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["own", "leased", "total"]
    value_alqueires: Decimal
    source_text: str

    @property
    def hectares(self) -> Decimal:
        return quantize_2(self.value_alqueires * ALQUEIRE_GOIANO_HECTARES)

    @property
    def display(self) -> str:
        return format_area_alqueire(self.value_alqueires)


class HectareAreaInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["total", "pasture", "crop"]
    hectares: Decimal
    source_text: str


class LivestockInfo(BaseModel):
    species: str = "Gado"
    breed: str | None = None
    count_heads: int | None = None
    purpose: str | None = None
    source_text: str


class FishTankInfo(BaseModel):
    quantity: int | None = None
    dimensions: list[str] = Field(default_factory=list)
    source_text: str


class FishFarmingInfo(BaseModel):
    species: list[str] = Field(default_factory=list)
    tanks: list[FishTankInfo] = Field(default_factory=list)
    source_text: str


class MachineInfo(BaseModel):
    description: str = MissingText
    manufacturer: str = "-"
    model: str = "-"
    source_text: str | None = None


class RuralVisitReport(BaseModel):
    client_name: str = MissingText
    municipality: str | None = None
    uf: str | None = None
    property_name: str = MissingText
    exploitation_type: str = MissingText
    productive_situation: str = MissingText
    own_area: AreaInfo | None = None
    leased_area: AreaInfo | None = None
    total_area: AreaInfo | None = None
    total_area_hectares: HectareAreaInfo | None = None
    pasture_area_hectares: HectareAreaInfo | None = None
    crop_area_hectares: HectareAreaInfo | None = None
    activities: list[str] = Field(default_factory=list)
    main_activity: str = MissingText
    main_cultures: list[str] = Field(default_factory=list)
    livestock: list[LivestockInfo] = Field(default_factory=list)
    fish_farming: FishFarmingInfo | None = None
    forage_species: list[str] = Field(default_factory=list)
    pasture_conditions: list[str] = Field(default_factory=list)
    crops: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    paddocks: list[str] = Field(default_factory=list)
    troughs: list[str] = Field(default_factory=list)
    fences: list[str] = Field(default_factory=list)
    corrals: list[str] = Field(default_factory=list)
    support_structures: list[str] = Field(default_factory=list)
    water_resources: list[str] = Field(default_factory=list)
    herd_movements: list[str] = Field(default_factory=list)
    machines: list[MachineInfo] = Field(default_factory=lambda: [MachineInfo()])
    missing_warnings: list[str] = Field(default_factory=list)
    technical_comments: str = MissingText
    conclusion: str = MissingText
    source_lines: list[str] = Field(default_factory=list)

    @field_validator("client_name", "property_name", mode="before")
    @classmethod
    def blank_to_missing(cls, value: str | None) -> str:
        if value is None or not str(value).strip():
            return MissingText
        return str(value).strip()

    @property
    def municipality_uf(self) -> str:
        if self.municipality and self.uf:
            return f"{self.municipality} - {self.uf}"
        if self.municipality:
            return self.municipality
        if self.uf:
            return self.uf
        return MissingText


class GenerationInput(BaseModel):
    notes: str
    template_path: Path
    output_dir: Path
    cell_map_path: Path
    client_name: str | None = None
    municipality: str | None = None
    uf: str | None = None
