"""定义所有 SQLAlchemy 数据模型共同继承的基础类。

这个文件只提供 `Base`。后续每个数据库模型都继承它，SQLAlchemy 就会把
这些模型登记到同一份 metadata（数据库结构清单）中。Alembic 会读取这份
清单，对比 Python 模型和真实数据库结构之间的差异。
"""

# DeclarativeBase 是 SQLAlchemy 2.x 提供的声明式模型基类。
# “声明式”表示可以通过编写 Python 类来描述数据库表。
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """项目内所有 SQLAlchemy 数据模型的共同父类。

    这个类目前不添加额外字段，只负责让所有子类共享同一个 metadata。
    `pass` 表示类体暂时不需要其它代码，但这个类本身仍然有效。
    """

    pass
