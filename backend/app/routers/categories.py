"""Reference data the frontend needs to stay in sync with the backend's
canonical category list -- avoids hardcoding categories in the UI."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.models.category import CATEGORIES, CATEGORY_ICONS

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryInfo(BaseModel):
    name: str
    # Lucide icon name, e.g. "shopping-cart"
    icon: str


@router.get("", response_model=list[CategoryInfo])
async def read_categories():
    """List every canonical category with its Lucide icon name."""
    return [
        CategoryInfo(name=name, icon=CATEGORY_ICONS.get(name, "circle-dot"))
        for name in CATEGORIES
    ]
