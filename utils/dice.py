"""
범용 주사위 표현식 파서 & 굴림 엔진.

지원 문법 예시:
  1d20          - d20 한 번
  2d6+3         - 2d6 굴려 합산 후 +3
  4d6kh3        - 4d6 굴려서 높은 것 3개만 합산 (kh = keep highest)
  4d6kl1        - 낮은 것 1개만 (kl = keep lowest)
  1d20adv       - 1d20 두 번 굴려 높은 값 (어드밴티지)
  1d20dis       - 어드밴티지 반대 (디스어드밴티지)
  1d100         - 퍼센타일 (크툴루류 시스템에서 "언더" 판정에 사용)

파서는 여러 개의 dice term + 정수 보정치를 '+'/'-'로 연결한 수식을 처리한다.
예: "1d20+1d4+3" 도 가능.
"""

import random
import re
from dataclasses import dataclass, field

DICE_TERM_RE = re.compile(
    r"(?P<count>\d*)d(?P<sides>\d+)"
    r"(?P<mod>(kh|kl)\d+)?"
    r"(?P<adv>adv|dis)?",
    re.IGNORECASE,
)


@dataclass
class RollResult:
    expression: str
    total: int
    breakdown: str
    rolls: list = field(default_factory=list)


def _roll_dice_term(count: int, sides: int, keep_mode: str = None, keep_n: int = None, adv: str = None):
    """단일 NdM 항을 굴리고 (합계, 굴림 상세 문자열, 개별 굴림 리스트)를 반환."""
    if adv in ("adv", "dis"):
        # 어드밴티지/디스어드밴티지는 항상 1개 주사위를 2번 굴려서 비교
        r1, r2 = random.randint(1, sides), random.randint(1, sides)
        chosen = max(r1, r2) if adv == "adv" else min(r1, r2)
        detail = f"({r1}, {r2} -> {chosen})"
        return chosen, detail, [r1, r2]

    rolls = [random.randint(1, sides) for _ in range(count)]
    display_rolls = rolls.copy()

    if keep_mode and keep_n:
        sorted_rolls = sorted(rolls, reverse=(keep_mode == "kh"))
        kept = sorted_rolls[:keep_n]
        total = sum(kept)
        detail = f"({', '.join(map(str, display_rolls))} -> keep {keep_mode}{keep_n}: {kept})"
        return total, detail, rolls

    total = sum(rolls)
    detail = f"({', '.join(map(str, display_rolls))})" if len(rolls) > 1 else f"({rolls[0]})"
    return total, detail, rolls


def roll(expression: str) -> RollResult:
    """
    "1d20+5", "2d6+1d4-2", "1d20adv+3" 같은 수식을 받아 RollResult를 반환.
    """
    expr = expression.replace(" ", "").lower()
    if not expr:
        raise ValueError("빈 주사위 수식입니다.")

    # 항들을 부호 유지한 채로 분리 (첫 항 앞에 부호 없으면 +로 취급)
    tokens = re.findall(r"[+-]?[^+-]+", expr)
    if not tokens:
        raise ValueError(f"인식할 수 없는 수식입니다: {expression}")

    total = 0
    parts = []
    all_rolls = []

    for token in tokens:
        sign = -1 if token.startswith("-") else 1
        body = token.lstrip("+-")

        m = DICE_TERM_RE.fullmatch(body)
        if m:
            count = int(m.group("count")) if m.group("count") else 1
            sides = int(m.group("sides"))
            mod = m.group("mod")
            adv = m.group("adv")
            keep_mode = keep_n = None
            if mod:
                keep_mode = mod[:2]
                keep_n = int(mod[2:])

            if count > 100 or sides > 1000:
                raise ValueError("주사위 개수/면 수가 너무 큽니다 (최대 100d1000).")

            value, detail, rolls = _roll_dice_term(count, sides, keep_mode, keep_n, adv)
            all_rolls.extend(rolls)
            signed_value = sign * value
            total += signed_value
            sign_str = "-" if sign < 0 else ("+" if parts else "")
            parts.append(f"{sign_str}{body}{detail}")
        elif body.isdigit():
            value = int(body)
            total += sign * value
            sign_str = "-" if sign < 0 else ("+" if parts else "")
            parts.append(f"{sign_str}{value}")
        else:
            raise ValueError(f"인식할 수 없는 항입니다: {token}")

    breakdown = " ".join(parts)
    return RollResult(expression=expression, total=total, breakdown=breakdown, rolls=all_rolls)


def roll_under(expression_dice: str, target: int):
    """
    "1d100 <= 능력치" 같은 판정 방식을 쓰는 시스템(예: 크툴루, 인세인)을 위한 헬퍼.
    expression_dice 예: "1d100", "1d20"
    target: 성공 기준치
    반환: (RollResult, success: bool)
    """
    result = roll(expression_dice)
    success = result.total <= target
    return result, success
