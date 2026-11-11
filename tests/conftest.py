import os

import httpx
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

os.environ.update(AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test", AWS_REGION="ap-south-1")
os.environ.pop("DYNAMODB_ENDPOINT", None)

from content_service.app import create_app as create_content  # noqa: E402
from mathpath_common.dynamo import resource  # noqa: E402
from practice_service.app import create_app as create_practice  # noqa: E402
from practice_service.content_client import ContentClient  # noqa: E402
from scripts.bootstrap import load_seed  # noqa: E402


@pytest.fixture
def ddb():
    with mock_aws():
        db = resource()
        load_seed(db)
        yield db


@pytest.fixture
def content_app(ddb):
    return create_content(ddb)


@pytest.fixture
def content(content_app):
    return content_app.test_client()


@pytest.fixture
def practice(ddb, content_app):
    # The practice service talks to the real Flask app over HTTP semantics (WSGI transport),
    # so the cross-service contract is exercised without opening sockets.
    client = ContentClient(base_url="http://content", transport=httpx.WSGITransport(app=content_app))
    return TestClient(create_practice(ddb, client))
