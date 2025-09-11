import pytest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from typing import Iterator

from app import app

from submodules.model.business_objects import (
    organization as organization_bo,
    user as user_bo,
    project as project_bo,
    general,
)
from submodules.s3 import controller as s3
from submodules.model.models import (
    Project as RefineryProject,
)


@pytest.fixture(scope="session", autouse=True)
def database_session() -> Iterator[None]:
    general.get_ctx_token()
    yield
    general.remove_and_refresh_session()


@pytest.fixture(scope="session")
def org_id() -> Iterator[str]:
    org_item = organization_bo.create(name="test_org", with_commit=True)
    s3.create_bucket(str(org_item.id))
    org_id = str(org_item.id)
    yield org_id
    organization_bo.delete(org_id, with_commit=True)
    s3.remove_bucket(org_id, True)


@pytest.fixture(scope="session")
def user_id(org_id: str) -> Iterator[str]:
    user_item = user_bo.create(user_id=uuid.uuid4(), with_commit=True)
    user_bo.update_organization(user_id=user_item.id, organization_id=org_id)
    yield str(user_item.id)


@pytest.fixture(scope="session")
def refinery_project(org_id: str, user_id: str) -> Iterator[RefineryProject]:
    project_item = project_bo.create(
        organization_id=org_id,
        name="test_project",
        description="test_description",
        created_by=user_id,
        tokenizer="en_core_web_sm",
        with_commit=True,
    )
    yield project_item
    project_bo.delete(project_item.id)


@pytest.fixture
def client(user_id: str) -> Iterator[TestClient]:
    with patch("controller.auth.manager.DEV_USER_ID", user_id):
        with TestClient(app, base_url="http://localhost:7051") as client:
            yield client
