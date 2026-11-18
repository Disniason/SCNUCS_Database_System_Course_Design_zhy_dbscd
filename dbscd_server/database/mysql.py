
import asyncio
import aiomysql
from typing import Optional, Tuple, List, Any

from database.sql_db import sql_db


class mysql_database:
    # ========= 在这里统一配置你的MySQL连接信息 =========
    DB_HOST = "127.0.0.1"
    DB_PORT = 3306
    DB_USER = "xxx"
    DB_PASSWORD = "xxxpw"
    DB_NAME = "dbscd_db"
    DB_CHARSET = "utf8mb4"
    RETRY_TIMES = 5
    RETRY_DELAY = 0.2

    @classmethod
    async def init_db(cls, main_dir: str = "."):
        """
        自动建库 + 建表，变量预先置None，关闭前判断
        """
        admin_conn: Optional[aiomysql.Connection] = None
        work_conn: Optional[aiomysql.Connection] = None
        try:
            # 先连 MySQL 服务（不指定库），查询是否存在目标数据库
            admin_conn = await aiomysql.connect(
                host=cls.DB_HOST,
                port=cls.DB_PORT,
                user=cls.DB_USER,
                password=cls.DB_PASSWORD,
                charset=cls.DB_CHARSET,
                autocommit=True
            )
            cur = await admin_conn.cursor()
            await cur.execute(
                sql_db.database_exists(),
                (cls.DB_NAME,)
            )
            exists = await cur.fetchone()
            await cur.close()

            if exists:
                print(f"数据库 {cls.DB_NAME} 已存在，跳过创建库")
            else:
                print(f"数据库 {cls.DB_NAME} 不存在，准备创建")
                cur = await admin_conn.cursor()
                create_db_sql = sql_db.create_database(cls.DB_NAME, cls.DB_CHARSET)
                await cur.execute(create_db_sql)
                await cur.close()
                print(f"数据库 {cls.DB_NAME} 创建成功")

            # 重试逻辑：连接目标业务库
            for attempt in range(cls.RETRY_TIMES):
                try:
                    work_conn = await aiomysql.connect(
                        host=cls.DB_HOST,
                        port=cls.DB_PORT,
                        user=cls.DB_USER,
                        password=cls.DB_PASSWORD,
                        db=cls.DB_NAME,
                        charset=cls.DB_CHARSET,
                        autocommit=False
                    )
                    break
                except aiomysql.OperationalError as ex:
                    if ex.args[0] == 1049 and attempt < cls.RETRY_TIMES - 1:
                        print(f"数据库尚未同步，等待 {cls.RETRY_DELAY}s 重试 ({attempt+1}/{cls.RETRY_TIMES})")
                        await asyncio.sleep(cls.RETRY_DELAY)
                    else:
                        raise ex

            # 执行建表语句（表定义内部自带 IF NOT EXISTS）
            cur = await work_conn.cursor()
            await cur.execute(sql_db.create_user_table())
            await cur.execute(sql_db.create_video_table())
            await cur.execute(sql_db.create_user_video_like_table())
            await cur.execute(sql_db.create_comment_table())
            await cur.execute(sql_db.create_user_comment_like_table())
            await cur.execute(sql_db.create_follow_table())
            await cur.execute(sql_db.create_blacklist_table())
            await cur.execute(sql_db.create_message_table())
            await cur.execute(sql_db.create_feedback_table())
            await work_conn.commit()
            await cur.close()
            print("数据表初始化完成")

        finally:
            # 每一个连接关闭前判断是否不为None
            if admin_conn is not None:
                try:
                    await admin_conn.close()
                except Exception:
                    pass
            if work_conn is not None:
                try:
                    await work_conn.close()
                except Exception:
                    pass

    @classmethod
    async def get_connection(cls) -> aiomysql.Connection:
        """获取业务数据库的异步连接"""
        conn: Optional[aiomysql.Connection] = None
        try:
            conn = await aiomysql.connect(
                host=cls.DB_HOST,
                port=cls.DB_PORT,
                user=cls.DB_USER,
                password=cls.DB_PASSWORD,
                db=cls.DB_NAME,
                charset=cls.DB_CHARSET,
                autocommit=False
            )
            return conn
        finally:
            if conn is not None:
                try:
                    await conn.close()
                except Exception:
                    pass

    @classmethod
    async def get_conn(cls) -> aiomysql.Connection:
        """获取一条独立连接，交给上层手动管理事务，不自动提交、不自动关闭"""
        conn = await aiomysql.connect(
            host=cls.DB_HOST,
            port=cls.DB_PORT,
            user=cls.DB_USER,
            password=cls.DB_PASSWORD,
            db=cls.DB_NAME,
            charset=cls.DB_CHARSET,
            autocommit=False
        )
        return conn

    @classmethod
    async def execute_sql(cls, sql: str, params: Optional[Tuple[Any, ...]] = None) -> Any:
        """
        params 仅用于字段值，库名、表名禁止走参数绑定
        SELECT 返回结果列表；DML 返回影响行数
        """
        conn: Optional[aiomysql.Connection] = None
        try:
            conn = await aiomysql.connect(
                host=cls.DB_HOST,
                port=cls.DB_PORT,
                user=cls.DB_USER,
                password=cls.DB_PASSWORD,
                db=cls.DB_NAME,
                charset=cls.DB_CHARSET,
                autocommit=False
            )
            cur = await conn.cursor(aiomysql.DictCursor)
            if params is not None:
                await cur.execute(sql, params)
            else:
                await cur.execute(sql)
            sql_stripped = sql.strip().upper()
            if sql_stripped.startswith("SELECT"):
                res = await cur.fetchall()
                await conn.commit()
                return res
            else:
                await conn.commit()
                return cur.rowcount
        except Exception as e:
            if conn is not None:
                try:
                    await conn.rollback()
                except Exception:
                    pass
            raise e
        finally:
            if conn is not None:
                try:
                    await conn.close()
                except Exception:
                    pass
