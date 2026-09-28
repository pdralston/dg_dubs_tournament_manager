"""create DG-Tags tables (org-scoped)

Revision ID: a1b2c3d4e5f6
Revises: 185e089a4a4b
Create Date: 2026-09-27

Creates the seven DG-Tags tables with org_id baked in from the start, matching
the final SQLAlchemy models. Positioned after the governance migration (so
organizations exists for the org_id FK) and before the Dubs org_id migration.

On prod, the DG-Tags tables do not exist yet, so this creates them fresh (no
data at risk). On a dev DB that already has them from earlier create_all runs,
wipe/rebuild from the chain to validate; this migration assumes the tables are
absent (standard for a fresh environment / prod).

Note: member_contact_info intentionally has NO phone column and NO org_id
(PII scoped transitively via tag_members.member_id).
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '185e089a4a4b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tag_members',
        sa.Column('member_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('udisc_name', sa.String(length=100), nullable=True),
        sa.Column('current_tag', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('member_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_tag_members_org_id'),
    )
    op.create_index('ix_tag_members_org_id', 'tag_members', ['org_id'])

    op.create_table(
        'member_contact_info',
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('shipping_address', sa.Text(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('member_id'),
        sa.ForeignKeyConstraint(
            ['member_id'], ['tag_members.member_id'],
            name='fk_member_contact_info_member', ondelete='CASCADE',
        ),
    )

    op.create_table(
        'tag_events',
        sa.Column('event_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.Enum('annual', 'monthly', name='event_type_enum'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('course', sa.String(length=200), nullable=True),
        sa.Column('status', sa.Enum('pending', 'scheduled', 'in_progress', 'complete', name='event_status_enum'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('event_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_tag_events_org_id'),
    )
    op.create_index('ix_tag_events_org_id', 'tag_events', ['org_id'])

    op.create_table(
        'tag_registrations',
        sa.Column('reg_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('is_player', sa.Boolean(), nullable=True),
        sa.Column('is_checked_in', sa.Boolean(), nullable=True),
        sa.Column('is_dnf', sa.Boolean(), nullable=True),
        sa.Column('old_tag', sa.Integer(), nullable=True),
        sa.Column('round_score', sa.Integer(), nullable=True),
        sa.Column('new_tag', sa.Integer(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('reg_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_tag_registrations_org_id'),
        sa.ForeignKeyConstraint(['event_id'], ['tag_events.event_id'], name='fk_tag_registrations_event'),
        sa.ForeignKeyConstraint(['member_id'], ['tag_members.member_id'], name='fk_tag_registrations_member'),
        sa.UniqueConstraint('event_id', 'member_id', name='uq_tag_event_member'),
    )
    op.create_index('ix_tag_registrations_org_id', 'tag_registrations', ['org_id'])

    op.create_table(
        'tag_history',
        sa.Column('history_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('old_tag', sa.Integer(), nullable=True),
        sa.Column('new_tag', sa.Integer(), nullable=False),
        sa.Column('round_score', sa.Integer(), nullable=True),
        sa.Column('is_dnf', sa.Boolean(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('history_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_tag_history_org_id'),
        sa.ForeignKeyConstraint(['member_id'], ['tag_members.member_id'], name='fk_tag_history_member'),
        sa.ForeignKeyConstraint(['event_id'], ['tag_events.event_id'], name='fk_tag_history_event'),
    )
    op.create_index('ix_tag_history_org_id', 'tag_history', ['org_id'])

    op.create_table(
        'tag_inventory',
        sa.Column('inventory_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('season_year', sa.Integer(), nullable=False),
        sa.Column('total_tags', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('inventory_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_tag_inventory_org_id'),
        sa.UniqueConstraint('org_id', 'season_year', name='uq_tag_inventory_org_season'),
    )
    op.create_index('ix_tag_inventory_org_id', 'tag_inventory', ['org_id'])

    op.create_table(
        'tag_unavailable',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('season_year', sa.Integer(), nullable=False),
        sa.Column('tag_number', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_tag_unavailable_org_id'),
        sa.UniqueConstraint('org_id', 'season_year', 'tag_number', name='uq_tag_unavailable_org_season_tag'),
    )
    op.create_index('ix_tag_unavailable_org_id', 'tag_unavailable', ['org_id'])


def downgrade():
    op.drop_table('tag_unavailable')
    op.drop_table('tag_inventory')
    op.drop_table('tag_history')
    op.drop_table('tag_registrations')
    op.drop_table('tag_events')
    op.drop_table('member_contact_info')
    op.drop_table('tag_members')
