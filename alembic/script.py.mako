"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

迁移脚本说明：
    upgrade()   ：正向变更（创建表、加字段、建索引等）
    downgrade() ：upgrade() 的逆操作，必须保证可安全回滚

生成与执行请使用 CLI，它会自动带上前端配置里的数据库连接：
    python think.py db-migrate --auto -m "变更说明"
    python think.py db-migrate --upgrade
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
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
