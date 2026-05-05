from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import VMActionLog, VMInstance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client():
    """Return an APIClient authenticated with a fresh JWT access token."""
    user, _ = User.objects.get_or_create(username='testuser')
    user.set_password('testpass123')
    user.save()

    anon = APIClient()
    res = anon.post(
        reverse('token_obtain_pair'),
        {'username': 'testuser', 'password': 'testpass123'},
        format='json',
    )
    client = APIClient()
    client.default_format = 'json'
    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {res.data["access"]}',
        HTTP_ACCEPT='application/json',
    )
    return client


def _provision(client, name='test-vm', **overrides):
    payload = {
        'name': name,
        'image_id': 'img-ubuntu-22.04',
        'flavor_id': 'm1.small',
        'network_id': 'net-private',
        'key_name': 'test-key',
        **overrides,
    }
    return client.post(reverse('vm-instance-list'), payload, format='json')


# ---------------------------------------------------------------------------
# Auth endpoint tests
# ---------------------------------------------------------------------------

class AuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('authuser', password='pass1234')

    def test_login_returns_access_and_refresh_tokens(self):
        res = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'authuser', 'password': 'pass1234'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_login_wrong_password_returns_401(self):
        res = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'authuser', 'password': 'wrong'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_request_returns_401(self):
        res = self.client.get(reverse('vm-instance-list'))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_returns_new_access_token(self):
        login = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'authuser', 'password': 'pass1234'},
            format='json',
        )
        res = self.client.post(
            reverse('token_refresh'),
            {'refresh': login.data['refresh']},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)


# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------

class ProvisionTests(APITestCase):
    def setUp(self):
        self.client = _make_client()

    def test_provision_returns_201_with_active_status(self):
        res = _provision(self.client)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], 'ACTIVE')
        self.assertIn('provider_instance_id', res.data)

    def test_provision_creates_audit_log(self):
        res = _provision(self.client)
        vm = VMInstance.objects.get(pk=res.data['id'])
        self.assertTrue(VMActionLog.objects.filter(vm=vm, action='PROVISION').exists())

    def test_provision_duplicate_name_returns_400(self):
        _provision(self.client, name='unique-vm')
        res = _provision(self.client, name='unique-vm')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_provision_missing_required_field_returns_400(self):
        res = self.client.post(reverse('vm-instance-list'), {'name': 'no-image'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# List & Retrieve
# ---------------------------------------------------------------------------

class ListRetrieveTests(APITestCase):
    def setUp(self):
        self.client = _make_client()
        _provision(self.client, name='vm-alpha')
        _provision(self.client, name='vm-beta')

    def test_list_returns_all_vms(self):
        res = self.client.get(reverse('vm-instance-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Paginated response wraps results in {"count": N, "results": [...]}
        self.assertEqual(res.data['count'], 2)
        self.assertEqual(len(res.data['results']), 2)

    def test_retrieve_includes_action_history(self):
        vm_id = VMInstance.objects.first().pk
        res = self.client.get(reverse('vm-instance-detail', args=[vm_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('PROVISION', [a['action'] for a in res.data['actions']])

    def test_retrieve_nonexistent_returns_404(self):
        res = self.client.get(reverse('vm-instance-detail', args=[99999]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Full lifecycle: happy-path
# ---------------------------------------------------------------------------

class LifecycleHappyPathTests(APITestCase):
    def setUp(self):
        self.client = _make_client()
        self.vm_id = _provision(self.client).data['id']

    def test_stop_vm(self):
        res = self.client.post(reverse('vm-instance-stop', args=[self.vm_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'STOPPED')

    def test_start_vm(self):
        self.client.post(reverse('vm-instance-stop', args=[self.vm_id]))
        res = self.client.post(reverse('vm-instance-start', args=[self.vm_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'ACTIVE')

    def test_reboot_vm(self):
        res = self.client.post(reverse('vm-instance-reboot', args=[self.vm_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'ACTIVE')

    def test_delete_vm(self):
        res = self.client.delete(reverse('vm-instance-detail', args=[self.vm_id]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(VMInstance.objects.filter(pk=self.vm_id).exists())

    def test_full_lifecycle_no_exception(self):
        self.client.post(reverse('vm-instance-stop', args=[self.vm_id]))
        self.client.post(reverse('vm-instance-start', args=[self.vm_id]))
        self.client.post(reverse('vm-instance-reboot', args=[self.vm_id]))
        self.client.delete(reverse('vm-instance-detail', args=[self.vm_id]))


# ---------------------------------------------------------------------------
# Invalid state-transition guards
# ---------------------------------------------------------------------------

class InvalidTransitionTests(APITestCase):
    def setUp(self):
        self.client = _make_client()
        self.vm_id = _provision(self.client).data['id']

    def test_start_already_active_vm_returns_409(self):
        res = self.client.post(reverse('vm-instance-start', args=[self.vm_id]))
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_stop_already_stopped_vm_returns_409(self):
        self.client.post(reverse('vm-instance-stop', args=[self.vm_id]))
        res = self.client.post(reverse('vm-instance-stop', args=[self.vm_id]))
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_action_on_nonexistent_vm_returns_404(self):
        res = self.client.post(reverse('vm-instance-start', args=[99999]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class HealthCheckTests(APITestCase):
    def test_liveness_returns_200(self):
        res = self.client.get(reverse('healthz'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'ok')

    def test_readiness_returns_200(self):
        res = self.client.get(reverse('readyz'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'ok')
        self.assertIn('db', res.data)

    def test_health_endpoints_require_no_auth(self):
        # No credentials — should still return 200, not 401
        anon = APIClient()
        self.assertEqual(anon.get(reverse('healthz')).status_code, status.HTTP_200_OK)
        self.assertEqual(anon.get(reverse('readyz')).status_code, status.HTTP_200_OK)
