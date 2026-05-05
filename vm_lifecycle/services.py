from dataclasses import dataclass


@dataclass
class ProviderVM:
    id: str
    status: str


class OpenStackService:
    """Thin adapter around a provider.

    This PoC keeps provider interactions simple and deterministic for local testing.
    """

    def create_vm(self, name: str, image_id: str, flavor_id: str, network_id: str, key_name: str = '') -> ProviderVM:
        provider_id = f'vm-{name.lower().replace(" ", "-")}'
        return ProviderVM(id=provider_id, status='ACTIVE')

    def start_vm(self, provider_id: str) -> ProviderVM:
        return ProviderVM(id=provider_id, status='ACTIVE')

    def stop_vm(self, provider_id: str) -> ProviderVM:
        return ProviderVM(id=provider_id, status='STOPPED')

    def reboot_vm(self, provider_id: str) -> ProviderVM:
        return ProviderVM(id=provider_id, status='ACTIVE')

    def delete_vm(self, provider_id: str) -> ProviderVM:
        return ProviderVM(id=provider_id, status='DELETED')
