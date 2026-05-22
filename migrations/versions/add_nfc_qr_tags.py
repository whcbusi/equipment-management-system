from alembic import op
import sqlalchemy as sa

def upgrade():
    # Users table
    op.add_column('users', sa.Column('nfc_tag_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('qr_code_id', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_users_nfc_tag_id', 'users', ['nfc_tag_id'])
    op.create_unique_constraint('uq_users_qr_code_id', 'users', ['qr_code_id'])
    op.create_index('ix_users_nfc_tag_id', 'users', ['nfc_tag_id'])
    op.create_index('ix_users_qr_code_id', 'users', ['qr_code_id'])
    
    # Equipment table
    op.add_column('equipment', sa.Column('nfc_tag_id', sa.String(255), nullable=True))
    op.add_column('equipment', sa.Column('qr_code_id', sa.String(255), nullable=True))
    op.add_column('equipment', sa.Column('qr_code_image', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_equipment_nfc_tag_id', 'equipment', ['nfc_tag_id'])
    op.create_unique_constraint('uq_equipment_qr_code_id', 'equipment', ['qr_code_id'])
    op.create_index('ix_equipment_nfc_tag_id', 'equipment', ['nfc_tag_id'])
    op.create_index('ix_equipment_qr_code_id', 'equipment', ['qr_code_id'])

def downgrade():
    op.drop_index('ix_equipment_qr_code_id', table_name='equipment')
    op.drop_index('ix_equipment_nfc_tag_id', table_name='equipment')
    op.drop_constraint('uq_equipment_qr_code_id', 'equipment', type_='unique')
    op.drop_constraint('uq_equipment_nfc_tag_id', 'equipment', type_='unique')
    op.drop_column('equipment', 'qr_code_image')
    op.drop_column('equipment', 'qr_code_id')
    op.drop_column('equipment', 'nfc_tag_id')
    
    op.drop_index('ix_users_qr_code_id', table_name='users')
    op.drop_index('ix_users_nfc_tag_id', table_name='users')
    op.drop_constraint('uq_users_qr_code_id', 'users', type_='unique')
    op.drop_constraint('uq_users_nfc_tag_id', 'users', type_='unique')
    op.drop_column('users', 'qr_code_id')
    op.drop_column('users', 'nfc_tag_id')
