
class sql_db:

    @classmethod
    def database_exists(cls):
        return "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME=%s"

    @classmethod
    def create_database(cls, db_name: str, charset: str):
        return (
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            f"CHARACTER SET {charset} COLLATE utf8mb4_unicode_ci;"
        )

    @classmethod
    def create_user_table(cls):
        return """
            CREATE TABLE IF NOT EXISTS user_table (
                userId BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID，唯一标识',
                userEmail VARCHAR(255) NOT NULL COMMENT '注册登录邮箱',
                userPassword VARCHAR(60) NOT NULL COMMENT 'bcrypt加密后的密码',
                userNick VARCHAR(100) NOT NULL COMMENT '用户昵称',
                createTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间，插入自动填充',
                UNIQUE INDEX uk_user_email (userEmail)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
        """

    @classmethod
    def create_video_table(cls):
        return """
            CREATE TABLE IF NOT EXISTS video_table (
                videoId BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '视频ID，唯一标识',
                videoUrl VARCHAR(512) NOT NULL COMMENT '视频资源路径/链接',
                videoTitle VARCHAR(512) NOT NULL COMMENT '视频标题',
                videoAuthor BIGINT NOT NULL COMMENT '视频作者userId',
                likeCount BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '点赞数，初始0',
                createTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间，插入自动填充',
                INDEX idx_video_author (videoAuthor),
                FOREIGN KEY (videoAuthor) REFERENCES user_table(userId) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='视频表';
        """

    @classmethod
    def create_user_video_like_table(cls):
        return """
            CREATE TABLE IF NOT EXISTS user_video_like_table (
                userId BIGINT NOT NULL COMMENT '点赞用户ID',
                videoId BIGINT NOT NULL COMMENT '被点赞视频ID',
                createTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
                PRIMARY KEY (userId, videoId),
                FOREIGN KEY (userId) REFERENCES user_table(userId) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (videoId) REFERENCES video_table(videoId) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户视频点赞表';
        """

    @classmethod
    def create_comment_table(cls):
        return """
            CREATE TABLE IF NOT EXISTS comment_table (
                commentId BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '评论ID，唯一标识',
                videoId BIGINT NOT NULL COMMENT '所属视频ID',
                userId BIGINT NOT NULL COMMENT '评论发布用户ID',
                parentId BIGINT NULL COMMENT '父评论ID，回复的目标评论',
                content VARCHAR(1024) NOT NULL COMMENT '评论内容',
                likeCount BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '评论点赞数，初始0',
                createTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评论发布时间',
                INDEX idx_comment_video (videoId),
                INDEX idx_comment_user (userId),
                INDEX idx_comment_parent (parentId),
                FOREIGN KEY (videoId) REFERENCES video_table(videoId) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (userId) REFERENCES user_table(userId) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (parentId) REFERENCES comment_table(commentId) ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论表';
        """

    @classmethod
    def create_user_comment_like_table(cls):
        return """
            CREATE TABLE IF NOT EXISTS user_comment_like_table (
                userId BIGINT NOT NULL COMMENT '点赞用户ID',
                commentId BIGINT NOT NULL COMMENT '被点赞评论ID',
                createTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
                PRIMARY KEY (userId, commentId),
                FOREIGN KEY (userId) REFERENCES user_table(userId) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (commentId) REFERENCES comment_table(commentId) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户评论点赞表';
        """

    @classmethod
    def create_follow_table(cls):
        return """
            CREATE TABLE IF NOT EXISTS follow_table (
                userId BIGINT NOT NULL COMMENT '关注操作人ID',
                followedId BIGINT NOT NULL COMMENT '被关注用户ID',
                createTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '关注时间',
                PRIMARY KEY (userId, followedId),
                FOREIGN KEY (userId) REFERENCES user_table(userId) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (followedId) REFERENCES user_table(userId) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='关注表';
        """

    @classmethod
    def create_blacklist_table(cls):
        return """
            CREATE TABLE IF NOT EXISTS blacklist_table (
                userId BIGINT NOT NULL COMMENT '拉黑操作人ID',
                blockedId BIGINT NOT NULL COMMENT '被拉黑用户ID',
                createTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '拉黑时间',
                PRIMARY KEY (userId, blockedId),
                FOREIGN KEY (userId) REFERENCES user_table(userId) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (blockedId) REFERENCES user_table(userId) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='拉黑表';
        """

    @classmethod
    def create_message_table(cls):
        """
        消息表 message_table
        messageType: 0被关注,1视频点赞,2视频评论,3评论点赞,4评论回复
        readed: 0未读 1已读，默认0
        """
        return """
            CREATE TABLE IF NOT EXISTS message_table (
                messageId BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '消息ID，唯一标识',
                userId BIGINT NULL COMMENT '消息推送目标用户ID',
                messageType TINYINT NOT NULL COMMENT '消息类型：0被关注，1视频点赞，2视频评论，3评论点赞，4评论回复',
                readed BOOLEAN NOT NULL DEFAULT 0 COMMENT '是否已读，0未读，1已读',
                content VARCHAR(2048) NOT NULL COMMENT '消息文本内容',
                createTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '消息创建时间',
                INDEX idx_msg_user (userId),
                FOREIGN KEY (userId) REFERENCES user_table(userId) ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统消息通知表';
        """

    @classmethod
    def create_feedback_table(cls):
        return """
            CREATE TABLE IF NOT EXISTS feedback_table (
                feedbackId BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '反馈唯一ID',
                userId BIGINT NULL COMMENT '反馈用户ID，外键关联user_table.userId',
                content VARCHAR(1024) NOT NULL COMMENT '反馈内容',
                createTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '反馈提交时间，插入自动填充',
                INDEX idx_feedback_user (userId),
                FOREIGN KEY (userId) REFERENCES user_table(userId)
                    ON DELETE SET NULL
                    ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT '用户反馈表';
        """









