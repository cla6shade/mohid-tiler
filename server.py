import logging
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

TILES_DIR = Path("./tiles")

# 타일은 zoom 6, 7, 9만 생성. 나머지는 좌표 변환으로 대응
ZOOM_MAPPING = {
    6: 6, 7: 7, 8: 8,
    9: 9, 10: 10, 11: 10, 12: 10, 13: 10,
}


@app.on_event("startup")
async def startup():
    datasets = [d.name for d in TILES_DIR.iterdir() if d.is_dir()] if TILES_DIR.exists() else []
    logger.info(f"Tile server started — datasets: {datasets}")


@app.get("/tiles/{dataset}/{z}/{x}/{y}.json")
async def get_tile(dataset: str, z: int, x: int, y: int):
    actual_z = ZOOM_MAPPING.get(z)
    if actual_z is None:
        logger.warning(f"Invalid zoom {z} for {dataset}/{z}/{x}/{y}")
        return Response(status_code=404)

    # zoom 차이만큼 x, y를 나눠서 상위 타일 좌표로 변환
    diff = z - actual_z
    actual_x = x >> diff
    actual_y = y >> diff

    file_path = TILES_DIR / dataset / str(actual_z) / str(actual_x) / f"{actual_y}.json"

    if not file_path.exists():
        return Response(status_code=204)

    logger.debug(f"Serving {dataset}/{z}/{x}/{y}")
    return Response(
        content=file_path.read_bytes(),
        media_type="application/json",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
