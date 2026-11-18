
from fastapi import Request
from fastapi import Depends, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse

from route.api_model import *
from service.user_service import user_service
from service.video_service import video_service
from service.message_service import message_service
from route.route_base import router, templates, get_current_user_id


# ========== 页面路由 ==========
@router.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    template = templates.get_template("login.html")
    return template.render(request=request)

@router.get("/user/register", response_class=HTMLResponse)
async def register_page(request: Request):
    template = templates.get_template("register.html")
    return template.render(request=request)

@router.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    template = templates.get_template("home.html")
    return template.render(request=request)

@router.get("/user/login", response_class=HTMLResponse)
async def login_html(request: Request):
    template = templates.get_template("login.html")
    return template.render(request=request)

# ========== 接口路由 /api/user ==========
@router.post("/api/user/send-code")
async def api_send_code(req: SendCodeReq):
    return await user_service.send_register_code(req.email.strip())

@router.post("/api/user/verify-code")
async def api_verify_code(req: VerifyCodeReq):
    return await user_service.verify_register_code(req.email.strip(), req.code.strip())

@router.post("/api/user/finish-register")
async def api_finish_register(req: FinishRegisterReq):
    return await user_service.finish_register(req.email.strip(), req.encrypted_password)

@router.post("/api/user/login-send-code")
async def api_login_send_code(data: dict):
    return await user_service.send_login_code(data["account"])

@router.post("/api/user/login")
async def api_login(data: dict):
    return await user_service.login(
        account=data["account"],
        loginType=data["loginType"],
        password=data.get("password"),
        code=data.get("code")
    )

@router.post("/api/user/logout")
async def api_logout(uid: int = Depends(get_current_user_id)):
    return await user_service.logout(str(uid))

@router.get("/api/user/verify-token")
async def api_verify_token(token: str):
    return await user_service.verify_token(token, "access")

@router.get("/api/user/profile")
async def api_user_profile(uid: int = Depends(get_current_user_id)):
    profile = await user_service.get_user_profile(uid)
    if profile is None:
        return {"code": 0, "msg": "用户不存在", "data": None}
    return {"code": 1, "msg": "ok", "data": profile}

@router.get("/api/user/follow-list")
async def api_follow_list(uid: int = Depends(get_current_user_id)):
    res_data = await user_service.get_my_follow_list(uid)
    return {"code": 1, "msg": "ok", "data": res_data}

@router.get("/api/user/fan-list")
async def api_fan_list(uid: int = Depends(get_current_user_id)):
    res_data = await user_service.get_my_fan_list(uid)
    return {"code": 1, "msg": "ok", "data": res_data}

@router.get("/api/user/comments")
async def api_user_comments(uid: int = Depends(get_current_user_id)):
    res_data = await video_service.get_user_comment_list(uid)
    return {"code": 1, "msg": "ok", "data": res_data}

@router.get("/api/search/user")
async def api_search_user(
    keyword: str = Query(..., description="搜索关键词"),
    uid: int = Depends(get_current_user_id)
):
    if not keyword.strip():
        return {"code":0, "msg":"搜索内容不能为空", "data":[]}
    data = await user_service.search_user(keyword.strip(), login_uid=uid)
    if not data:
        return {"code":0, "msg":"没有匹配用户", "data":[]}
    return {"code":1, "msg":"ok", "data":data}

@router.get("/api/user/blacklist")
async def api_get_my_blacklist(loginUserId: int = Query(...)):
    """获取我的黑名单列表"""
    list_data = await user_service.get_my_blacklist(loginUserId)
    return {"code": 1, "msg": "ok", "data": list_data}

@router.put("/api/user/update")
async def api_update_user(
    loginUserId: int = Query(...),
    userNick: str | None = Body(default=None),
    userPassword: str | None = Body(default=None)
):
    """修改昵称、密码，传null不修改"""
    ok = await user_service.update_user(loginUserId, userNick, userPassword)
    if not ok:
        return {"code": 0, "msg": "用户不存在"}
    return {"code": 1, "msg": "修改成功"}

@router.delete("/api/user/delete")
async def api_delete_account(loginUserId: int = Query(...)):
    """注销账号"""
    await user_service.delete_my_account(loginUserId)
    return {"code": 1, "msg": "账号已注销"}

@router.get("/api/user/info")
async def api_get_user_info(userId: int = Query(...)):
    """根据userId获取用户基础信息（昵称、ID、邮箱、创建时间，不返回密码）"""
    user = await user_service.get_user_by_id(userId)
    if not user:
        return {"code": 0, "msg": "用户不存在"}
    return {
        "code": 1,
        "msg": "ok",
        "data": user
    }

@router.get("/api/user/works")
async def api_user_works(loginUserId: int = Query(...)):
    """获取当前登录用户所有作品videoId列表"""
    vid_list = await user_service.get_user_works_video_id_list(loginUserId)
    return {
        "code": 1,
        "data": vid_list
    }

@router.get("/api/user/like-video")
async def api_user_like_video(loginUserId: int = Query(...)):
    """获取当前登录用户点赞的所有视频videoId列表"""
    vid_list = await user_service.get_user_like_video_id_list(loginUserId)
    return {
        "code": 1,
        "data": vid_list
    }

@router.get("/api/recommend/video-list")
async def api_recommend_video_list(loginUserId: int = Query(...)):
    """获取推荐流videoId列表"""
    vid_list = await user_service.get_recommend_video_id_list(loginUserId)
    return {
        "code": 1,
        "data": vid_list
    }

@router.get("/api/followed/video-list")
async def api_followed_video_list(loginUserId: int = Query(...)):
    """获取关注作者更新视频流 videoId 列表"""
    vid_list = await user_service.get_followed_video_id_list(loginUserId)
    return {
        "code": 1,
        "data": vid_list
    }

@router.get("/api/message/unread-list")
async def api_msg_unread_list(uid: int = Depends(get_current_user_id)):
    """获取未读消息预览列表"""
    data = await message_service.get_unread_message_list(uid)
    return JSONResponse(content={"code": 1, "msg": "ok", "data": data})

@router.get("/api/message/history-list")
async def api_msg_history_list(uid: int = Depends(get_current_user_id)):
    """获取历史已读消息预览列表"""
    data = await message_service.get_history_message_list(uid)
    return JSONResponse(content={"code": 1, "msg": "ok", "data": data})

@router.get("/api/message/detail")
async def api_msg_detail(messageId: int, uid: int = Depends(get_current_user_id)):
    """获取消息详情，自动标记已读"""
    detail = await message_service.get_message_detail(uid, messageId)
    if not detail:
        return JSONResponse(content={"code": 0, "msg": "消息不存在", "data": None})
    return JSONResponse(content={"code": 1, "msg": "ok", "data": detail})

@router.get("/api/account/info")
async def get_other_account_info(loginUserId: int = Query(...), targetUserId: int = Query(...)):
    """获取对方用户信息 + 是否关注、是否拉黑状态【打开主页第一步调用】"""
    user_info = await user_service.get_other_user_base_info(targetUserId)
    if not user_info:
        return {"code": 0, "msg": "用户不存在"}
    isFollow = await user_service.check_is_follow(loginUserId, targetUserId)
    isBlock = await user_service.check_is_block(loginUserId, targetUserId)
    isBlocked = await user_service.check_is_block(targetUserId, loginUserId)
    return {
        "code": 1,
        "msg": "ok",
        "data": {
            "userId": user_info["userId"],
            "userNick": user_info["userNick"],
            "isFollow": isFollow,
            "isBlock": isBlock,
            "isBlocked": isBlocked
        }
    }

@router.post("/api/account/follow")
async def api_follow(loginUserId: int = Query(...), targetUserId: int = Query(...)):
    await user_service.follow_user(loginUserId, targetUserId)
    return {"code": 1, "msg": "操作成功"}

@router.post("/api/account/unfollow")
async def api_unfollow(loginUserId: int = Query(...), targetUserId: int = Query(...)):
    await user_service.unfollow_user(loginUserId, targetUserId)
    return {"code": 1, "msg": "操作成功"}

@router.post("/api/account/block")
async def api_block(loginUserId: int = Query(...), targetUserId: int = Query(...)):
    await user_service.block_user(loginUserId, targetUserId)
    return {"code": 1, "msg": "操作成功"}

@router.post("/api/account/unblock")
async def api_unblock(loginUserId: int = Query(...), targetUserId: int = Query(...)):
    await user_service.unblock_user(loginUserId, targetUserId)
    return {"code": 1, "msg": "操作成功"}

@router.get("/api/account/works")
async def api_account_works(userId: int = Query(...)):
    """获取【其他用户】的作品videoId列表"""
    vid_list = await user_service.get_other_user_works_video_id_list(userId)
    return {
        "code": 1,
        "data": vid_list
    }

@router.post("/api/feedback/publish")
async def feedback_publish(
    body: FeedbackPublishBody,
    uid: int = Depends(get_current_user_id)
):
    ok, msg = await user_service.publish_feedback(uid, body.content)
    if ok:
        return {"code": 1, "msg": msg}
    return {"code": 0, "msg": msg}

@router.get("/api/feedback/list")
async def feedback_list(
    uid: int = Depends(get_current_user_id)
):
    data = await user_service.get_user_feedback_list(uid)
    return {"code": 1, "data": data}


