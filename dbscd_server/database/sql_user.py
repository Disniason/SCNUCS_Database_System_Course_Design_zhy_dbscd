
class sql_user:

    @classmethod
    def check_email_exists(cls):
        """检查邮箱是否已经注册"""
        return "SELECT userId FROM user_table WHERE userEmail = %s LIMIT 1;"

    @classmethod
    def insert_user(cls):
        """插入新用户"""
        return """
            INSERT INTO user_table(userEmail, userPassword, userNick)
            VALUES (%s, %s, %s);
        """

    def sql_user_login():
        return """
            SELECT userId, userEmail, userPassword FROM user_table
            WHERE userEmail = %s OR userId = %s
            LIMIT 1
        """

    def sql_query_email_by_account():
        return """
            SELECT userEmail FROM user_table
            WHERE userEmail = %s OR userId = %s
            LIMIT 1
        """

    @classmethod
    def get_user_profile_by_id(cls):
        return """
            SELECT userId, userNick FROM user_table WHERE userId = %s
        """

    @classmethod
    def count_follow_by_userId(cls):
        """统计当前用户关注总数"""
        return """
            SELECT COUNT(*) AS cnt FROM follow_table WHERE userId = %s
        """

    @classmethod
    def list_follow_by_userId(cls):
        """获取我的关注列表，逆序"""
        return """
            SELECT f.followedId, u.userNick, f.createTime
            FROM follow_table f
            INNER JOIN user_table u ON f.followedId = u.userId
            WHERE f.userId = %s
            ORDER BY f.createTime DESC
        """

    @classmethod
    def count_fan_by_followedId(cls):
        """统计我的粉丝总数：followedId是我"""
        return """
            SELECT COUNT(*) AS cnt FROM follow_table WHERE followedId = %s
        """

    @classmethod
    def list_fan_by_followedId(cls):
        """获取粉丝列表，逆序"""
        return """
            SELECT f.userId, u.userNick, f.createTime
            FROM follow_table f
            INNER JOIN user_table u ON f.userId = u.userId
            WHERE f.followedId = %s
            ORDER BY f.createTime DESC
        """

    @classmethod
    def search_user_sql(cls):
        """
        搜索用户：userId精确匹配 OR 昵称模糊匹配
        过滤双向拉黑，我关注的优先排序
        :param login_uid: 当前登录用户
        """
        return """
            SELECT userId, userNick, createTime
            FROM user_table
            WHERE
                (userId = %s OR userNick LIKE CONCAT('%%', %s, '%%'))
                AND userId NOT IN (
                    SELECT blockedId FROM blacklist_table WHERE userId = %s
                    UNION
                    SELECT userId FROM blacklist_table WHERE blockedId = %s
                )
            ORDER BY
                CASE WHEN userId IN (SELECT followedId FROM follow_table WHERE userId = %s) THEN 0 ELSE 1 END ASC,
                createTime DESC
            LIMIT 50
        """

    @classmethod
    def get_other_user_info_sql(cls):
        """获取对方用户昵称ID"""
        return """
            SELECT userId, userNick
            FROM user_table
            WHERE userId = %s
        """

    @classmethod
    def check_follow_sql(cls):
        """查询是否关注：loginUserId 关注 targetUserId"""
        return """
            SELECT 1 FROM follow_table WHERE userId=%s AND followedId=%s
        """

    @classmethod
    def check_block_sql(cls):
        """查询是否拉黑：loginUserId 拉黑 targetUserId"""
        return """
            SELECT 1 FROM blacklist_table WHERE userId=%s AND blockedId=%s
        """

    @classmethod
    def add_follow_sql(cls):
        """新增关注"""
        return """
            INSERT IGNORE INTO follow_table(userId, followedId) VALUES (%s, %s)
        """

    @classmethod
    def remove_follow_sql(cls):
        """取消关注"""
        return """
            DELETE FROM follow_table WHERE userId=%s AND followedId=%s
        """

    @classmethod
    def add_block_sql(cls):
        """加入黑名单"""
        return """
            INSERT IGNORE INTO blacklist_table(userId, blockedId) VALUES (%s, %s)
        """

    @classmethod
    def remove_block_sql(cls):
        """解除黑名单"""
        return """
            DELETE FROM blacklist_table WHERE userId=%s AND blockedId=%s
        """

    @classmethod
    def get_black_list_sql(cls):
        """查询当前用户拉黑的全部用户：loginUserId 是操作者，返回被拉黑用户信息"""
        return """
            SELECT ut.userId, ut.userNick
            FROM blacklist_table bl
            LEFT JOIN user_table ut ON bl.blockedId = ut.userId
            WHERE bl.userId = %s
            ORDER BY bl.createTime DESC
        """

    @classmethod
    def update_user_info_sql(cls):
        """更新昵称/密码，二选一或者一起更新"""
        return """
            UPDATE user_table
            SET userNick = %s, userPassword = %s
            WHERE userId = %s
        """

    @classmethod
    def select_user_nick_pwd_by_id_sql(cls):
        """查询用户昵称、密码哈希"""
        return """
            SELECT userNick, userPassword
            FROM user_table
            WHERE userId = %s
        """

    @classmethod
    def update_user_info_sql(cls):
        """更新昵称、密码哈希"""
        return """
            UPDATE user_table
            SET userNick = %s, userPassword = %s
            WHERE userId = %s
        """

    @classmethod
    def delete_user_by_id_sql(cls):
        return "DELETE FROM user_table WHERE userId = %s"

    @classmethod
    def select_user_by_id_sql(cls):
        return """
            SELECT userId, userNick, userEmail, createTime
            FROM user_table
            WHERE userId = %s
        """

    @classmethod
    def get_user_work_video_ids(cls):
        """根据作者userId 查询他所有作品videoId列表"""
        return """
            SELECT videoId FROM video_table
            WHERE videoAuthor = %s
            ORDER BY createTime DESC
        """

    @classmethod
    def get_user_like_video_ids(cls):
        """根据用户userId 查询他点赞过的所有videoId列表，按点赞时间倒序"""
        return """
            SELECT videoId FROM user_video_like_table
            WHERE userId = %s
            ORDER BY createTime DESC
        """

    @classmethod
    def get_recommend_video_ids(cls):
        return """
            SELECT t.videoId
            FROM (
                SELECT v.videoId, v.createTime
                FROM video_table v
                WHERE v.videoId NOT IN (
                    SELECT videoId FROM user_video_like_table WHERE userId = %s
                )
                AND v.videoAuthor NOT IN (
                    SELECT blockedId FROM blacklist_table WHERE userId = %s
                )
                AND v.videoAuthor NOT IN (
                    SELECT userId FROM blacklist_table WHERE blockedId = %s
                )
                ORDER BY v.createTime DESC
            ) t
            GROUP BY t.videoId
            ORDER BY t.createTime DESC
        """

    @classmethod
    def get_other_user_work_video_ids(cls):
        """查询指定用户的作品ID列表，和自己作品SQL逻辑一致"""
        return """
            SELECT videoId FROM video_table
            WHERE videoAuthor = %s
            ORDER BY createTime DESC
        """

    @classmethod
    def get_followed_video_ids(cls):
        """
        关注流：获取已关注作者的视频ID
        过滤双向拉黑
        排序：未点赞优先，同组内时间倒序
        """
        return """
            SELECT DISTINCT v.videoId, v.createTime
            FROM video_table v
            INNER JOIN follow_table f ON v.videoAuthor = f.followedId AND f.userId = %s
            WHERE
                v.videoAuthor NOT IN (SELECT blockedId FROM blacklist_table WHERE userId = %s)
                AND v.videoAuthor NOT IN (SELECT userId FROM blacklist_table WHERE blockedId = %s)
            ORDER BY
                CASE WHEN v.videoId IN (SELECT videoId FROM user_video_like_table WHERE userId = %s) THEN 1 ELSE 0 END ASC,
                v.createTime DESC
            LIMIT 100
        """

    @classmethod
    def insert_feedback(cls):
        """新增反馈"""
        return """
            INSERT INTO feedback_table (userId, content) VALUES (%s, %s)
        """

    @classmethod
    def list_feedback_by_user(cls):
        """查询当前用户全部反馈，createTime DESC 逆序"""
        return """
            SELECT feedbackId, content, createTime
            FROM feedback_table
            WHERE userId = %s
            ORDER BY createTime DESC
        """


