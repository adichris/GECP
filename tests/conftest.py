import pytest
from django.core.management import call_command

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('seed_gecp', skip_assets=True)


@pytest.fixture
def seeded(db):
    """Use the seeded test database; each test still receives rollback isolation."""
