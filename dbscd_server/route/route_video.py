import os
from fastapi import UploadFile
from fastapi.responses import JSONResponse
from fastapi import Query, File, Form, Depends

from route.api_model import *
from service.video_service import video_service
from route.route_base import router, get_current_user_id


@router.get("/api/search/video")
async def api_search_video(
    keyword: str = Query(..., description="搜索关键词"),
    uid: int = Depends(get_current_user_id)
):
    if not keyword.strip():
        return {"code":0, "msg":"搜索内容不能为空", "data":[]}
    data = await video_service.search_video(keyword.strip(), login_uid=uid)
    if not data:
        return {"code":0, "msg":"没有匹配视频", "data":[]}
    return {"code":1, "msg":"ok", "data":data}

@router.post("/api/video/upload")
async def api_video_upload(
    loginUserId: int = Query(...),
    videoTitle: str = Form(...),
    file: UploadFile = File(...)
):
    # 校验后缀
    if not file.filename.lower().endswith(".mp4"):
        return JSONResponse(content={"code":0, "msg":"仅支持 mp4 视频文件"}, status_code=400)
    if len(videoTitle) > 128:
        return JSONResponse(content={"code":0, "msg":"视频标题最多128个字"})

    video_service.ensure_video_dir()
    next_vid = await video_service.get_next_video_id()
    file_name = f"video_{loginUserId}_{next_vid}.mp4"
    full_save_path = os.path.join(video_service.VIDEO_SAVE_BASE, file_name)

    # 分片写入磁盘
    with open(full_save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    # 存入数据库的路径（你前端访问静态资源可以按需调整；这里存绝对路径）
    db_video_url = full_save_path
    await video_service.create_video_record(db_video_url, videoTitle, loginUserId)

    return {"code":1, "msg":"上传发布成功", "data":{"videoId": next_vid}}

@router.get("/api/video/preview")
async def api_video_preview(videoId: int = Query(...)):
    """独立接口：根据videoId 获取视频预览卡片信息（封面、标题、作者、点赞、时间）"""
    preview_data = await video_service.get_video_preview(videoId)
    if preview_data is None:
        return {"code": -1, "msg": "视频不存在"}
    return {
        "code": 1,
        "data": preview_data
    }

@router.get("/api/video/detail")
async def api_video_detail(videoId: int):
    """获取视频详情信息，不需要登录"""
    detail = await video_service.get_video_detail(videoId)
    if not detail:
        return JSONResponse(content={"code":0, "msg":"视频不存在", "data":None})
    return JSONResponse(content={"code":1, "msg":"ok", "data":detail})

@router.get("/api/video/check-like")
async def api_check_like(videoId: int, uid: int = Depends(get_current_user_id)):
    """检查当前登录用户是否点赞"""
    liked = await video_service.is_user_liked_video(uid, videoId)
    return JSONResponse(content={"code":1, "msg":"ok", "data":{"liked":liked}})

@router.post("/api/video/like")
async def api_like_video(videoId: int, uid: int = Depends(get_current_user_id)):
    """点赞接口"""
    await video_service.like_video(uid, videoId)
    return JSONResponse(content={"code":1, "msg":"点赞成功"})

@router.post("/api/video/cancel-like")
async def api_cancel_like_video(videoId: int, uid: int = Depends(get_current_user_id)):
    """取消点赞接口"""
    await video_service.cancel_like_video(uid, videoId)
    return JSONResponse(content={"code":1, "msg":"已取消点赞"})

@router.get("/api/comment/first-list")
async def api_comment_first_list(videoId: int, uid: int = Depends(get_current_user_id)):
    data = await video_service.list_first_level_comment(videoId, uid)
    return JSONResponse(content={"code": 1, "msg": "ok", "data": data})

@router.get("/api/comment/flat-descendant-list")
async def api_comment_flat_descendant_list(parentFirstCommentId: int, uid: int = Depends(get_current_user_id)):
    """
    前端点击一级评论【展开】调用这个接口
    返回：这条一级评论下所有后代（2级原样、≥3级后端已经拼接回复前缀）扁平化数组
    """
    data = await video_service.list_all_flat_descendant_comments(parentFirstCommentId, uid)
    return JSONResponse(content={"code": 1, "msg": "ok", "data": data})

@router.post("/api/comment/toggle-like")
async def api_comment_toggle_like(commentId: int, uid: int = Depends(get_current_user_id)):
    new_like_status = await video_service.toggle_comment_like(uid, commentId)
    return JSONResponse(content={"code": 1, "msg": "ok", "data": {"isLiked": new_like_status}})

@router.post("/api/comment/publish")
async def api_comment_publish(
    videoId: int,
    content: str,
    parentId: int | None = Query(default=None),
    uid: int = Depends(get_current_user_id)
):
    if not content or len(content.strip()) == 0:
        return JSONResponse(content={"code": 0, "msg": "评论内容不能为空", "data": None})
    if len(content) > 256:
        return JSONResponse(content={"code":0, "msg":"评论不能超过256个汉字"})
    await video_service.publish_comment(videoId, uid, parentId, content.strip())
    return JSONResponse(content={"code": 1, "msg": "发表成功", "data": None})

@router.post("/api/comment/delete")
async def api_comment_delete(
    commentId: int,
    uid: int = Depends(get_current_user_id)
):
    ok = await video_service.delete_my_comment(uid, commentId)
    if ok:
        return JSONResponse(content={"code": 1, "msg": "删除成功", "data": None})
    else:
        return JSONResponse(content={"code": 0, "msg": "无权删除或者评论不存在", "data": None})

@router.post("/api/video/delete")
async def delete_video(
    videoId: int,
    login_uid: dict = Depends(get_current_user_id)
):
    ok, msg = await video_service.delete_video(login_uid, videoId)
    return {"code": 1, "msg": msg} if ok else {"code": 0, "msg": msg}



