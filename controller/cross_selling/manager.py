from typing import List

from submodules.model.business_objects import cross_selling as cross_selling_bo
from submodules.model.models import CrossSelling
from submodules.model.util import sql_alchemy_to_dict
from submodules.model.exceptions import EntityNotFoundException


def get_cross_selling(cross_selling_id: str) -> CrossSelling:
    entity = cross_selling_bo.get(cross_selling_id)
    if not entity:
        raise EntityNotFoundException(f"Cross selling {cross_selling_id} not found")
    return entity


def get_all_cross_sellings() -> List[CrossSelling]:
    return cross_selling_bo.get_all()


def create_cross_selling(name: str = None):
    return cross_selling_bo.create(name=name, with_commit=True)


def update_cross_selling(cross_selling_id: str, name: str = None) -> CrossSelling:
    entity = cross_selling_bo.update(cross_selling_id, name=name, with_commit=True)
    if not entity:
        raise EntityNotFoundException(f"Cross selling {cross_selling_id} not found")
    return entity


def delete_cross_selling(cross_selling_id: str) -> None:
    entity = cross_selling_bo.get(cross_selling_id)
    if not entity:
        return
    cross_selling_bo.delete(cross_selling_id, with_commit=True)
