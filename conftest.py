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
from submodules.model.models import (
    Organization,
    User,
    Project as RefineryProject,
)


@pytest.fixture(scope="session", autouse=True)
def database_session() -> Iterator[None]:
    session_token = general.get_ctx_token()
    yield
    general.remove_and_refresh_session(session_token)


@pytest.fixture(scope="session")
def org() -> Iterator[Organization]:
    org_item = organization_bo.create(name="test_org", with_commit=True)
    yield org_item
    organization_bo.delete(org_item.id, with_commit=True)


@pytest.fixture(scope="session")
def user(org: Organization) -> Iterator[User]:
    user_item = user_bo.create(user_id=uuid.uuid4(), with_commit=True)
    user_bo.update_organization(user_id=user_item.id, organization_id=org.id)
    yield user_item


@pytest.fixture(scope="session")
def refinery_project(org: Organization, user: User) -> Iterator[RefineryProject]:
    project_item = project_bo.create(
        organization_id=org.id,
        name="test_project",
        description="test_description",
        created_by=user.id,
        with_commit=True,
    )
    yield project_item
    project_bo.delete(project_item.id, with_commit=True)


@pytest.fixture
def client(user: User) -> Iterator[TestClient]:
    with patch("controller.auth.manager.DEV_USER_ID", str(user.id)):
        with TestClient(app, base_url="http://localhost:7051") as client:
            yield client
