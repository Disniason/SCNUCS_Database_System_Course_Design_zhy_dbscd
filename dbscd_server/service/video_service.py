import os
import asyncio
import aiomysql
from datetime import datetime

from database.sql_video import sql_video
from database.mysql import mysql_database
from service.message_service import message_service


class video_service:

    VIDEO_SAVE_BASE = "/home/xxx/DBSCD/database/video"
    VIDEO_URL_PREFIX = "/static/video"
    COVER_SAVE_DIR = "./static/cover"
    COVER_URL_PREFIX = "/static/cover"
    
    @staticmethod
    async def get_user_comment_list(user_id: int):
        count_sql = sql_video.count_comment_by_userId()
        count_row = await mysql_database.execute_sql(count_sql, (user_id,))
        total = count_row[0]["cnt"] if count_row else 0

        list_sql = sql_video.list_comment_by_userId()
        data_list = await mysql_database.execute_sql(list_sql, (user_id,))
        return {
            "total": total,
            "list": data_list
        }

    @classmethod
    async def search_video(cls, keyword: str, login_uid: int):
        """
        搜索视频，模糊标题，过滤双向拉黑作者，关注优先排序
        :param keyword: 标题关键词
        :param login_uid: 当前登录用户
        """
        sql = sql_video.search_video_sql()
        # 参数顺序：keyword, login_uid拉黑A, login_uid拉黑B反向, login_uid关注排序
        rows = await mysql_database.execute_sql(sql, (keyword, login_uid, login_uid, login_uid))
        res = []
        for r in rows:
            res.append({
                "videoId": r["videoId"],
                "videoTitle": r["videoTitle"],
                "videoUrl": await cls.video_url_static_map(r["videoUrl"]),
                "likeCount": r["likeCount"],
                "createTime": r["createTime"].strftime("%Y-%m-%d %H:%M:%S"),
                "authorId": r["authorId"],
                "authorNick": r["authorNick"]
            })
        return res

    @classmethod
    async def video_url_static_map(cls, video_url: str):
        """
        将本地绝对视频路径 /home/zhy/DBSCD/database/video/xxx.mp4
        映射为静态访问路径 /static/video/xxx.mp4
        :param video_url: 数据库存的本地绝对路径
        :return: 静态url路径字符串
        """
        local_base = cls.VIDEO_SAVE_BASE
        prefix = cls.VIDEO_URL_PREFIX
        if video_url.startswith(local_base):
            rel_path = video_url[len(local_base):]
            # 防止出现重复斜杠，比如 /static/video//xxx.mp4
            rel_path = rel_path.lstrip("/")
            return f"{prefix}/{rel_path}"
        # 不在视频根目录下，原样返回或者返回None，看你的需求
        return video_url

    @classmethod
    async def get_next_video_id(cls) -> int:
        """获取下一个videoId：行数+1"""
        sql = sql_video.count_video_total_sql()
        row = await mysql_database.execute_sql(sql)
        total = row[0]["cnt"]
        return total + 1

    @classmethod
    async def create_video_record(cls, video_url: str, title: str, author_uid: int):
        """写入数据库视频记录"""
        sql = sql_video.insert_video_sql()
        await mysql_database.execute_sql(sql, (video_url, title, author_uid))
        return True

    @classmethod
    def ensure_video_dir(cls):
        """确保视频保存目录存在"""
        if not os.path.exists(cls.VIDEO_SAVE_BASE):
            os.makedirs(cls.VIDEO_SAVE_BASE, exist_ok=True)

    @classmethod
    async def get_video_preview(cls, video_id: int):
        """
        【独立公共函数】给前端 /api/video/preview 使用
        返回：videoId, coverUrl, videoTitle, authorId, authorNick, likeCount, createTime
        videoUrl 为服务端本地绝对路径；自动判断封面是否存在，不存在则异步ffmpeg截取视频第一帧生成封面
        """
        os.makedirs(cls.COVER_SAVE_DIR, exist_ok=True)
        sql = sql_video.get_video_preview_by_id()
        rows = await mysql_database.execute_sql(sql, (video_id,))
        if not rows:
            return None
        row = rows[0]

        videoId = row["videoId"]
        video_local_abs_path = row["videoUrl"]  # 本地绝对路径
        videoTitle = row["videoTitle"]
        authorId = row["videoAuthor"]
        authorNick = row["userNick"]
        likeCount = row["likeCount"]
        createTime = row["createTime"]

        cover_filename = f"cover_{videoId}.jpg"
        cover_path = os.path.join(cls.COVER_SAVE_DIR, cover_filename)
        cover_url = f"{cls.COVER_URL_PREFIX}/{cover_filename}"

        # 封面已经存在，直接返回，不需要截取
        if os.path.exists(cover_path):
            return {
                "videoId": videoId,
                "coverUrl": cover_url,
                "videoTitle": videoTitle,
                "authorId": authorId,
                "authorNick": authorNick,
                "likeCount": likeCount,
                "createTime": createTime.strftime("%Y-%m-%d %H:%M")
            }

        # 封面不存在，开始截取首帧
        # 先校验源视频本地文件是否存在
        if not os.path.isfile(video_local_abs_path):
            print(f"源视频文件不存在: {video_local_abs_path}")
            cover_url = ""
            return {
                "videoId": videoId,
                "coverUrl": cover_url,
                "videoTitle": videoTitle,
                "authorId": authorId,
                "authorNick": authorNick,
                "likeCount": likeCount,
                "createTime": createTime.strftime("%Y-%m-%d %H:%M")
            }

        try:
            # 异步调用 ffmpeg，不阻塞 FastAPI 事件循环
            cmd = [
                "ffmpeg",
                "-ss", "00:00:00.001",
                "-i", video_local_abs_path,
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                cover_path
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                print(f"ffmpeg 截取失败，stderr: {stderr.decode('utf-8', errors='ignore')}")
                cover_url = ""
        except Exception as e:
            print("截取封面异常：", e)
            cover_url = ""

        return {
            "videoId": videoId,
            "coverUrl": cover_url,
            "videoTitle": videoTitle,
            "authorId": authorId,
            "authorNick": authorNick,
            "likeCount": likeCount,
            "createTime": createTime.strftime("%Y-%m-%d %H:%M")
        }

    @classmethod
    async def get_video_detail(cls, video_id: int):
        """获取视频详情（标题、url、作者id、昵称、点赞数、发布时间）"""
        sql = sql_video.get_video_detail_by_vid()
        row = await mysql_database.execute_sql(sql, (video_id,))
        if not row:
            return None
        row = row[0]
        if isinstance(row["createTime"], datetime):
            row["createTime"] = row["createTime"].strftime("%Y-%m-%d %H:%M")
        row["videoUrl"] = await cls.video_url_static_map(row["videoUrl"])
        return row

    @staticmethod
    async def is_user_liked_video(user_id: int, video_id: int) -> bool:
        """判断用户是否点赞"""
        sql = sql_video.check_user_like_video()
        res = await mysql_database.execute_sql(sql, (user_id, video_id))
        return len(res) > 0

    @staticmethod
    async def like_video(user_id: int, video_id: int):
        conn = None
        try:
            try:
                conn = await mysql_database.get_conn()
            except Exception as e:
                # print("【获取数据库连接失败】", repr(e))
                raise e

            cur = await conn.cursor(aiomysql.DictCursor)
            await cur.execute(sql_video.add_video_like(), (user_id, video_id))
            await cur.execute(sql_video.inc_video_like_count(), (video_id,))
            await conn.commit()
            await message_service.insert_video_like_message(user_id, video_id)
            return True
        except Exception as e:
            # print("【点赞业务异常】", repr(e))
            raise e
        finally:
            if conn is not None:
                try:
                    # aiomysql close 是同步方法！不要加 await
                    conn.close()
                except Exception as close_err:
                    # print("【关闭连接异常】", repr(close_err))
                    pass

    @staticmethod
    async def cancel_like_video(user_id: int, video_id: int):
        conn = None
        try:
            try:
                conn = await mysql_database.get_conn()
            except Exception as e:
                # print("【获取数据库连接失败】", repr(e))
                raise e

            cur = await conn.cursor(aiomysql.DictCursor)
            await cur.execute(sql_video.remove_video_like(), (user_id, video_id))
            await cur.execute(sql_video.dec_video_like_count(), (video_id,))
            await conn.commit()
            return True
        except Exception as e:
            # print("【取消点赞业务异常】", repr(e))
            raise e
        finally:
            if conn is not None:
                try:
                    # 重点：删掉 await！
                    conn.close()
                except Exception as close_err:
                    # print("【关闭连接异常】", repr(close_err))
                    pass

    @classmethod
    async def _get_black_user_ids(cls, uid: int) -> set:
        """获取和uid双向拉黑的用户id集合"""
        rows = await mysql_database.execute_sql(sql_video.get_blacklist_ids(), (uid, uid))
        return {r["blockedId"] for r in rows}

    @classmethod
    async def list_first_level_comment(cls, video_id: int, login_uid: int):
        """获取一级评论，过滤拉黑用户，附带isLiked"""
        black_ids = await cls._get_black_user_ids(login_uid)
        raw_comments = await mysql_database.execute_sql(sql_video.list_first_level_comment_by_video(), (video_id,))
        res = []
        for c in raw_comments:
            if c["userId"] in black_ids:
                continue
            like_res = await mysql_database.execute_sql(sql_video.check_comment_like(), (login_uid, c["commentId"]))
            is_liked = like_res is not None and len(like_res) > 0
            res.append({
                "commentId": c["commentId"],
                "videoId": c["videoId"],
                "userId": c["userId"],
                "parentId": c["parentId"],
                "content": c["content"],
                "likeCount": c["likeCount"],
                "userNick": c["userNick"],
                "createTime": c["createTime"].strftime("%Y-%m-%d %H:%M:%S"),
                "isLiked": is_liked
            })
        return res

    @classmethod
    async def _get_black_user_ids(cls, uid: int) -> set:
        """获取双向拉黑用户ID集合"""
        rows = await mysql_database.execute_sql(sql_video.get_blacklist_ids(), (uid, uid))
        return {r["blockedId"] for r in rows}

    @classmethod
    async def _recursive_fetch_all_descendant_comments(
        cls,
        parent_cid: int,
        login_uid: int,
        black_ids: set,
        out_list: list,
        current_real_level: int
    ):
        """
        Python递归抓取所有后代评论
        parent_cid: 当前父评论id
        current_real_level: 当前这一批子评论的【真实层级】
            - 当 parent是一级评论 → 这批子评论真实层级 = 2
            - 当 parent是2级评论 → 这批子评论真实层级 = 3
        规则：
            real_level == 2 → content原样，show_content=原生内容
            real_level >=3 → show_content = f"回复用户{parentUserNick}：{content}"
        """
        # 查当前parent的直接子节点
        child_rows = await mysql_database.execute_sql(sql_video.get_direct_child_comments(), (parent_cid,))

        for row in child_rows:
            # 拉黑过滤：发布者在黑名单直接跳过，不继续递归它的子评论
            if row["userId"] in black_ids:
                continue

            # 查询点赞状态
            like_res = await mysql_database.execute_sql(sql_video.check_comment_like(), (login_uid, row["commentId"]))
            is_liked = like_res is not None and len(like_res) > 0

            origin_content = row["content"]
            if current_real_level == 2:
                # 真实2级：不拼接前缀
                show_content = origin_content
            else:
                # >=3级：拼接回复前缀
                show_content = f"回复用户{row['parentUserNick']}：{origin_content}"

            comment_item = {
                "commentId": row["commentId"],
                "videoId": row["videoId"],
                "userId": row["userId"],
                "parentId": row["parentId"],
                "content": show_content,
                "originContent": origin_content,
                "likeCount": row["likeCount"],
                "userNick": row["userNick"],
                "parentUserNick": row["parentUserNick"],
                "createTime": row["createTime"].strftime("%Y-%m-%d %H:%M:%S"),
                "isLiked": is_liked,
                "realLevel": current_real_level  # 传给前端，可选，前端不用渲染层级，仅调试
            }
            out_list.append(comment_item)

            # 递归：继续抓这条评论自己的子评论，层级+1
            await cls._recursive_fetch_all_descendant_comments(
                parent_cid=row["commentId"],
                login_uid=login_uid,
                black_ids=black_ids,
                out_list=out_list,
                current_real_level=current_real_level + 1
            )

    @classmethod
    async def list_first_level_comment(cls, video_id: int, login_uid: int):
        """一级评论逻辑不变"""
        black_ids = await cls._get_black_user_ids(login_uid)
        raw_comments = await mysql_database.execute_sql(sql_video.list_first_level_comment_by_video(), (video_id,))
        res = []
        for c in raw_comments:
            if c["userId"] in black_ids:
                continue
            like_res = await mysql_database.execute_sql(sql_video.check_comment_like(), (login_uid, c["commentId"]))
            is_liked = like_res is not None and len(like_res) > 0
            res.append({
                "commentId": c["commentId"],
                "videoId": c["videoId"],
                "userId": c["userId"],
                "parentId": c["parentId"],
                "content": c["content"],
                "likeCount": c["likeCount"],
                "userNick": c["userNick"],
                "createTime": c["createTime"].strftime("%Y-%m-%d %H:%M:%S"),
                "isLiked": is_liked
            })
        return res

    @classmethod
    async def list_all_flat_descendant_comments(cls, parent_first_comment_id: int, login_uid: int):
        """
        对外接口：传入【一级评论commentId】
        递归抓取它下面全部后代（2,3,4,5...级），扁平化合并成一维数组返回给前端
        """
        black_ids = await cls._get_black_user_ids(login_uid)
        flat_list = []
        # 一级评论的直接子节点，真实层级 = 2
        await cls._recursive_fetch_all_descendant_comments(
            parent_cid=parent_first_comment_id,
            login_uid=login_uid,
            black_ids=black_ids,
            out_list=flat_list,
            current_real_level=2
        )
        return flat_list

    @classmethod
    async def like_comment(cls, user_id: int, comment_id: int):
        conn = None
        try:
            try:
                conn = await mysql_database.get_conn()
            except Exception as e:
                raise e

            cur = await conn.cursor(aiomysql.DictCursor)
            # 新增点赞记录
            await cur.execute(sql_video.add_comment_like(), (user_id, comment_id))
            # 评论likeCount +1
            await cur.execute(sql_video.inc_comment_like_count(), (comment_id,))
            await conn.commit()
            # 推送评论点赞消息
            await message_service.insert_comment_like_message(user_id, comment_id)
            return True
        except Exception as e:
            raise e
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception as close_err:
                    pass

    @classmethod
    async def cancel_like_comment(cls, user_id: int, comment_id: int):
        conn = None
        try:
            try:
                conn = await mysql_database.get_conn()
            except Exception as e:
                raise e

            cur = await conn.cursor(aiomysql.DictCursor)
            # 删除点赞记录
            await cur.execute(sql_video.remove_comment_like(), (user_id, comment_id))
            # 评论likeCount -1
            await cur.execute(sql_video.dec_comment_like_count(), (comment_id,))
            await conn.commit()
            return False
        except Exception as e:
            raise e
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception as close_err:
                    pass

    @classmethod
    async def toggle_comment_like(cls, login_uid: int, comment_id: int):
        check = await mysql_database.execute_sql(sql_video.check_comment_like(), (login_uid, comment_id))
        if check and len(check) > 0:
            # 已经点赞 → 取消点赞
            return await cls.cancel_like_comment(login_uid, comment_id)
        else:
            # 未点赞 → 新增点赞
            return await cls.like_comment(login_uid, comment_id)

    @classmethod
    async def publish_comment(cls, video_id: int, login_uid: int, parent_id: int | None, content: str):
        # 插入评论记录
        await mysql_database.execute_sql(sql_video.insert_comment(), (video_id, login_uid, parent_id, content))

        if parent_id is None:
            # 一级评论：通知视频作者
            await message_service.insert_video_comment_message(login_uid, video_id, content)
        else:
            await message_service.insert_video_comment_message(login_uid, video_id, content)
            # 回复评论：通知父评论作者，传入父评论ID和本次回复内容
            await message_service.insert_comment_reply_message(login_uid, parent_id, content)

        return True

    @classmethod
    async def delete_my_comment(cls, login_uid: int, comment_id: int) -> bool:
        """
        删除评论：必须是评论作者本人才能删
        返回 True=成功删除；False=不存在或者不是本人无权删除
        """
        affected = await mysql_database.execute_sql(sql_video.delete_comment_by_id(), (comment_id, login_uid))
        return True

    @classmethod
    async def delete_video(cls, login_uid: int, video_id: int):
        """
        删除视频，依靠外键 ON DELETE CASCADE 自动清理评论、点赞等关联数据
        校验：只能作者本人删除
        """
        await mysql_database.execute_sql(sql_video.delete_video_by_id(), (video_id, login_uid))
        return True, "删除成功"

