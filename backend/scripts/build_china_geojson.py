"""
构建中国市级行政区边界 GeoJSON（供离线反向地理编码使用）。

数据来源：阿里 DataV.GeoAtlas 公共边界服务
    https://geo.datav.aliyun.com/areas_v3/bound/{adcode}_full.json

流程：
    1. 拉取全国省级列表（100000_full.json）；
    2. 逐省下钻拉取市级边界；直辖市 / 港澳台无市级，直接用省级面并以省名作为“市”；
    3. 坐标四舍五入到 5 位小数并去除连续重复点以压缩体积；
    4. 合并为一个 FeatureCollection，properties 仅保留 {province, city, adcode}。

输出：backend/data/geo/china_city.geojson

用法：
    cd backend
    uv run python scripts/build_china_geojson.py
（一次构建，产物随仓库分发，团队成员无需重复下载。）
"""

import json
import time
from pathlib import Path

import httpx

BASE = "https://geo.datav.aliyun.com/areas_v3/bound/{code}_full.json"
OUT = Path(__file__).resolve().parents[1] / "data" / "geo" / "china_city.geojson"

# 直辖市 + 港澳台：无市级下钻，直接用省级面，city = 省名
NO_CITY_LEVEL = {110000, 120000, 310000, 500000, 710000, 810000, 820000}

# 坐标精度：5 位小数约 1m，足够市级包含判断，同时显著缩小体积
NDIGITS = 5


def _round_ring(ring: list) -> list:
    """四舍五入坐标并去除连续重复点。"""
    out = []
    last = None
    for pt in ring:
        p = [round(pt[0], NDIGITS), round(pt[1], NDIGITS)]
        if p != last:
            out.append(p)
            last = p
    return out


def _round_geometry(geom: dict) -> dict:
    """对 Polygon / MultiPolygon 的所有环做精度压缩。"""
    t = geom["type"]
    coords = geom["coordinates"]
    if t == "Polygon":
        new = [_round_ring(r) for r in coords]
    elif t == "MultiPolygon":
        new = [[_round_ring(r) for r in poly] for poly in coords]
    else:
        raise ValueError(f"不支持的几何类型: {t}")
    return {"type": t, "coordinates": new}


def _get(url: str, verify: bool) -> httpx.Response:
    resp = httpx.get(url, timeout=30.0, verify=verify)
    resp.raise_for_status()
    return resp


def _fetch(code: int) -> dict:
    """下载并解析边界数据。

    默认开启 TLS 证书校验；仅当遇到证书类错误时（部分内网/代理会拦截 TLS）
    才降级为不校验重试，避免全局禁用带来的中间人风险。
    """
    url = BASE.format(code=code)
    verify = True
    for attempt in range(3):
        try:
            return _get(url, verify).json()
        except httpx.ConnectError as e:
            # 证书校验失败时降级为不校验（仅针对该受信任的公共数据源）
            if verify and "certificate" in str(e).lower():
                print(f"  [{code}] 证书校验失败，降级为不校验重试")
                verify = False
                continue
            print(f"  [{code}] 第 {attempt + 1} 次失败: {e}")
            time.sleep(1.5)
        except Exception as e:  # noqa: BLE001
            print(f"  [{code}] 第 {attempt + 1} 次失败: {e}")
            time.sleep(1.5)
    raise RuntimeError(f"下载失败: {code}")


def main() -> None:
    print("拉取全国省级列表 ...")
    provinces = _fetch(100000)
    prov_features = provinces["features"]
    print(f"省级区划 {len(prov_features)} 个")

    out_features = []
    for pf in prov_features:
        props = pf["properties"]
        adcode = props["adcode"]
        prov_name = props["name"]

        # 跳过非行政区要素（如“九段线” adcode="100000_JD"，为字符串且 level 为空）
        if not isinstance(adcode, int) or pf["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
            print(f"  跳过非行政区要素 adcode={adcode}")
            continue

        if adcode in NO_CITY_LEVEL:
            # 直辖市/港澳台：省即市
            out_features.append(
                {
                    "type": "Feature",
                    "properties": {"province": prov_name, "city": prov_name, "adcode": adcode},
                    "geometry": _round_geometry(pf["geometry"]),
                }
            )
            print(f"  {prov_name}（省即市）")
            continue

        print(f"  下钻 {prov_name} ...")
        cities = _fetch(adcode)
        for cf in cities["features"]:
            cp = cf["properties"]
            out_features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "province": prov_name,
                        "city": cp["name"],
                        "adcode": cp["adcode"],
                    },
                    "geometry": _round_geometry(cf["geometry"]),
                }
            )
        time.sleep(0.2)

    fc = {"type": "FeatureCollection", "features": out_features}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"\n完成：{len(out_features)} 个市级面 -> {OUT}")
    print(f"文件大小：{size_mb:.1f} MB")


if __name__ == "__main__":
    main()
