from backend.app.gate import evaluate_drift_gate
from backend.app.impact import ClaimImpact


def make_impact(
    claim_id="claim-1",
    importance="important",
    affected=False,
    material=False,
    severity="none",
    dependency_status="intact",
):
    return ClaimImpact(
        claim_id=claim_id,
        importance=importance,
        affected=affected,
        material=material,
        severity=severity,
        dependency_status=dependency_status,
    )


def test_no_affected_claims_passes():
    result = evaluate_drift_gate(
        [
            make_impact(),
        ]
    )

    assert result.decision == "pass"
    assert result.severity == "none"
    assert result.affected_claim_ids == []
    assert result.material_claim_ids == []
    assert result.reasons == []


def test_material_important_claim_blocks():
    result = evaluate_drift_gate(
        [
            make_impact(
                claim_id="claim-1",
                importance="important",
                affected=True,
                material=True,
                severity="high",
                dependency_status="lost",
            )
        ]
    )

    assert result.decision == "block"
    assert result.severity == "high"
    assert result.affected_claim_ids == ["claim-1"]
    assert result.material_claim_ids == ["claim-1"]
    assert len(result.reasons) == 1
    assert "claim-1" in result.reasons[0]


def test_material_critical_claim_blocks():
    result = evaluate_drift_gate(
        [
            make_impact(
                claim_id="claim-critical",
                importance="critical",
                affected=True,
                material=True,
                severity="high",
                dependency_status="lost",
            )
        ]
    )

    assert result.decision == "block"
    assert result.severity == "high"
    assert result.affected_claim_ids == [
        "claim-critical"
    ]
    assert result.material_claim_ids == [
        "claim-critical"
    ]
    assert len(result.reasons) == 1
    assert "claim-critical" in result.reasons[0]


def test_partial_support_loss_warns():
    result = evaluate_drift_gate(
        [
            make_impact(
                claim_id="claim-1",
                importance="important",
                affected=True,
                material=False,
                severity="high",
                dependency_status="partially_degraded",
            )
        ]
    )

    assert result.decision == "warn"
    assert result.severity == "high"
    assert result.affected_claim_ids == ["claim-1"]
    assert result.material_claim_ids == []
    assert len(result.reasons) == 1
    assert "claim-1" in result.reasons[0]


def test_supporting_evidence_change_warns():
    result = evaluate_drift_gate(
        [
            make_impact(
                claim_id="claim-1",
                importance="important",
                affected=True,
                material=False,
                severity="medium",
                dependency_status="changed",
            )
        ]
    )

    assert result.decision == "warn"
    assert result.severity == "medium"
    assert result.affected_claim_ids == ["claim-1"]
    assert result.material_claim_ids == []
    assert len(result.reasons) == 1
    assert "claim-1" in result.reasons[0]


def test_contextual_complete_support_loss_passes():
    result = evaluate_drift_gate(
        [
            make_impact(
                claim_id="claim-context",
                importance="contextual",
                affected=True,
                material=False,
                severity="high",
                dependency_status="lost",
            )
        ]
    )

    assert result.decision == "pass"
    assert result.severity == "none"
    assert result.affected_claim_ids == [
        "claim-context"
    ]
    assert result.material_claim_ids == []
    assert result.reasons == []


def test_contradicting_evidence_change_warns():
    result = evaluate_drift_gate(
        [
            make_impact(
                claim_id="claim-1",
                importance="important",
                affected=True,
                material=False,
                severity="medium",
                dependency_status="context_changed",
            )
        ]
    )

    assert result.decision == "warn"
    assert result.severity == "medium"
    assert result.affected_claim_ids == ["claim-1"]
    assert result.material_claim_ids == []
    assert len(result.reasons) == 1
    assert "claim-1" in result.reasons[0]


def test_unaffected_claim_does_not_warn():
    result = evaluate_drift_gate(
        [
            make_impact(
                claim_id="claim-1",
                affected=False,
                material=False,
                severity="none",
                dependency_status="intact",
            )
        ]
    )

    assert result.decision == "pass"
    assert result.severity == "none"
    assert result.affected_claim_ids == []
    assert result.material_claim_ids == []
    assert result.reasons == []


def test_material_claim_blocks_even_with_other_warnings():
    result = evaluate_drift_gate(
        [
            make_impact(
                claim_id="claim-warning",
                importance="important",
                affected=True,
                material=False,
                severity="medium",
                dependency_status="changed",
            ),
            make_impact(
                claim_id="claim-block",
                importance="critical",
                affected=True,
                material=True,
                severity="high",
                dependency_status="lost",
            ),
        ]
    )

    assert result.decision == "block"
    assert result.severity == "high"

    assert result.affected_claim_ids == [
        "claim-warning",
        "claim-block",
    ]

    assert result.material_claim_ids == [
        "claim-block",
    ]

    # Only the material claim contributes to BLOCK reasons.
    assert len(result.reasons) == 1
    assert "claim-block" in result.reasons[0]


def test_multiple_material_claims_all_appear_in_result():
    result = evaluate_drift_gate(
        [
            make_impact(
                claim_id="claim-1",
                importance="critical",
                affected=True,
                material=True,
                severity="high",
                dependency_status="lost",
            ),
            make_impact(
                claim_id="claim-2",
                importance="important",
                affected=True,
                material=True,
                severity="high",
                dependency_status="lost",
            ),
        ]
    )

    assert result.decision == "block"
    assert result.severity == "high"

    assert result.affected_claim_ids == [
        "claim-1",
        "claim-2",
    ]

    assert result.material_claim_ids == [
        "claim-1",
        "claim-2",
    ]

    # One blocking reason per material claim.
    assert len(result.reasons) == 2
    assert "claim-1" in result.reasons[0]
    assert "claim-2" in result.reasons[1]
