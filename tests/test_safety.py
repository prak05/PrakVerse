from prakverse.safety import ActionRisk, SafetyPolicy, requires_confirmation


def test_full_auto_does_not_require_confirmation() -> None:
    policy = SafetyPolicy()

    assert policy.execution_mode == "full_auto"
    assert not any(policy.requires_confirmation(risk) for risk in ActionRisk)
    assert not requires_confirmation(ActionRisk.DESTRUCTIVE)
