"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """升级数据库结构（正向迁移）
    
    在此处编写数据库结构变更逻辑，例如：
    - 创建新表
    - 添加/删除/修改字段
    - 创建索引
    - 添加约束
    
    示例:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('username', sa.String(50), nullable=False),
            sa.Column('email', sa.String(100)),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )
    """
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """降级数据库结构（回滚迁移）
    
    在此处编写撤销升级操作的逻辑，确保可以安全回滚。
     downgrade() 应该是 upgrade() 的逆操作。
    
    示例:
        op.drop_table('users')
    """
    ${downgrades if downgrades else "pass"}
