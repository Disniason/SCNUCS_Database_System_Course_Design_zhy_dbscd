

class sql_message:
    @classmethod
    def get_user_nick_by_id(cls):
        """根据userId查询用户昵称"""
        return "SELECT userNick FROM user_table WHERE userId = %s LIMIT 1"

    @classmethod
    def get_video_title_and_author_by_id(cls):
        """根据videoId 查询视频标题、视频作者userId"""
        return "SELECT videoTitle, videoAuthor FROM video_table WHERE videoId = %s LIMIT 1"

    @classmethod
    def insert_message(cls):
        """插入通知消息
        :params: userId(接收消息的用户), messageType, content
        """
        return """
            INSERT INTO message_table (userId, messageType, content)
            VALUES (%s, %s, %s)
        """

    @classmethod
    def list_unread_message(cls):
        """查询当前用户【未读消息预览】readed=0，时间倒序"""
        return """
            SELECT messageId, messageType, content, createTime
            FROM message_table
            WHERE userId = %s AND readed = 0
            ORDER BY createTime DESC
        """

    @classmethod
    def list_history_message(cls):
        """查询当前用户【已读历史消息预览】readed=1，时间倒序"""
        return """
            SELECT messageId, messageType, content, createTime
            FROM message_table
            WHERE userId = %s AND readed = 1
            ORDER BY createTime DESC
        """

    @classmethod
    def get_message_detail_by_id(cls):
        """根据messageId获取单条完整消息"""
        return """
            SELECT messageId, messageType, content, createTime, readed
            FROM message_table
            WHERE messageId = %s AND userId = %s
            LIMIT 1
        """

    @classmethod
    def mark_message_read(cls):
        """标记消息为已读 readed=1"""
        return """
            UPDATE message_table
            SET readed = 1
            WHERE messageId = %s AND userId = %s
        """

    @classmethod
    def get_comment_author_and_video_id_by_cid(cls):
        """通过commentId拿到评论发布者userId、所属videoId"""
        return """
            SELECT userId, videoId FROM comment_table WHERE commentId = %s
        """

    @classmethod
    def get_video_title_by_vid(cls):
        """根据videoId拿视频标题"""
        return """
            SELECT videoTitle FROM video_table WHERE videoId = %s
        """

    @classmethod
    def get_video_author_by_vid(cls):
        """根据videoId，拿到视频作者uid + 视频标题"""
        return """
            SELECT videoAuthor, videoTitle FROM video_table WHERE videoId = %s
        """

    @classmethod
    def get_comment_info_by_cid(cls):
        """根据commentId拿到：评论作者uid、评论原文content、所属videoId"""
        return """
            SELECT userId, content, videoId FROM comment_table WHERE commentId = %s
        """

    @classmethod
    def get_comment_content_by_cid(cls):
        """根据commentId拿到：评论作者uid、评论原文content、所属videoId"""
        return """
            SELECT content FROM comment_table WHERE commentId = %s
        """



