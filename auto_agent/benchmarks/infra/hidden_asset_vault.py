"""
HiddenAssetVault - Hidden Asset Protection
=======================================

Yashirin assetlarni himoya qilish.

Bu modul:
- Alohida joyda saqlash
- Read-only
- Agent-visible tree'dan tashqarida
- Faqat verifier runner ko'radi

Definition of Done:
6. Hidden tests/verifiers agent-visible tree'dan tashqarida turadi.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import os
import hashlib
import json


@dataclass
class HiddenAsset:
    """Hidden asset."""
    asset_id: str
    asset_type: str  # test, verifier, canary, fixture
    path: str
    checksum: str
    permissions: str = "read_only"


class HiddenAssetVault:
    """
    Hidden asset vault.
    
    Definition of Done:
    6. Hidden tests/verifiers agent-visible tree'dan tashqarida turadi.
    """
    
    def __init__(self, vault_path: str = None):
        self.vault_path = vault_path or "/var/eval/hidden_vault"
        os.makedirs(self.vault_path, exist_ok=True)
        
        # Asset manifest
        self.manifest_path = os.path.join(self.vault_path, "manifest.json")
        self.manifest = self._load_manifest()
    
    def register_asset(
        self,
        asset_id: str,
        asset_type: str,
        source_path: str,
    ) -> HiddenAsset:
        """Assetni ro'yxatga olish."""
        # Read and hash
        with open(source_path, 'rb') as f:
            content = f.read()
            checksum = hashlib.sha256(content).hexdigest()
        
        # Copy to vault
        dest_path = os.path.join(self.vault_path, asset_type, asset_id)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        with open(dest_path, 'wb') as f:
            f.write(content)
        
        # Make read-only
        os.chmod(dest_path, 0o444)
        
        # Register
        asset = HiddenAsset(
            asset_id=asset_id,
            asset_type=asset_type,
            path=dest_path,
            checksum=checksum,
        )
        
        self.manifest[asset_id] = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "path": dest_path,
            "checksum": checksum,
        }
        
        self._save_manifest()
        
        return asset
    
    def get_asset_path(self, asset_id: str) -> Optional[str]:
        """Asset path olish."""
        return self.manifest.get(asset_id, {}).get("path")
    
    def verify_asset(self, asset_id: str) -> bool:
        """Asset to'g'ri ekanligini tekshirish."""
        asset_info = self.manifest.get(asset_id)
        if not asset_info:
            return False
        
        path = asset_info.get("path")
        if not os.path.exists(path):
            return False
        
        # Verify checksum
        with open(path, 'rb') as f:
            content = f.read()
            checksum = hashlib.sha256(content).hexdigest()
        
        return checksum == asset_info.get("checksum")
    
    def get_verifier_path(self, verifier_id: str) -> Optional[str]:
        """Verifier path olish."""
        return self.get_asset_path(f"verifier_{verifier_id}")
    
    def get_hidden_test_path(self, test_id: str) -> Optional[str]:
        """Hidden test path olish."""
        return self.get_asset_path(f"test_{test_id}")
    
    def _load_manifest(self) -> Dict:
        """Manifestni yuklash."""
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_manifest(self) -> None:
        """Manifestni saqlash."""
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)


def create_hidden_vault(vault_path: str = None) -> HiddenAssetVault:
    """Hidden vault yaratish."""
    return HiddenAssetVault(vault_path)
