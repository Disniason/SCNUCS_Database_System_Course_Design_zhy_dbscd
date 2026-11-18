
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from fastapi import Request, APIRouter, HTTPException

from service.user_service import user_service


# 模板路径自行配置
templates_path = "./templates"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login", auto_error=False)
router = APIRouter()
templates = Jinja2Templates(directory=templates_path)

# 依赖：token解析，获取当前登录用户id（对齐get_current_learner_id风格）
async def get_current_user_id(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = auth_header.split(" ")[1]
    res = await user_service.verify_token(token, "access")
    if res["code"] != 1:
        raise HTTPException(status_code=401, detail=res["msg"])
    return int(res["data"]["sub"])
