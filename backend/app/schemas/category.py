from pydantic import BaseModel, Field

from app.models.category import CATEGORIES


class CategoryResponse(BaseModel):
    name: str
    icon: str


class CategoryRulesUpdate(BaseModel):
    rules: dict[str, str] = Field(
        description="Key-value mapping of keyword to category name"
    )
