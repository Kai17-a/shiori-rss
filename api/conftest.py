from api.tests.test_support import CompatTestClient


def pytest_configure():
    import fastapi.testclient as fastapi_testclient

    fastapi_testclient.TestClient = CompatTestClient
