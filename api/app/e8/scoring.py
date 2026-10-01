"""Essential Eight scoring and action plan. Pure functions over {answer key: answer}.

ASD's rule: a strategy is at maturity level N only when every requirement of levels 1..N is
met; there is no partial credit and no averaging across strategies. "Not applicable" counts as
met, "partly" and unanswered count as not met. The organisation's overall level is the lowest
strategy level, because one weak strategy is enough to get in.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from .content import MAX_LEVEL, REQUIREMENTS, STRATEGIES, STRATEGY_BY_CODE, Requirement

MET = frozenset({"yes", "na"})
# position of each answer key in the content, to keep plan items in ASD's order
_ORDER: dict[str, int] = {}
for _i, _r in enumerate(REQUIREMENTS):
    _ORDER.setdefault(_r.key, _i)


@dataclass
class StrategyScore:
    code: str
    level: int
    next_level: int | None  # None once at Maturity Level Three
    next_met: int  # requirements met for next_level
    next_total: int


@dataclass
class Score:
    overall_level: int
    strategies: list[StrategyScore]


@dataclass
class PlanItem:
    key: str
    level: int  # lowest maturity level that needs it
    strategies: list[str]  # most important first
    title: str
    text: str
    effort: str
    answer: str | None
    in_target: bool


def _met(answers: Mapping[str, str], r: Requirement) -> bool:
    return answers.get(r.key) in MET


def score(answers: Mapping[str, str]) -> Score:
    result = []
    for s in STRATEGIES:
        reqs = [r for r in REQUIREMENTS if r.strategy == s.code]
        level = 0
        while level < MAX_LEVEL and all(_met(answers, r) for r in reqs if r.applies_at(level + 1)):
            level += 1
        if level == MAX_LEVEL:
            result.append(StrategyScore(s.code, level, None, 0, 0))
        else:
            needed = [r for r in reqs if r.applies_at(level + 1)]
            met = sum(_met(answers, r) for r in needed)
            result.append(StrategyScore(s.code, level, level + 1, met, len(needed)))
    return Score(overall_level=min(s.level for s in result), strategies=result)


def action_plan(answers: Mapping[str, str], target_level: int) -> list[PlanItem]:
    """Unmet requirements, one item per answer key: those needed for the target level first
    (lowest level, then the most important strategy), then the ones beyond the target.
    Requirements that a stricter one replaces below or at the target level are left out."""
    items: dict[str, PlanItem] = {}
    for r in REQUIREMENTS:
        if _met(answers, r) or (r.until is not None and r.until < target_level):
            continue
        item = items.get(r.key)
        if item is None:
            items[r.key] = PlanItem(r.key, r.level, [r.strategy], r.title, r.text, r.effort,
                                    answers.get(r.key), r.level <= target_level)
        else:
            item.level = min(item.level, r.level)
            item.in_target = item.level <= target_level
            item.strategies.append(r.strategy)
    for item in items.values():
        item.strategies.sort(key=lambda c: STRATEGY_BY_CODE[c].priority)
    return sorted(
        items.values(),
        key=lambda i: (not i.in_target, i.level, STRATEGY_BY_CODE[i.strategies[0]].priority, _ORDER[i.key]),
    )

