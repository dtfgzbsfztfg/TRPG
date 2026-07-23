"""
systems/*.yaml 파일을 읽어서 "시스템 프로필"로 사용.
새 TRPG 시스템을 추가하려면 systems/ 폴더에 yaml 파일만 추가하면 됨 (코드 수정 불필요).
"""

import os
import yaml

SYSTEMS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "systems")

_cache: dict[str, dict] = {}


def load_system(name: str) -> dict:
    if name in _cache:
        return _cache[name]

    path = os.path.join(SYSTEMS_DIR, f"{name}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"시스템 프로필을 찾을 수 없습니다: {name} ({path})")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _cache[name] = data
    return data


def list_systems() -> list[str]:
    return [
        f[:-5] for f in os.listdir(SYSTEMS_DIR)
        if f.endswith(".yaml")
    ]


def default_stats(system_name: str) -> dict:
    """시스템 프로필의 능력치 목록 기준으로 기본값(0 또는 지정값) 딕셔너리 생성."""
    profile = load_system(system_name)
    stats = {}
    for stat in profile.get("stats", []):
        stats[stat["key"]] = stat.get("default", 0)
    return stats
