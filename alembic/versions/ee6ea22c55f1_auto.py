"""auto

Revision ID: ee6ea22c55f1
Revises: 
Create Date: 2025-02-16 23:39:48.228900

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee6ea22c55f1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('institutions',
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('domain', sa.String(length=100), nullable=False),
    sa.Column('logo', sa.String(length=500), nullable=True),
    sa.Column('scraper_status', sa.Enum('not_started', 'queued', 'in_progress', 'completed', 'failed', 'cancelled', name='scraperstatus'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('average_rating', sa.Float(), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('domain')
    )
    op.create_table('courses',
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('hero_image', sa.String(length=500), nullable=True),
    sa.Column('degree_type', sa.Enum('bachelor', 'master', 'phd', 'not_specified', name='degreetype'), nullable=True),
    sa.Column('study_mode', sa.Enum('full_time', 'part_time', 'online', 'hybrid', 'not_specified', name='studymode'), nullable=True),
    sa.Column('ects_credits', sa.Integer(), nullable=True),
    sa.Column('teaching_language', sa.String(length=200), nullable=True),
    sa.Column('diploma_awarded', sa.String(length=500), nullable=True),
    sa.Column('start_date', sa.String(), nullable=True),
    sa.Column('end_date', sa.String(), nullable=True),
    sa.Column('duration_in_semesters', sa.Integer(), nullable=True),
    sa.Column('application_deadline', sa.String(), nullable=True),
    sa.Column('campus_location', sa.String(length=200), nullable=True),
    sa.Column('study_abroad_available', sa.Boolean(), nullable=False),
    sa.Column('tuition_fee_per_semester', sa.String(), nullable=True),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('is_featured', sa.Boolean(), nullable=False),
    sa.Column('average_rating', sa.Float(), nullable=False),
    sa.Column('total_reviews', sa.Integer(), nullable=False),
    sa.Column('detailed_content', sa.Text(), nullable=True),
    sa.Column('institution_id', sa.String(), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('first_name', sa.String(length=30), nullable=False),
    sa.Column('last_name', sa.String(length=30), nullable=False),
    sa.Column('email', sa.String(length=50), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('password', sa.String(), nullable=False),
    sa.Column('avatar', sa.String(), nullable=True),
    sa.Column('role', sa.Enum('user', 'instructor', 'admin', name='userrole'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_verified', sa.Boolean(), nullable=False),
    sa.Column('verification_token', sa.String(length=255), nullable=True),
    sa.Column('verification_token_expires', sa.DateTime(), nullable=True),
    sa.Column('institution_id', sa.String(), nullable=True),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('verification_token')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('course_bookmarks',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('course_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'course_id')
    )
    op.create_table('sessions',
    sa.Column('access_token', sa.String(length=500), nullable=False),
    sa.Column('refresh_token', sa.String(length=500), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('sessions')
    op.drop_table('course_bookmarks')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('courses')
    op.drop_table('institutions')
    # ### end Alembic commands ###
