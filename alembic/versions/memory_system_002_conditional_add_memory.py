"""Add conversation memory system - conditional

Revision ID: memory_system_002
Revises: 22c354143f25
Create Date: 2025-09-28

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'memory_system_002'
down_revision = '22c354143f25'
branch_labels = None
depends_on = None

def upgrade():
    # Get current connection to check existing columns
    conn = op.get_bind()
    
    # Check what columns exist in users table
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users'
    """))
    existing_columns = [row[0] for row in result.fetchall()]
    
    # Only add columns that don't exist
    if 'business_context' not in existing_columns:
        op.add_column('users', sa.Column('business_context', sa.Text(), nullable=True))
        
    if 'conversation_summary' not in existing_columns:
        op.add_column('users', sa.Column('conversation_summary', sa.Text(), nullable=True))
        
    if 'business_type' not in existing_columns:
        op.add_column('users', sa.Column('business_type', sa.String(length=100), nullable=True))
        
    if 'last_interaction' not in existing_columns:
        op.add_column('users', sa.Column('last_interaction', sa.DateTime(), nullable=True))
    
    # Check if conversation_history table exists
    result = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'conversation_history'
    """))
    table_exists = result.fetchone() is not None
    
    # Only create table if it doesn't exist
    if not table_exists:
        op.create_table('conversation_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('user_message', sa.Text(), nullable=False),
            sa.Column('ai_response', sa.Text(), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('message_type', sa.String(length=50), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Check if indexes exist before creating
    result = conn.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE indexname IN ('idx_conversation_user_time', 'idx_users_last_interaction')
    """))
    existing_indexes = [row[0] for row in result.fetchall()]
    
    if 'idx_conversation_user_time' not in existing_indexes and not table_exists:
        op.create_index('idx_conversation_user_time', 'conversation_history', ['user_id', 'timestamp'], unique=False)
        
    if 'idx_users_last_interaction' not in existing_indexes:
        op.create_index('idx_users_last_interaction', 'users', ['last_interaction'], unique=False)

def downgrade():
    # Check what exists before trying to drop
    conn = op.get_bind()
    
    # Drop indexes if they exist
    result = conn.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE indexname IN ('idx_conversation_user_time', 'idx_users_last_interaction')
    """))
    existing_indexes = [row[0] for row in result.fetchall()]
    
    if 'idx_users_last_interaction' in existing_indexes:
        op.drop_index('idx_users_last_interaction', table_name='users')
        
    if 'idx_conversation_user_time' in existing_indexes:
        op.drop_index('idx_conversation_user_time', table_name='conversation_history')
    
    # Drop table if it exists
    result = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'conversation_history'
    """))
    if result.fetchone():
        op.drop_table('conversation_history')
    
    # Drop columns if they exist
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users'
    """))
    existing_columns = [row[0] for row in result.fetchall()]
    
    if 'last_interaction' in existing_columns:
        op.drop_column('users', 'last_interaction')
    if 'business_type' in existing_columns:
        op.drop_column('users', 'business_type')
    if 'conversation_summary' in existing_columns:
        op.drop_column('users', 'conversation_summary')
    if 'business_context' in existing_columns:
        op.drop_column('users', 'business_context')