"""Scoring and action plan rules (pure functions; no API)."""

from app.e8.content import KEYS, REQUIREMENTS, STRATEGIES
from app.e8.scoring import action_plan, score


def answers_up_to(level, value="yes"):
    return {r.key: value for r in REQUIREMENTS if r.level <= level}


def levels(result):
    return {s.code: s.level for s in result.strategies}


def test_content_covers_all_strategies_and_levels():
    assert len(STRATEGIES) == 8 and len(REQUIREMENTS) == 152 and len(KEYS) == 126
    for s in STRATEGIES:
        assert {r.level for r in REQUIREMENTS if r.strategy == s.code} >= {1, 3}, s.code


def test_nothing_answered_is_level_zero():
    result = score({})
    assert result.overall_level == 0 and set(levels(result).values()) == {0}
    mfa = next(s for s in result.strategies if s.code == "MFA")
    assert (mfa.next_level, mfa.next_met, mfa.next_total) == (1, 0, 7)


def test_levels_are_cumulative():
    assert score(answers_up_to(1)).overall_level == 1
    assert score(answers_up_to(2)).overall_level == 2
    result = score(answers_up_to(3))
    assert result.overall_level == 3 and all(s.next_level is None for s in result.strategies)


def test_level_two_answers_without_level_one_score_zero():
    answers = {r.key: "yes" for r in REQUIREMENTS if r.level == 2}
    assert score(answers).overall_level == 0


def test_not_applicable_counts_as_met_but_partly_does_not():
    assert score(answers_up_to(1, "na")).overall_level == 1
    assert score(answers_up_to(1, "partly")).overall_level == 0


def test_overall_is_the_weakest_strategy():
    answers = answers_up_to(3)
    answers["BAK-1.04"] = "no"  # restores never tested
    result = score(answers)
    assert result.overall_level == 0 and levels(result)["BAK"] == 0 and levels(result)["MFA"] == 3


def test_shared_answer_counts_for_every_strategy():
    answers = answers_up_to(3)
    answers["LOGS-PROTECTED"] = "no"
    assert levels(score(answers)) == {"PA": 3, "PO": 3, "MFA": 1, "RAP": 1, "AC": 1, "MAC": 3, "UAH": 1, "BAK": 3}


def test_plan_puts_target_level_first_and_most_important_strategy_first():
    plan = action_plan({}, target_level=1)
    assert len(plan) == len(KEYS)
    in_target = [i for i in plan if i.in_target]
    assert {i.level for i in in_target} == {1} and plan[: len(in_target)] == in_target
    assert [i.key for i in plan[:2]] == ["MFA-1.01", "MFA-1.02"]
    assert [i.level for i in plan] == sorted(i.level for i in plan)


def test_plan_skips_met_and_lists_shared_items_once():
    plan = action_plan({"MFA-1.01": "yes", "PA-1.03": "na", "MFA-1.02": "partly"}, target_level=2)
    keys = [i.key for i in plan]
    assert "MFA-1.01" not in keys and "PA-1.03" not in keys
    assert next(i for i in plan if i.key == "MFA-1.02").answer == "partly"
    logs = [i for i in plan if i.key == "LOGS-PROTECTED"]
    assert len(logs) == 1 and logs[0].strategies == ["MFA", "RAP", "UAH", "AC"]


def test_plan_drops_requirements_replaced_below_the_target():
    replaced = {"PA-1.07", "PO-1.07", "MFA-2.04"}
    assert replaced <= {i.key for i in action_plan({}, target_level=2)}
    assert not replaced & {i.key for i in action_plan({}, target_level=3)}


def test_everything_met_means_an_empty_plan():
    assert action_plan(answers_up_to(3), target_level=3) == []
