"""Role and permission management service layer."""

from app.auth.casbin import (
    get_casbin_enforcer,
    ROLE_ADMIN,
    ROLE_REVIEWER,
    ROLE_AUDITOR,
)


class RoleService:
    """Service for managing roles and permissions."""

    @staticmethod
    async def assign_role(user_id: str, role: str) -> None:
        """Assign a role to a user.
        
        Args:
            user_id: User identifier
            role: Role name (admin, reviewer, auditor)
        """
        enforcer = get_casbin_enforcer()

        # Remove existing roles for user
        enforcer.delete_roles_for_user(user_id)

        # Assign new role
        if role in (ROLE_ADMIN, ROLE_REVIEWER, ROLE_AUDITOR):
            enforcer.add_role_for_user(user_id, role)
            enforcer.save_policy()

    @staticmethod
    async def remove_role(user_id: str) -> None:
        """Remove all roles from a user.
        
        Args:
            user_id: User identifier
        """
        enforcer = get_casbin_enforcer()
        enforcer.delete_roles_for_user(user_id)
        enforcer.save_policy()

    @staticmethod
    async def get_user_roles(user_id: str) -> list[str]:
        """Get all roles assigned to a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of role names
        """
        enforcer = get_casbin_enforcer()
        return enforcer.get_roles_for_user(user_id)

    @staticmethod
    async def toggle_role(user_id: str, role: str) -> bool:
        """Toggle a role for a user (on/off).
        
        Args:
            user_id: User identifier
            role: Role name to toggle
            
        Returns:
            True if role was added, False if removed
        """
        current_roles = await RoleService.get_user_roles(user_id)

        if role in current_roles:
            await RoleService.remove_role(user_id)
            return False
        else:
            await RoleService.assign_role(user_id, role)
            return True

    @staticmethod
    async def seed_default_policies() -> None:
        """Seed default RBAC policies.
        
        Defines permissions:
        - admin: manage users, toggle roles, view audit log
        - reviewer: view batches, relabel predictions (confidence < 0.7)
        - auditor: read-only on batches and audit log
        """
        enforcer = get_casbin_enforcer()

        # Check if policies already exist
        all_policies = enforcer.get_policy()
        if all_policies:
            return

        # Admin permissions
        enforcer.add_policy(ROLE_ADMIN, "users", "create")
        enforcer.add_policy(ROLE_ADMIN, "users", "read")
        enforcer.add_policy(ROLE_ADMIN, "users", "update")
        enforcer.add_policy(ROLE_ADMIN, "users", "delete")
        enforcer.add_policy(ROLE_ADMIN, "users", "manage_roles")
        enforcer.add_policy(ROLE_ADMIN, "batches", "read")
        enforcer.add_policy(ROLE_ADMIN, "predictions", "read")
        enforcer.add_policy(ROLE_ADMIN, "predictions", "update")
        enforcer.add_policy(ROLE_ADMIN, "audit_log", "read")

        # Reviewer permissions
        enforcer.add_policy(ROLE_REVIEWER, "batches", "read")
        enforcer.add_policy(ROLE_REVIEWER, "predictions", "read")
        enforcer.add_policy(ROLE_REVIEWER, "predictions", "update")

        # Auditor permissions (read-only)
        enforcer.add_policy(ROLE_AUDITOR, "batches", "read")
        enforcer.add_policy(ROLE_AUDITOR, "audit_log", "read")

        enforcer.save_policy()
