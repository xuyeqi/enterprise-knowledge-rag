# Database Migrations

这个目录保存 Alembic 数据库迁移代码。

- `env.py`：连接数据库，并把 SQLAlchemy 模型 metadata 提供给 Alembic。
- `script.py.mako`：以后生成新迁移文件时使用的模板。
- `versions/`：按顺序保存每一次数据库结构变化。

迁移会真实修改数据库 schema。执行前需要确认目标数据库和 `.env` 配置，
不要在不知道影响范围时运行升级或回滚命令。
