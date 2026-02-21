# KOOS Temp Server

MOHID 해양 수치모델 데이터를 웹 맵 타일(`{z}/{x}/{y}`) 형식으로 서브세팅하여 클라이언트에 제공하는 타일 서버입니다.

## 구조

```
├── main.ipynb         # NetCDF → 타일 JSON 변환 (전처리)
├── server.py          # FastAPI 타일 서빙 서버
├── requirements.txt   # Python 의존성
├── data/              # 원본 MOHID NetCDF 파일 (git 미추적)
└── tiles/             # 생성된 타일 JSON 파일 (git 미추적)
```

## 서브세팅 원리 (main.ipynb)

### 1. 입력 데이터

MOHID 수치모델이 출력한 NetCDF 파일 두 종류를 사용합니다:

- **Hydrodynamic** (`L2_Hydrodynamic_*.nc`): 유속(`u`, `v`), 해수면 높이(`ssh`)
- **WaterProperties** (`L2_WaterProperties_*.nc`): 수온(`temperature`), 염분(`salinity`)

두 파일 모두 동일한 정규 격자(712 x 720, 위도 28.68 - 43.49, 경도 117.51 - 132.49)를 가집니다.

### 2. 웹 맵 타일 좌표 매핑

격자점의 위경도를 [Slippy Map](https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames) 타일 좌표로 변환합니다:

```
tile_x = floor((lon + 180) / 360 * 2^zoom)
tile_y = floor((1 - log(tan(lat) + sec(lat)) / pi) / 2 * 2^zoom)
```

각 격자점이 어느 `(z, x, y)` 타일에 속하는지 벡터 연산으로 일괄 계산한 뒤, 동일 타일에 속하는 격자점끼리 묶어 JSON 파일로 저장합니다.

### 3. 줌 레벨별 스트라이드

데이터 밀도를 줌 레벨에 맞게 조절하기 위해 격자점을 일정 간격으로 건너뛰는(stride) 방식을 사용합니다:

| Zoom | Stride | 설명 |
|------|--------|------|
| 6 | 5 | 격자점 5개당 1개 사용 (광역 조감) |
| 7 | 4 | 격자점 4개당 1개 사용 |
| 8 | 3 | 격자점 3개당 1개 사용 |
| 9 | 1 | 전체 격자점 사용 |
| 10 | 1 | 전체 격자점 사용 |

### 4. 타일 저장 형식

생성된 타일은 `tiles/{dataset}/{z}/{x}/{y}.json` 경로에 저장되며, JSON 구조는 다음과 같습니다:

```json
{
  "lon": [127.51, 127.53, ...],
  "lat": [33.52, 33.54, ...],
  "temperature": [[15.2, 15.3, ...], ...]
}
```

- `lon`, `lat`: 해당 타일에 포함된 좌표 배열 (1차원)
- 변수 데이터: `lat x lon` 크기의 2차원 배열
- 육지 등 데이터가 없는 격자점은 `null`

### 5. 병렬 처리

4개 데이터셋(`uv`, `ssh`, `temperature`, `salinity`)을 `ThreadPoolExecutor`로 동시에 처리합니다.

## 서빙 (server.py)

FastAPI 기반 타일 서버입니다.

- **엔드포인트**: `GET /tiles/{dataset}/{z}/{x}/{y}.json`
- **줌 매핑**: 실제 타일이 존재하지 않는 높은 줌 레벨(11-13)은 비트 시프트로 zoom 10 타일 좌표로 매핑하여 응답합니다.

  ```
  actual_x = x >> (z - actual_z)
  actual_y = y >> (z - actual_z)
  ```

- **응답 코드**:
  - `200`: 타일 데이터 반환
  - `204`: 해당 좌표에 데이터 없음 (육지 등)
  - `404`: 지원하지 않는 줌 레벨

## 실행 방법

### 1. 환경 설정

```bash
python -m venv .venv --prompt koos-temp-server
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

> Python 3.12 사용을 권장합니다.

### 2. 타일 생성 (전처리)

`data/` 디렉토리에 MOHID NetCDF 파일을 배치한 후 `main.ipynb`를 순서대로 실행합니다. `tiles/` 디렉토리에 JSON 타일이 생성됩니다.

### 3. 서버 실행

```bash
python server.py
```

서버가 `http://0.0.0.0:8000`에서 시작됩니다.

타일 요청 예시:

```
GET http://localhost:8000/tiles/temperature/8/214/99.json
```
