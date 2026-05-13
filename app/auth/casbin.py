"""Casbin RBAC setup and model configuration."""

import casbin
from casbin_sqlalchemy_adapter import Adapter
from sqlalchemy import create_engine

from app.core.config import settings

# RBAC model definition
RBAC_MODEL = """
[request_definition]
r = sub, obj, act

[role_definition]
g = _, _

[policy_definition]
p = sub, obj, act

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
"""

# Roles
ROLE_ADMIN = "admin"
ROLE_REVIEWER = "reviewer"
ROLE_AUDITOR = "auditor"

# Resources
RESOURCE_USERS = "users"
RESOURCE_BATCHES = "batches"
RESOURCE_PREDICTIONS = "predictions"
RESOURCE_AUDIT_LOG = "audit_log"

# Actions
ACTION_CREATE = "create"
ACTION_READ = "read"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_MANAGE_ROLES = "manage_roles"

# Global enforcer instance
_enforcer: casbin.Enforcer | None = None
_sync_engine = None


def _create_sync_engine():
    global _sync_engine
    if _sync_engine is not None:
        return _sync_engine
    # casbin_sqlalchemy_adapter requires a synchronous engine.
    connect_args = (
        {"check_same_thread": False}
        if settings.DATABASE_SYNC_URL.startswith("sqlite")
        else {}
    )
    _sync_engine = create_engine(settings.DATABASE_SYNC_URL, connect_args=connect_args)
    return _sync_engine


def init_casbin_enforcer() -> casbin.Enforcer:
    """Initialize Casbin enforcer with SQLAlchemy adapter."""
    global _enforcer
    if _enforcer is not None:
        return _enforcer

    adapter = Adapter(_create_sync_engine())
    model = casbin.Model()
    model.load_model_from_text(RBAC_MODEL)
    _enforcer = casbin.Enforcer(model, adapter)
    _enforcer.load_policy()
    return _enforcer


def get_casbin_enforcer() -> casbin.Enforcer:
    """Get the global Casbin enforcer instance."""
    return init_casbin_enforcer()
