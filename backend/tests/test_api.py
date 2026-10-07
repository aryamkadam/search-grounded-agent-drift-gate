from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def make_capture(
    *,
    capture_id,
    url="https://example.com/source",
    item_count=1,
):
    return {
        "capture_id": capture_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "search_context": {
            "query": "test query",
            "engine": "google",
        },
        "serpapi_metadata": {
            "search_id": f"search-{capture_id}",
            "status": "Success",
        },
        "raw_response": {},
        "normalized_evidence": {
            "surfaces": {
                "organic_results": {
                    "state": "present",
                    "item_count": item_count,
                }
            },
            "organic_results": (
                [
                    {
                        "identity_key": "url:https://example.com/source",
                        "position": 1,
                        "title": "Example Source",
                        "url": url,
                        "displayed_link": "example.com",
                        "snippet": "Original evidence",
                        "source": "Example",
                        "extra": {},
                    }
                ]
                if item_count == 1
                else []
            ),
            "ai_overview": None,
            "perspectives": [],
            "related_questions": [],
            "inline_images": [],
            "inline_videos": [],
            "additional_surfaces": {},
        },
    }


def make_answer(
    *,
    identity_key="url:https://example.com/source",
):
    return {
        "answer_id": "answer-1",
        "text": "The example claim is supported.",
        "claims": [
            {
                "claim_id": "claim-1",
                "text": "The example claim is true.",
                "importance": "important",
                "confidence": 0.9,
                "evidence_refs": [
                    {
                        "surface": "organic_results",
                        "identity_key": identity_key,
                        "relation": "supports",
                    }
                ],
            }
        ],
    }


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_evaluation_endpoint_returns_pass():
    payload = {
        "baseline_capture": make_capture(
            capture_id="baseline"
        ),
        "current_capture": make_capture(
            capture_id="current"
        ),
        "agent_answer": make_answer(),
    }

    response = client.post(
        "/v1/evaluations",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["evaluation_id"] == (
        "baseline:current:answer-1"
    )

    assert body["validation"]["valid"] is True

    assert body["result"]["gate"]["decision"] == "pass"


def test_evaluation_endpoint_returns_block_for_support_loss():
    payload = {
        "baseline_capture": make_capture(
            capture_id="baseline",
            item_count=1,
        ),
        "current_capture": make_capture(
            capture_id="current",
            item_count=0,
        ),
        "agent_answer": make_answer(),
    }

    response = client.post(
        "/v1/evaluations",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["validation"]["valid"] is True
    assert body["result"]["gate"]["decision"] == "block"
    assert body["result"]["gate"]["material_claim_ids"] == [
        "claim-1"
    ]


def test_evaluation_endpoint_returns_validation_failure():
    payload = {
        "baseline_capture": make_capture(
            capture_id="baseline"
        ),
        "current_capture": make_capture(
            capture_id="current"
        ),
        "agent_answer": make_answer(
            identity_key="url:https://example.com/missing"
        ),
    }

    response = client.post(
        "/v1/evaluations",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["validation"]["valid"] is False
    assert len(
        body["validation"]["unresolved_claim_links"]
    ) == 1
    assert body["result"] is None


def test_evaluation_endpoint_rejects_malformed_request():
    response = client.post(
        "/v1/evaluations",
        json={
            "baseline_capture": {},
            "current_capture": {},
            "agent_answer": {},
        },
    )

    assert response.status_code == 422
