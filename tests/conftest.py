import pytest

from jobsearcher.db.database import connect, init_db


@pytest.fixture
def conn():
    connection = connect(":memory:")
    init_db(connection)
    yield connection
    connection.close()
