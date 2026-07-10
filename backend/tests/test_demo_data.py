from app.demo_data import demo_chat, demo_navigation, demo_ops_actions
from app.models import NavigationRequest


def test_demo_navigation_avoids_congested_zone() -> None:
    response = demo_navigation(
        NavigationRequest(
            start_location="Section_214",
            destination_intent="nearest_restroom",
            step_free=True,
            language="en",
        )
    )

    assert response.step_free is True
    assert response.total_distance_m > 0
    assert response.avoid_reason is not None
    assert "Zone_4" in response.avoid_reason


def test_demo_chat_is_multilingual_and_grounded() -> None:
    response = demo_chat("Where is the nearest accessible restroom?", "es")

    assert response.detected_intent == "facilities"
    assert response.language == "es"
    assert response.sources[0]["type"] == "demo_knowledge_graph"


def test_demo_ops_actions_are_ranked_for_impact() -> None:
    actions = demo_ops_actions()

    assert actions[0].priority.value == "critical"
    assert actions[0].affected_population > actions[-1].affected_population
    assert "step-free" in actions[0].reasoning
