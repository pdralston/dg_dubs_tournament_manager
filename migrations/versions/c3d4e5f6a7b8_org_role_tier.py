"""org-role tier: org_roles table, narrow org_memberships (drop '*'/'viewer')

Revision ID: c3d4e5f6a7b8
Revises: b2f1c3a4d5e6
Create Date: 2026-10-07

Implements the §13 Org-Role Tier scaffolding:

  * NEW governance table ``org_roles`` (org-wide owner/manager, no app column).
  * Data-migrate the legacy ``app='*'`` memberships into ``org_roles``
    (admin -> owner, director -> manager), then delete the '*' rows. Delete any
    ``role='viewer'`` membership rows (viewer is no longer a grant).
  * Narrow ``org_app_enum`` ('*' removed) and ``org_role_enum`` ('viewer'
    removed), and drop the ``server_default`` on both ``org_memberships``
    columns.

Ordering is deliberate: the data migration (step 2) MUST run before the enum
narrowing (step 3), because MySQL's in-place ``MODIFY COLUMN`` rejects the ALTER
while out-of-range values ('*'/'viewer') still exist in the column.

Dialect handling: on MySQL (prod) the enum change + default drop is an in-place
``ALTER TABLE ... MODIFY COLUMN``. On SQLite (local rehearsal/tests) there is no
real ENUM and ``MODIFY`` is unsupported, so a ``batch_alter_table`` rebuilds the
table with the new column definition (SQLite stores enums as plain TEXT, so the
narrowed value set is simply not enforced — acceptable for a dev rehearsal).
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'b2f1c3a4d5e6'
branch_labels = None
depends_on = None


# ── Enum value sets ──────────────────────────────────────────────────────────
APP_NARROW = ('dubs', 'tags', 'putt')
APP_WIDE = ('dubs', 'tags', 'putt', '*')
ROLE_NARROW = ('admin', 'director')
ROLE_WIDE = ('admin', 'director', 'viewer')


def _enum_sql(values):
    return "ENUM(" + ", ".join(f"'{v}'" for v in values) + ")"


def _mysql_modify(app_values, role_values, app_default=None, role_default=None):
    """Emit MySQL MODIFY COLUMN statements for the two enum columns.

    ``*_default`` is the server default to set; None drops the default.
    """
    app_def = f" DEFAULT '{app_default}'" if app_default else ""
    role_def = f" DEFAULT '{role_default}'" if role_default else ""
    op.execute(
        f"ALTER TABLE org_memberships "
        f"MODIFY COLUMN app {_enum_sql(app_values)} NOT NULL{app_def}"
    )
    op.execute(
        f"ALTER TABLE org_memberships "
        f"MODIFY COLUMN role {_enum_sql(role_values)} NOT NULL{role_def}"
    )


def _is_sqlite():
    return op.get_bind().dialect.name == 'sqlite'


def upgrade():
    conn = op.get_bind()

    # 1. Create the governance table.
    op.create_table(
        'org_roles',
        sa.Column('org_role_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column(
            'role',
            sa.Enum('owner', 'manager', name='org_governance_role_enum'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('org_role_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.UniqueConstraint('org_id', 'user_id', name='uq_org_user_role'),
    )

    # 2. Data migration BEFORE enum narrowing.
    #    Legacy wildcard memberships -> governance rows (admin->owner,
    #    director->manager).
    now_expr = "NOW()" if not _is_sqlite() else "CURRENT_TIMESTAMP"
    wildcard_rows = conn.execute(sa.text(
        "SELECT org_id, user_id, role FROM org_memberships WHERE app = '*'"
    )).fetchall()
    for org_id, user_id, role in wildcard_rows:
        gov_role = 'owner' if role == 'admin' else 'manager'
        # Guard against a pre-existing governance row for this (org, user).
        exists = conn.execute(sa.text(
            "SELECT COUNT(*) FROM org_roles WHERE org_id = :o AND user_id = :u"
        ), {"o": org_id, "u": user_id}).scalar()
        if not exists:
            conn.execute(sa.text(
                "INSERT INTO org_roles (org_id, user_id, role, created_at) "
                f"VALUES (:o, :u, :r, {now_expr})"
            ), {"o": org_id, "u": user_id, "r": gov_role})

    # Delete the migrated wildcard rows and any viewer rows (no longer grantable).
    conn.execute(sa.text("DELETE FROM org_memberships WHERE app = '*'"))
    conn.execute(sa.text("DELETE FROM org_memberships WHERE role = 'viewer'"))

    # 3. Narrow the enums + drop server defaults.
    if _is_sqlite():
        with op.batch_alter_table('org_memberships', schema=None) as batch_op:
            batch_op.alter_column(
                'app',
                existing_type=sa.Enum(*APP_WIDE, name='org_app_enum'),
                type_=sa.Enum(*APP_NARROW, name='org_app_enum'),
                existing_nullable=False,
                server_default=None,
            )
            batch_op.alter_column(
                'role',
                existing_type=sa.Enum(*ROLE_WIDE, name='org_role_enum'),
                type_=sa.Enum(*ROLE_NARROW, name='org_role_enum'),
                existing_nullable=False,
                server_default=None,
            )
    else:
        _mysql_modify(APP_NARROW, ROLE_NARROW)  # defaults dropped (None)


def downgrade():
    conn = op.get_bind()

    # 1. Re-widen enums + restore the original server defaults.
    if _is_sqlite():
        with op.batch_alter_table('org_memberships', schema=None) as batch_op:
            batch_op.alter_column(
                'app',
                existing_type=sa.Enum(*APP_NARROW, name='org_app_enum'),
                type_=sa.Enum(*APP_WIDE, name='org_app_enum'),
                existing_nullable=False,
                server_default='*',
            )
            batch_op.alter_column(
                'role',
                existing_type=sa.Enum(*ROLE_NARROW, name='org_role_enum'),
                type_=sa.Enum(*ROLE_WIDE, name='org_role_enum'),
                existing_nullable=False,
                server_default='viewer',
            )
    else:
        _mysql_modify(APP_WIDE, ROLE_WIDE, app_default='*', role_default='viewer')

    # 2. Re-materialize wildcard memberships from governance rows, then drop
    #    the governance rows. owner -> admin, manager -> director.
    now_expr = "NOW()" if not _is_sqlite() else "CURRENT_TIMESTAMP"
    gov_rows = conn.execute(sa.text(
        "SELECT org_id, user_id, role FROM org_roles"
    )).fetchall()
    for org_id, user_id, role in gov_rows:
        app_role = 'admin' if role == 'owner' else 'director'
        exists = conn.execute(sa.text(
            "SELECT COUNT(*) FROM org_memberships "
            "WHERE org_id = :o AND user_id = :u AND app = '*'"
        ), {"o": org_id, "u": user_id}).scalar()
        if not exists:
            conn.execute(sa.text(
                "INSERT INTO org_memberships (org_id, user_id, app, role, created_at) "
                f"VALUES (:o, :u, '*', :r, {now_expr})"
            ), {"o": org_id, "u": user_id, "r": app_role})

    # 3. Drop the governance table.
    op.drop_table('org_roles')
