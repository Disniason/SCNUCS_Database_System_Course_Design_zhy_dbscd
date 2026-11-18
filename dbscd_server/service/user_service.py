import jwt
import bcrypt
import random
import asyncio
import secrets
import smtplib
from redis.asyncio import Redis
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

from database.sql_user import sql_user
from database.mysql import mysql_database
from service.message_service import message_service


class user_service:
    # Redis 配置（整合自 redis_database）
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = ""
    pool: Redis | None = None

    # 邮箱 SMTP
    EMAIL_HOST = "smtp.qq.com"
    EMAIL_PORT = 465
    EMAIL_USER = "xxxxxxxxxx@qq.com"
    EMAIL_PWD = "xxxxxxxxxxxxxxxx"
    # 验证码配置
    CODE_EXPIRE_SEC = 600    # 验证码有效期 10min
    RATE_LIMIT_SEC = 60      # 发送限流 60s

    JWT_SECRET_KEY = secrets.token_hex(32)
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 120
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    @classmethod
    async def init_redis(cls):
        """服务启动时调用一次初始化redis连接"""
        try:
            cls.pool = Redis(
                host=cls.REDIS_HOST,
                port=cls.REDIS_PORT,
                db=cls.REDIS_DB,
                password=cls.REDIS_PASSWORD if cls.REDIS_PASSWORD else None,
                decode_responses=True
            )
            # 测试连通性
            await cls.pool.ping()
            print("Redis 初始化成功")
            return True
        except Exception as e:
            print(f"Redis初始化失败: {e}")
            cls.pool = None
            return False

    @classmethod
    async def close_redis(cls):
        """关闭redis连接，lifespan结束时调用"""
        if cls.pool is not None:
            await cls.pool.aclose()
            cls.pool = None
            print("Redis连接已关闭")

    @classmethod
    async def set_code(cls, email: str, code: str, expire_second: int = 300):
        """保存验证码"""
        if cls.pool is None:
            raise RuntimeError("Redis未初始化")
        await cls.pool.setex(f"verify:{email}", expire_second, code)

    @classmethod
    async def get_code(cls, email: str):
        """读取验证码"""
        if cls.pool is None:
            raise RuntimeError("Redis未初始化")
        return await cls.pool.get(f"verify:{email}")

    @classmethod
    async def send_register_code(cls, email: str):
        """
        发送注册验证码
        1. 限流判断
        2. 判断邮箱是否已注册
        3. 生成6位验证码存入redis
        4. 异步发邮件
        """
        if cls.pool is None:
            return {"code": 0, "msg": "Redis未初始化"}

        rate_key = f"user_reg_rate:{email}"
        if await cls.pool.exists(rate_key):
            return {"code": 0, "msg": "1分钟内只能发送一次验证码"}

        # 校验邮箱是否注册
        res = await mysql_database.execute_sql(sql_user.check_email_exists(), (email,))
        if res:
            return {"code": 0, "msg": "该邮箱已经注册"}

        code = f"{random.randint(100000, 999999)}"
        code_key = f"user_reg_code:{email}"
        await cls.pool.setex(code_key, cls.CODE_EXPIRE_SEC, code)
        await cls.pool.setex(rate_key, cls.RATE_LIMIT_SEC, "1")

        asyncio.create_task(cls._send_email_task(email, code))
        return {"code": 1, "msg": "验证码已发送，请查收邮箱"}

    @classmethod
    async def verify_register_code(cls, email: str, code: str):
        """校验验证码，通过后删除验证码"""
        if cls.pool is None:
            return {"code": 0, "msg": "Redis未初始化"}

        code_key = f"user_reg_code:{email}"
        stored = await cls.pool.get(code_key)
        if not stored:
            return {"code": 0, "msg": "验证码不存在或已过期"}
        if stored != code.strip():
            return {"code": 0, "msg": "验证码错误"}

        await cls.pool.delete(code_key)
        return {"code": 1, "msg": "验证成功，请设置密码"}

    @classmethod
    async def finish_register(cls, email: str, password: str):
        """完成注册，bcrypt加密密码，自动生成昵称"""
        # 二次校验邮箱，防止并发
        res = await mysql_database.execute_sql(sql_user.check_email_exists(), (email,))
        if res:
            return {"code": 0, "msg": "邮箱已被注册"}

        # bcrypt加密
        salt = bcrypt.gensalt()
        hash_pw = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        nick = f"用户{email.split('@')[0]}"

        try:
            await mysql_database.execute_sql(sql_user.insert_user(), (email, hash_pw, nick))
            return {"code": 1, "msg": "注册成功，即将跳转登录页"}
        except Exception as e:
            print("注册异常：", e)
            return {"code": 0, "msg": "注册失败，请稍后重试"}

    @classmethod
    async def _send_email_task(cls, to_email: str, code: str):
        """异步邮件任务，线程池跑同步smtp"""
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, cls._smtp_send, to_email, code)
        except Exception as e:
            print("邮件发送失败：", e)

    @classmethod
    def _smtp_send(cls, to_email: str, code: str):
        msg = MIMEText(f"您的注册验证码：{code}\n有效期10分钟，请勿泄露。", "plain", "utf-8")
        msg["From"] = cls.EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = "zhy_dbscd简易短视频平台验证码"
        with smtplib.SMTP_SSL(cls.EMAIL_HOST, cls.EMAIL_PORT) as smtp:
            smtp.login(cls.EMAIL_USER, cls.EMAIL_PWD)
            smtp.sendmail(cls.EMAIL_USER, [to_email], msg.as_string())

    @classmethod
    def create_access_token(cls, data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, cls.JWT_SECRET_KEY, algorithm=cls.JWT_ALGORITHM)
        return encoded_jwt

    @classmethod
    async def create_refresh_token(cls, data: dict):
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, cls.JWT_SECRET_KEY, algorithm=cls.JWT_ALGORITHM)
        # refresh token存入redis用于注销校验
        await cls.pool.setex(
            f"refresh_token:{data['sub']}",
            cls.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            encoded_jwt
        )
        return encoded_jwt

    @classmethod
    async def verify_token(cls, token: str, token_type: str = "access"):
        try:
            payload = jwt.decode(
                token,
                cls.JWT_SECRET_KEY,
                algorithms=[cls.JWT_ALGORITHM],
                options={"verify_exp": True}
            )
            if payload.get("type") != token_type:
                return {"code": 0, "msg": "令牌类型错误"}
            user_id = payload.get("sub")
            if not user_id:
                return {"code": 0, "msg": "令牌无效"}
            if token_type == "refresh":
                stored_token = await cls.pool.get(f"refresh_token:{user_id}")
                if not stored_token or stored_token != token:
                    return {"code": 0, "msg": "令牌已注销"}
            return {"code": 1, "msg": "令牌有效", "data": payload}
        except jwt.ExpiredSignatureError:
            return {"code": 0, "msg": "令牌已过期"}
        except Exception as e:
            print("JWT解码异常：", repr(e))
            return {"code": 0, "msg": "令牌无效"}

    @classmethod
    async def send_login_code(cls, account: str):
        """发送登录验证码：account支持邮箱 / userId"""
        # account如果是纯数字，当作userId查询
        is_num_id = account.isdigit()
        res = await mysql_database.execute_sql(sql_user.sql_query_email_by_account(), (account, account if is_num_id else -1))
        if not res:
            return {"code": 0, "msg": "账号不存在"}
        email = res[0]["userEmail"]

        rate_key = f"user_login_rate:{email}"
        if await cls.pool.exists(rate_key):
            return {"code": 0, "msg": "1分钟内只能发送一次验证码"}

        code = f"{random.randint(100000, 999999)}"
        code_key = f"user_login_code:{email}"
        await cls.pool.setex(code_key, cls.CODE_EXPIRE_SEC, code)
        await cls.pool.setex(rate_key, cls.RATE_LIMIT_SEC, "1")

        asyncio.create_task(cls._send_email_task(email, code))
        return {"code": 1, "msg": "验证码已发送，请查收邮箱"}

    @classmethod
    async def login(cls, account: str, loginType: str, password=None, code=None):
        """
        登录主逻辑
        loginType: password / code
        account: 邮箱 或者 userId字符串
        """
        is_num_id = account.isdigit()
        rows = await mysql_database.execute_sql(sql_user.sql_user_login(), (account, account if is_num_id else -1))
        if not rows:
            return {"code": 0, "msg": "账号不存在"}
        row = rows[0]
        userId = row["userId"]
        userEmail = row["userEmail"]
        hash_pw = row["userPassword"]

        if loginType == "password":
            if not bcrypt.checkpw(password.encode("utf-8"), hash_pw.encode("utf-8")):
                return {"code": 0, "msg": "密码错误"}
        else:
            # 验证码登录
            code_key = f"user_login_code:{userEmail}"
            stored = await cls.pool.get(code_key)
            if not stored or stored != code.strip():
                return {"code": 0, "msg": "验证码错误或已过期"}
            await cls.pool.delete(code_key)

        # 生成令牌
        access_exp = timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = cls.create_access_token(data={"sub": str(userId), "email": userEmail}, expires_delta=access_exp)
        refresh_token = await cls.create_refresh_token(data={"sub": str(userId)})

        return {
            "code": 1,
            "msg": "登录成功",
            "data": {
                "userId": userId,
                "email": userEmail,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }
        }

    @classmethod
    async def logout(cls, user_id: str):
        await cls.pool.delete(f"refresh_token:{user_id}")
        return {"code": 1, "msg": "退出登录成功"}

    @staticmethod
    async def get_user_profile(user_id: int):
        sql = sql_user.get_user_profile_by_id()
        rows = await mysql_database.execute_sql(sql, (user_id,))
        if not rows:
            return None
        return rows[0]

    @staticmethod
    async def get_my_follow_list(user_id: int):
        # 总数
        count_sql = sql_user.count_follow_by_userId()
        count_row = await mysql_database.execute_sql(count_sql, (user_id,))
        total = count_row[0]["cnt"] if count_row else 0

        list_sql = sql_user.list_follow_by_userId()
        data_list = await mysql_database.execute_sql(list_sql, (user_id,))
        return {
            "total": total,
            "list": data_list
        }

    @staticmethod
    async def get_my_fan_list(user_id: int):
        count_sql = sql_user.count_fan_by_followedId()
        count_row = await mysql_database.execute_sql(count_sql, (user_id,))
        total = count_row[0]["cnt"] if count_row else 0

        list_sql = sql_user.list_fan_by_followedId()
        data_list = await mysql_database.execute_sql(list_sql, (user_id,))
        return {
            "total": total,
            "list": data_list
        }

    @classmethod
    async def search_user(cls, keyword: str, login_uid: int):
        """
        搜索用户
        :param keyword: 搜索词（数字则匹配userId，同时模糊匹配昵称）
        :param login_uid: 当前登录用户ID，用于拉黑过滤 + 关注优先排序
        """
        sql = sql_user.search_user_sql()
        if keyword.isdigit():
            uid_param = int(keyword)
        else:
            uid_param = keyword
        # 参数顺序：%s(userId精确), %s(昵称模糊), %s(login_uid拉黑A), %s(login_uid拉黑B反向), %s(关注排序)
        rows = await mysql_database.execute_sql(sql, (uid_param, keyword, login_uid, login_uid, login_uid))
        res = []
        for r in rows:
            res.append({
                "userId": r["userId"],
                "userNick": r["userNick"],
                "createTime": r["createTime"].strftime("%Y-%m-%d %H:%M:%S")
            })
        return res

    @classmethod
    async def get_other_user_base_info(cls, target_user_id: int):
        """获取对方昵称ID"""
        sql = sql_user.get_other_user_info_sql()
        row = await mysql_database.execute_sql(sql, (target_user_id,))
        if not row:
            return None
        return {
            "userId": row[0]["userId"],
            "userNick": row[0]["userNick"]
        }

    @classmethod
    async def check_is_follow(cls, login_uid: int, target_uid: int) -> bool:
        sql = sql_user.check_follow_sql()
        res = await mysql_database.execute_sql(sql, (login_uid, target_uid))
        return len(res) > 0

    @classmethod
    async def check_is_block(cls, login_uid: int, target_uid: int) -> bool:
        sql = sql_user.check_block_sql()
        res = await mysql_database.execute_sql(sql, (login_uid, target_uid))
        return len(res) > 0

    @classmethod
    async def follow_user(cls, login_uid: int, target_uid: int):
        # 先删除拉黑记录（关注前自动解除拉黑，需求规定）
        await mysql_database.execute_sql(sql_user.remove_block_sql(), (login_uid, target_uid))
        # await mysql_database.execute_sql(sql_user.remove_block_sql(), (target_uid, login_uid))
        # 添加关注
        await mysql_database.execute_sql(sql_user.add_follow_sql(), (login_uid, target_uid))
        # 添加消息
        await message_service.insert_follow_message(login_uid, target_uid)
        return True

    @classmethod
    async def unfollow_user(cls, login_uid: int, target_uid: int):
        await mysql_database.execute_sql(sql_user.remove_follow_sql(), (login_uid, target_uid))
        return True

    @classmethod
    async def block_user(cls, login_uid: int, target_uid: int):
        # 拉黑前，自动取消关注（需求规定）
        await mysql_database.execute_sql(sql_user.remove_follow_sql(), (login_uid, target_uid))
        # await mysql_database.execute_sql(sql_user.remove_follow_sql(), (target_uid, login_uid))
        await mysql_database.execute_sql(sql_user.add_block_sql(), (login_uid, target_uid))
        return True

    @classmethod
    async def unblock_user(cls, login_uid: int, target_uid: int):
        await mysql_database.execute_sql(sql_user.remove_block_sql(), (login_uid, target_uid))
        return True

    @classmethod
    async def get_my_blacklist(cls, login_uid: int):
        """获取我拉黑的用户列表"""
        sql = sql_user.get_black_list_sql()
        rows = await mysql_database.execute_sql(sql, (login_uid,))
        res = []
        for r in rows:
            res.append({
                "userId": r["userId"],
                "userNick": r["userNick"]
            })
        return res

    @classmethod
    async def update_user(cls, user_id: int, new_nick: str | None, new_pwd: str | None):
        """
        更新用户信息
        new_nick=None 不修改昵称
        new_pwd=None 不修改密码；传入明文会自动bcrypt哈希
        """
        # 查原始数据，SQL从sql_user获取，不手写
        sql_select = sql_user.select_user_nick_pwd_by_id_sql()
        origin = await mysql_database.execute_sql(sql_select, (user_id,))
        if not origin:
            return False

        old_nick = origin[0]["userNick"]
        old_pwd_hash = origin[0]["userPassword"]

        # 昵称逻辑：传了非空值就用新昵称，否则保留旧昵称
        final_nick = new_nick.strip() if (new_nick is not None and new_nick.strip() != "") else old_nick

        # 密码逻辑重点：
        # 前端传null / 空字符串 → 不修改密码，沿用原有bcrypt哈希
        # 前端传非空明文 → bcrypt哈希之后再入库
        if new_pwd is not None and new_pwd.strip() != "":
            pwd_bytes = new_pwd.strip().encode("utf-8")
            salt = bcrypt.gensalt()
            final_pwd_hash = bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")
        else:
            final_pwd_hash = old_pwd_hash

        sql_update = sql_user.update_user_info_sql()
        await mysql_database.execute_sql(sql_update, (final_nick, final_pwd_hash, user_id))
        return True

    @classmethod
    async def delete_my_account(cls, user_id: int):
        """注销账号，外键 ON DELETE CASCADE，关注、黑名单自动清除"""
        await mysql_database.execute_sql(sql_user.delete_user_by_id_sql(), (user_id,))
        return True

    @classmethod
    async def get_user_by_id(cls, user_id: int):
        sql = sql_user.select_user_by_id_sql()
        rows = await mysql_database.execute_sql(sql, (user_id,))
        if not rows:
            return None
        return rows[0]

    @staticmethod
    async def get_user_works_video_id_list(author_user_id: int):
        """
        接口 /api/user/works 调用：只拿到该用户所有作品videoId数组
        """
        sql = sql_user.get_user_work_video_ids()
        rows = await mysql_database.execute_sql(sql, (author_user_id,))
        vid_list = [row["videoId"] for row in rows]
        return vid_list

    @staticmethod
    async def get_user_like_video_id_list(like_user_id: int):
        """
        接口 /api/user/like-video 调用：只拿到该用户点赞视频的videoId数组
        """
        sql = sql_user.get_user_like_video_ids()
        rows = await mysql_database.execute_sql(sql, (like_user_id,))
        vid_list = [row["videoId"] for row in rows]
        return vid_list

    @staticmethod
    async def get_recommend_video_id_list(login_user_id: int):
        """
        /api/recommend/video-list 调用
        返回符合推荐规则的videoId数组，时间倒序
        """
        sql = sql_user.get_recommend_video_ids()
        rows = await mysql_database.execute_sql(sql, (login_user_id, login_user_id, login_user_id))
        vid_list = [row["videoId"] for row in rows]
        return vid_list

    @staticmethod
    async def get_other_user_works_video_id_list(target_user_id: int):
        """
        /api/account/works 使用：查询指定userId的所有作品videoId
        """
        sql = sql_user.get_other_user_work_video_ids()
        rows = await mysql_database.execute_sql(sql, (target_user_id,))
        vid_list = [row["videoId"] for row in rows]
        return vid_list
    
    @staticmethod
    async def get_followed_video_id_list(login_user_id: int):
        """
        /api/followed/video-list 关注流接口调用
        返回关注作者视频ID数组，未点赞靠前、时间倒序
        """
        sql = sql_user.get_followed_video_ids()
        rows = await mysql_database.execute_sql(sql, (login_user_id, login_user_id, login_user_id, login_user_id))
        vid_list = [row["videoId"] for row in rows]
        return vid_list
    
    @classmethod
    async def publish_feedback(cls, login_uid: int, content: str):
        # 字符校验：上限256字符（最大 256*4=1024字节，匹配varchar(1024) utf8mb4）
        if len(content) > 256:
            return False, "反馈内容最多256个字"
        if not content.strip():
            return False, "反馈内容不能为空"
        await mysql_database.execute_sql(sql_user.insert_feedback(), (login_uid, content))
        return True, "提交成功"

    @classmethod
    async def get_user_feedback_list(cls, login_uid: int):
        rows = await mysql_database.execute_sql(sql_user.list_feedback_by_user(), (login_uid,))
        res = []
        for r in rows:
            res.append({
                "feedbackId": r["feedbackId"],
                "content": r["content"],
                "createTime": r["createTime"].strftime("%Y-%m-%d %H:%M:%S")
            })
        return res




