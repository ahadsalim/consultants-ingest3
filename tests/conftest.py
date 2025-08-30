import pytest
from django.contrib.auth.models import User, Group
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def db_setup(db):
    """Set up database with required groups."""
    Group.objects.get_or_create(name='Operator')
    Group.objects.get_or_create(name='Reviewer')
    Group.objects.get_or_create(name='Admin')


@pytest.fixture
def user_operator(db_setup):
    """Create an operator user."""
    user = User.objects.create_user(
        username='operator',
        email='operator@test.com',
        password='testpass123'
    )
    operator_group = Group.objects.get(name='Operator')
    user.groups.add(operator_group)
    return user


@pytest.fixture
def user_reviewer(db_setup):
    """Create a reviewer user."""
    user = User.objects.create_user(
        username='reviewer',
        email='reviewer@test.com',
        password='testpass123'
    )
    reviewer_group = Group.objects.get(name='Reviewer')
    user.groups.add(reviewer_group)
    return user


@pytest.fixture
def user_admin(db_setup):
    """Create an admin user."""
    user = User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123'
    )
    admin_group = Group.objects.get(name='Admin')
    user.groups.add(admin_group)
    return user


@pytest.fixture
def api_client():
    """Return DRF API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user_operator):
    """Return authenticated API client."""
    refresh = RefreshToken.for_user(user_operator)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client
