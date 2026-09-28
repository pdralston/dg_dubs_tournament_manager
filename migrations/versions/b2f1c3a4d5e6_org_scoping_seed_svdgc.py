"""org scoping (Dubs): add org_id to Dubs tables, backfill SVDGC, memberships, re-scope players.name

Revision ID: b2f1c3a4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2026-09-27

Adds org_id to the DG-Dubs tables (which hold real data in prod) and backfills
them to SVDGC (org_id=1, seeded in 185e089a4a4b). Also backfills one org
membership per existing user, and re-scopes players.name uniqueness to be
per-org.

The DG-Tags tables are created already-org-scoped in a1b2c3d4e5f6, so they are
NOT handled here.

All operations on Dubs tables are additive (ADD COLUMN + backfill + constraints)
— prod-safe, no data loss. The players.name change swaps a global unique index
for a composite (org_id, name) unique; safe as long as names were already
unique (they were).
"""
from alembic import op
import sqlalchemy as sa


revision = 'b2f1c3a4d5e6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


# DG-Dubs tenant tables (hold data in prod). Tags tables are created org-scoped
# in the prior migration and are excluded here.
DUBS_TABLES = [
    'players',
    'tournaments',
    'teams',
    'player_history',
    'tournament_participants',
    'ace_pot_tracker',
    'ace_pot_config',
    'seasons',
]

SVDGC_ORG_ID = 1


def upgrade():
    conn = op.get_bind()

    # 1. Add nullable org_id + backfill to SVDGC on each Dubs table.
    for table in DUBS_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column('org_id', sa.Integer(), nullable=True))
        conn.execute(sa.text(f"UPDATE {table} SET org_id = :oid"), {"oid": SVDGC_ORG_ID})

    # 2. One membership per existing user, mirroring their current global role.
    users = conn.execute(sa.text("SELECT id, role FROM users")).fetchall()
    for user_id, role in users:
        norm = role if role in ('admin', 'director', 'viewer') else 'viewer'
        conn.execute(sa.text(
            "INSERT INTO org_memberships (org_id, user_id, app, role, created_at) "
            "VALUES (:oid, :uid, '*', :role, NOW())"
        ), {"oid": SVDGC_ORG_ID, "uid": user_id, "role": norm})

    # 3. Enforce NOT NULL + FK + index on each Dubs table.
    for table in DUBS_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column('org_id', existing_type=sa.Integer(), nullable=False)
            batch_op.create_index(f'ix_{table}_org_id', ['org_id'])
            batch_op.create_foreign_key(
                f'fk_{table}_org_id', 'organizations', ['org_id'], ['org_id']
            )

    # 4. Re-scope players.name: drop global unique key `name`, keep plain
    #    idx_player_name, add composite unique (org_id, name).
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_constraint('name', type_='unique')
        batch_op.create_unique_constraint('uq_players_org_name', ['org_id', 'name'])


def downgrade():
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_constraint('uq_players_org_name', type_='unique')
        batch_op.create_unique_constraint('name', ['name'])

    for table in DUBS_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(f'fk_{table}_org_id', type_='foreignkey')
            batch_op.drop_index(f'ix_{table}_org_id')
            batch_op.drop_column('org_id')

    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM org_memberships WHERE org_id = :oid"),
                 {"oid": SVDGC_ORG_ID})
