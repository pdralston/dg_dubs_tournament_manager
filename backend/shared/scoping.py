"""Org-scoping layer for tenant-owned models.

Two mechanisms keep org isolation in one place instead of scattered across
every route/service:

  * ``tenant_query(Model)`` — returns a query pre-filtered to the current org.
    Services should use this instead of ``Model.query`` for tenant models.

  * a ``before_flush`` SQLAlchemy hook — stamps ``org_id`` on new tenant rows
    from the current org context, and blocks cross-org writes.

``init_scoping(app, db)`` registers the flush hook. Org context comes from
``backend.shared.org_context.current_org_id``.
"""

from flask import g, has_request_context
from sqlalchemy import event

from backend.models import TenantMixin
from backend.shared.org_context import current_org_id


def _is_tenant(obj) -> bool:
    return isinstance(obj, TenantMixin)


def tenant_query(model):
    """Return ``model.query`` filtered to the current org.

    Only valid for models using ``TenantMixin``.
    """
    if not (isinstance(model, type) and issubclass(model, TenantMixin)):
        raise TypeError(f"tenant_query requires a TenantMixin model, got {model!r}")
    return model.query.filter(model.org_id == current_org_id())


def init_scoping(app, db):
    """Register the before_flush hook that stamps/validates org_id."""

    @event.listens_for(db.session, 'before_flush')
    def _stamp_org_id(sess, flush_context, instances):  # noqa: ANN001
        # Only stamp within a request context; outside one (CLI, migrations,
        # boot-time load) there is no org to resolve and tenant writes should
        # set org_id explicitly.
        if not has_request_context():
            return
        oid = current_org_id()
        for obj in sess.new:
            if _is_tenant(obj):
                if getattr(obj, 'org_id', None) is None:
                    obj.org_id = oid
                elif obj.org_id != oid:
                    raise PermissionError(
                        f"Cross-org write blocked: object org_id={obj.org_id} "
                        f"but current org={oid}"
                    )
