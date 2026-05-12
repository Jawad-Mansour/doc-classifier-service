#!/usr/bin/env python3
"""Seed Casbin RBAC policies.

Usage:
    python scripts/seed_policies.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.role_service import RoleService


async def main():
    """Seed default RBAC policies."""
    try:
        print("🌱 Seeding RBAC policies...")
        await RoleService.seed_default_policies()
        print("✅ RBAC policies seeded successfully!")
        print()
        print("Policies:")
        print("  admin: manage users, toggle roles, view audit log")
        print("  reviewer: view batches, relabel predictions")
        print("  auditor: read-only on batches and audit log")
    except Exception as e:
        print(f"❌ Error seeding policies: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
