


from service.user_service import user_service
from service.video_service import video_service


class tester:

    @classmethod
    async def insert_10000_user(cls):
        for _ in range(10000):
            email = f'20242181{_:04d}@m.scnu.edu.cn'
            password =  f'20242181{_:04d}'
            res = await user_service.finish_register(email,password)
            if res['code'] == 1:
                print(res['msg'])

    @classmethod
    async def insert_100000_user_video_like(cls):
        for vid in range(0, 14):
            for uid in range(6, 10005):
                res = await video_service.like_video(uid, vid)
                if res is not None and res == True:
                    print(f'插入视频点赞记录成功uid: {uid}, vid: {vid}')











