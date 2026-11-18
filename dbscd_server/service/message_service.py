
from database.mysql import mysql_database
from database.sql_message import sql_message

class message_service:

    @classmethod
    async def insert_follow_message(cls, follow_uid: int, followed_uid: int):
        """
        关注通知：A关注B，给B推送消息
        follow_uid: 发起关注的用户（A）
        followed_uid: 被关注的用户（B，消息接收者）
        messageType = 0
        """
        # 查询发起关注人的昵称
        row = await mysql_database.execute_sql(sql_message.get_user_nick_by_id(), (follow_uid,))
        if not row:
            return
        nick = row[0]["userNick"]
        content = f"用户{nick}（ID：{follow_uid}）关注了你"
        # 插入消息，接收者是 followed_uid
        await mysql_database.execute_sql(
            sql_message.insert_message(),
            (followed_uid, 0, content)
        )

    @classmethod
    async def insert_video_like_message(cls, like_uid: int, liked_video_id: int):
        """
        视频点赞通知：A点赞视频，给视频作者推送消息
        like_uid: 点赞的用户A
        liked_video_id: 被点赞的视频ID
        messageType = 1
        """
        # 1. 查询点赞人的昵称
        user_row = await mysql_database.execute_sql(sql_message.get_user_nick_by_id(), (like_uid,))
        if not user_row:
            return
        nick = user_row[0]["userNick"]

        # 2. 查询视频标题 + 视频作者ID（消息接收人）
        video_row = await mysql_database.execute_sql(sql_message.get_video_title_and_author_by_id(), (liked_video_id,))
        if not video_row:
            return
        title = video_row[0]["videoTitle"]
        author_uid = video_row[0]["videoAuthor"]

        content = f"用户{nick}（ID：{like_uid}）点赞了你的视频《{title}》"
        # 插入消息，接收者是视频作者 author_uid
        await mysql_database.execute_sql(
            sql_message.insert_message(),
            (author_uid, 1, content)
        )

    @classmethod
    async def insert_video_comment_message(cls, comment_uid: int, video_id: int, comment_content: str):
        """
        一级评论通知：用户评论视频，通知视频作者
        messageType = 2
        comment_uid：评论人uid
        video_id：被评论视频id
        comment_content：本条评论原文
        """
        # 获取评论人昵称
        user_row = await mysql_database.execute_sql(sql_message.get_user_nick_by_id(), (comment_uid,))
        if not user_row:
            return
        nick = user_row[0]["userNick"]

        # 获取视频作者、视频标题
        video_row = await mysql_database.execute_sql(sql_message.get_video_author_by_vid(), (video_id,))
        if not video_row:
            return
        video_author_uid = video_row[0]["videoAuthor"]
        video_title = video_row[0]["videoTitle"]

        # 自己给自己视频评论，不发通知
        if video_author_uid == comment_uid:
            return

        msg = f"用户{nick}（ID：{comment_uid}）评论了你视频《{video_title}》，评论内容：{comment_content}"
        await mysql_database.execute_sql(
            sql_message.insert_message(),
            (video_author_uid, 2, msg)
        )

    @classmethod
    async def insert_comment_like_message(cls, like_uid: int, liked_comment_id: int):
        """
        评论点赞通知：A点赞评论，推送给这条评论的作者
        like_uid: 点赞用户
        liked_comment_id: 被点赞的评论ID
        messageType = 3（约定：1视频点赞，2评论回复，3评论点赞）
        """
        # 点赞人昵称
        user_row = await mysql_database.execute_sql(sql_message.get_user_nick_by_id(), (like_uid,))
        if not user_row:
            return
        nick = user_row[0]["userNick"]

        # 拿到评论作者、所属视频id
        comment_row = await mysql_database.execute_sql(sql_message.get_comment_author_and_video_id_by_cid(), (liked_comment_id,))
        if not comment_row:
            return
        comment_author_uid = comment_row[0]["userId"]
        video_id = comment_row[0]["videoId"]

        # 不自己给自己发通知
        if comment_author_uid == like_uid:
            return

        # 视频标题
        video_row = await mysql_database.execute_sql(sql_message.get_video_title_by_vid(), (video_id,))
        if not video_row:
            return
        video_title = video_row[0]["videoTitle"]

        comment_row = await mysql_database.execute_sql(sql_message.get_comment_content_by_cid(), (liked_comment_id,))
        comment_content = comment_row[0]["content"]

        msg_content = f"用户{nick}（ID：{like_uid}）点赞了你在视频《{video_title}》下的评论，评论原文：{comment_content}"
        await mysql_database.execute_sql(
            sql_message.insert_message(),
            (comment_author_uid, 3, msg_content)
        )

    @classmethod
    async def insert_comment_reply_message(
        cls,
        reply_uid: int,
        parent_comment_id: int,
        reply_content: str
    ):
        """
        回复评论通知：A回复B的评论，通知B
        messageType = 4
        reply_uid：回复人uid
        parent_comment_id：被回复的父评论id
        reply_content：本次回复的原文
        """
        # 获取回复人昵称
        user_row = await mysql_database.execute_sql(sql_message.get_user_nick_by_id(), (reply_uid,))
        if not user_row:
            return
        nick = user_row[0]["userNick"]

        # 获取父评论信息：父评论作者、父评论原文、视频id
        parent_comment_row = await mysql_database.execute_sql(sql_message.get_comment_info_by_cid(), (parent_comment_id,))
        if not parent_comment_row:
            return
        parent_comment_author_uid = parent_comment_row[0]["userId"]
        parent_comment_content = parent_comment_row[0]["content"]
        video_id = parent_comment_row[0]["videoId"]

        # 获取视频标题
        video_row = await mysql_database.execute_sql(sql_message.get_video_title_by_vid(), (video_id,))
        if not video_row:
            return
        video_title = video_row[0]["videoTitle"]

        # 自己回复自己的评论，不推送
        if parent_comment_author_uid == reply_uid:
            return

        msg = (
            f"用户{nick}（ID：{reply_uid}）回复了你在视频《{video_title}》下的评论。"
            f"你的原评论：{parent_comment_content}，对方回复：{reply_content}"
        )
        await mysql_database.execute_sql(
            sql_message.insert_message(),
            (parent_comment_author_uid, 4, msg)
        )

    message_type_title = [
        "被关注类消息",
        "视频点赞类消息",
        "视频评论类消息",
        "评论点赞类消息",
        "评论回复类消息"
    ]

    @classmethod
    def _cut_short_content(cls, text: str, max_len=36) -> str:
        """截断内容，超长末尾加...，前端单行预览"""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    @classmethod
    async def get_unread_message_list(cls, user_id: int):
        """获取未读消息预览列表"""
        rows = await mysql_database.execute_sql(sql_message.list_unread_message(), (user_id,))
        res = []
        for r in rows:
            msg_type = r["messageType"]
            # 防止越界，超出0~4显示未知消息
            title = cls.message_type_title[msg_type] if 0 <= msg_type < len(cls.message_type_title) else "未知通知消息"
            short_txt = cls._cut_short_content(r["content"])
            res.append({
                "messageId": r["messageId"],
                "title": title,
                "shortContent": short_txt,
                "createTime": r["createTime"].strftime("%Y-%m-%d %H:%M:%S")
            })
        return res

    @classmethod
    async def get_history_message_list(cls, user_id: int):
        """获取历史已读消息预览列表"""
        rows = await mysql_database.execute_sql(sql_message.list_history_message(), (user_id,))
        res = []
        for r in rows:
            msg_type = r["messageType"]
            title = cls.message_type_title[msg_type] if 0 <= msg_type < len(cls.message_type_title) else "未知通知消息"
            short_txt = cls._cut_short_content(r["content"])
            res.append({
                "messageId": r["messageId"],
                "title": title,
                "shortContent": short_txt,
                "createTime": r["createTime"].strftime("%Y-%m-%d %H:%M:%S")
            })
        return res

    @classmethod
    async def get_message_detail(cls, user_id: int, message_id: int):
        """获取消息详情，同时自动标记为已读"""
        row = await mysql_database.execute_sql(sql_message.get_message_detail_by_id(), (message_id, user_id))
        if not row:
            return None
        # 读取详情，标记已读
        await mysql_database.execute_sql(sql_message.mark_message_read(), (message_id, user_id))
        r = row[0]
        msg_type = r["messageType"]
        title = cls.message_type_title[msg_type] if 0 <= msg_type < len(cls.message_type_title) else "未知通知消息"
        return {
            "messageId": r["messageId"],
            "title": title,
            "fullContent": r["content"],
            "createTime": r["createTime"].strftime("%Y-%m-%d %H:%M:%S")
        }
        





