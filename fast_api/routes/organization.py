from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/overview-stats")
async def get_overview_stats(request: Request):
    print("REQUEST: get_overview_stats")
    print(request)
