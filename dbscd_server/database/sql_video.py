
class sql_video:

    @classmethod
    def count_comment_by_userId(cls):
        """统计该用户所有评论总数"""
        return """
            SELECT COUNT(*) AS cnt FROM comment_table WHERE userId = %s
        """

    @classmethod
    def list_comment_by_userId(cls):
        """用户自己的评论列表，按评论时间逆序"""
        return """
            SELECT commentId, videoId, content, createTime
            FROM comment_table
            WHERE userId = %s
            ORDER BY createTime DESC
        """

    @classmethod
    def search_video_sql(cls):
        """
        搜索视频：标题模糊匹配，带出作者信息
        过滤：作者和当前用户双向拉黑全部剔除
        排序：作者是我关注的优先靠前，再按发布时间倒序
        """
        return """
            SELECT v.videoId, v.videoTitle, v.videoUrl, v.likeCount, v.createTime,
                u.userId AS authorId, u.userNick AS authorNick
            FROM video_table v
            LEFT JOIN user_table u ON v.videoAuthor = u.userId
            WHERE
                v.videoTitle LIKE CONCAT('%%', %s, '%%')
                AND v.videoAuthor NOT IN (
                    SELECT blockedId FROM blacklist_table WHERE userId = %s
                    UNION
                    SELECT userId FROM blacklist_table WHERE blockedId = %s
                )
            ORDER BY
                CASE WHEN v.videoAuthor IN (SELECT followedId FROM follow_table WHERE userId = %s) THEN 0 ELSE 1 END ASC,
                v.createTime DESC
            LIMIT 50
        """

    @classmethod
    def count_video_total_sql(cls):
        """统计video_table总条数，用于生成videoId"""
        return """
            SELECT COUNT(*) AS cnt FROM video_table
        """

    @classmethod
    def insert_video_sql(cls):
        """插入视频记录"""
        return """
            INSERT INTO video_table (videoUrl, videoTitle, videoAuthor, likeCount)
            VALUES (%s, %s, %s, 0)
        """

    @classmethod
    def get_video_preview_by_id(cls):
        """单条视频预览信息：关联用户表拿昵称"""
        return """
            SELECT
                v.videoId,
                v.videoUrl,
                v.videoTitle,
                v.videoAuthor,
                u.userNick,
                v.likeCount,
                v.createTime
            FROM video_table v
            LEFT JOIN user_table u ON v.videoAuthor = u.userId
            WHERE v.videoId = %s
        """

    @classmethod
    def get_video_detail_by_vid(cls):
        """查询视频详情+作者昵称"""
        return """
            SELECT v.videoId, v.videoUrl, v.videoTitle, v.videoAuthor, v.likeCount, v.createTime, u.userNick
            FROM video_table v
            LEFT JOIN user_table u ON v.videoAuthor = u.userId
            WHERE v.videoId = %s
        """

    @classmethod
    def check_user_like_video(cls):
        """查询用户是否已经点赞该视频"""
        return """
            SELECT 1 FROM user_video_like_table WHERE userId = %s AND videoId = %s
        """

    @classmethod
    def add_video_like(cls):
        """新增点赞记录"""
        return """
            INSERT INTO user_video_like_table (userId, videoId) VALUES (%s, %s)
        """

    @classmethod
    def remove_video_like(cls):
        """取消点赞，删除点赞记录"""
        return """
            DELETE FROM user_video_like_table WHERE userId = %s AND videoId = %s
        """

    @classmethod
    def inc_video_like_count(cls):
        """点赞数 +1"""
        return """
            UPDATE video_table SET likeCount = likeCount + 1 WHERE videoId = %s
        """

    @classmethod
    def dec_video_like_count(cls):
        """点赞数 -1"""
        return """
            UPDATE video_table SET likeCount = likeCount - 1 WHERE videoId = %s
        """

    @classmethod
    def get_blacklist_ids(cls):
        """获取和uid存在拉黑关系的所有用户ID（我拉黑的 + 拉黑我的）"""
        return """
            SELECT blockedId FROM blacklist_table WHERE userId = %s
            UNION
            SELECT userId FROM blacklist_table WHERE blockedId = %s
        """

    @classmethod
    def list_first_level_comment_by_video(cls):
        """查询视频一级评论 parentId IS NULL，关联用户昵称"""
        return """
            SELECT c.commentId, c.videoId, c.userId, c.parentId, c.content, c.likeCount, c.createTime, u.userNick
            FROM comment_table c
            LEFT JOIN user_table u ON c.userId = u.userId
            WHERE c.videoId = %s AND c.parentId IS NULL
            ORDER BY c.createTime DESC
        """

    @classmethod
    def list_second_level_comment_by_parent(cls):
        """查询指定父评论下所有二级评论（parentId = 一级评论id），关联用户、父评论发布者昵称"""
        return """
            SELECT 
                sc.commentId, sc.videoId, sc.userId, sc.parentId, sc.content, sc.likeCount, sc.createTime,
                cu.userNick, pu.userNick AS parentUserNick
            FROM comment_table sc
            LEFT JOIN user_table cu ON sc.userId = cu.userId
            LEFT JOIN comment_table pc ON sc.parentId = pc.commentId
            LEFT JOIN user_table pu ON pc.userId = pu.userId
            WHERE sc.parentId = %s
            ORDER BY sc.createTime DESC
        """

    @classmethod
    def get_direct_child_comments(cls):
        """根据父commentId，查询它的直接子评论（只查下一代，递归外层Python控制）"""
        return """
            SELECT 
                c.commentId, c.videoId, c.userId, c.parentId, c.content, c.likeCount, c.createTime,
                cu.userNick, pu.userNick AS parentUserNick
            FROM comment_table c
            LEFT JOIN user_table cu ON c.userId = cu.userId
            LEFT JOIN comment_table pc ON c.parentId = pc.commentId
            LEFT JOIN user_table pu ON pc.userId = pu.userId
            WHERE c.parentId = %s
            ORDER BY c.createTime DESC
        """

    @classmethod
    def check_comment_like(cls):
        """查询用户是否点赞该评论"""
        return """
            SELECT 1 FROM user_comment_like_table WHERE userId = %s AND commentId = %s LIMIT 1
        """

    @classmethod
    def add_comment_like(cls):
        """点赞评论"""
        return """
            INSERT INTO user_comment_like_table (userId, commentId) VALUES (%s, %s)
        """

    @classmethod
    def remove_comment_like(cls):
        """取消评论点赞"""
        return """
            DELETE FROM user_comment_like_table WHERE userId = %s AND commentId = %s
        """

    @classmethod
    def inc_comment_like_count(cls):
        """评论点赞 +1"""
        return """
            UPDATE comment_table SET likeCount = likeCount + 1 WHERE commentId = %s
        """

    @classmethod
    def dec_comment_like_count(cls):
        """评论点赞 -1"""
        return """
            UPDATE comment_table SET likeCount = likeCount - 1 WHERE commentId = %s
        """

    @classmethod
    def insert_comment(cls):
        """新增评论，parentId可为NULL"""
        return """
            INSERT INTO comment_table (videoId, userId, parentId, content) VALUES (%s, %s, %s, %s)
        """

    @classmethod
    def delete_comment_by_id(cls):
        """删除评论，校验归属：只能删除自己发的评论"""
        return """
            DELETE FROM comment_table WHERE commentId = %s AND userId = %s
        """

    @classmethod
    def delete_video_by_id(cls):
        """删除视频主记录，关联评论、点赞依靠外键级联自动删除"""
        return """
            DELETE FROM video_table WHERE videoId = %s AND videoAuthor = %s
        """




