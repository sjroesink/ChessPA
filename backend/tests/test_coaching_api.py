import uuid

from app.models.user import User
from app.models.coaching_insight import CoachingInsight
from app.auth.dependencies import set_session


async def _setup(test_db_factory):
    async with test_db_factory() as db:
        user = User(username="coach_api", auth_provider="google", email="coachapi@test.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        insight = CoachingInsight(
            user_id=user.id,
            type="weakness",
            title="Test zwakte",
            description="Je maakt te veel blunders.",
            severity="high",
            related_games=[],
            model_version="test-model",
        )
        db.add(insight)
        await db.commit()
        await db.refresh(insight)

    set_session("coaching-test", user.id)
    return user, insight


async def test_list_insights(client, app, test_db_factory, override_db):
    user, insight = await _setup(test_db_factory)
    response = await client.get("/api/coaching/insights", cookies={"chesspa_session": "coaching-test"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "weakness"
    assert data[0]["title"] == "Test zwakte"


async def test_get_insight_detail(client, app, test_db_factory, override_db):
    user, insight = await _setup(test_db_factory)
    response = await client.get(
        f"/api/coaching/insights/{insight.id}",
        cookies={"chesspa_session": "coaching-test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Je maakt te veel blunders."


async def test_get_insight_not_found(client, app, test_db_factory, override_db):
    user, insight = await _setup(test_db_factory)
    fake = str(uuid.uuid4())
    response = await client.get(
        f"/api/coaching/insights/{fake}",
        cookies={"chesspa_session": "coaching-test"},
    )
    assert response.status_code == 404


async def test_weaknesses_empty_for_new_user(client, app, test_db_factory, override_db):
    async with test_db_factory() as db:
        user = User(username="weak_empty", auth_provider="google", email="weak@test.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    set_session("weak-empty-test", user.id)
    response = await client.get(
        "/api/coaching/weaknesses",
        cookies={"chesspa_session": "weak-empty-test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["games_analyzed"] == 0
    assert data["per_opening"] == []
    assert data["per_phase"] == {}
    assert data["top_motifs"] == []
