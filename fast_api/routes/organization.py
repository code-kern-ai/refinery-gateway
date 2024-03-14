from fastapi import APIRouter, Request
from fast_api.routes.client_response import pack_json_result


router = APIRouter()


@router.get("/overview-stats")
async def get_overview_stats(request: Request):
    print("REQUEST: get_overview_stats")
    print(request)
    return pack_json_result({"status": 200, "message": "OK"})
