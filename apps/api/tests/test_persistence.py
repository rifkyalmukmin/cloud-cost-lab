"""Lifecycle persistence through Alembic-created tables."""

from datetime import date

from app.models.database import CostDailyAggregate, CostRecord
from app.persistence import bind_lifecycle
from app.services.cost_service import cost_service
from app.services.recommendation_service import recommendation_service
from app.services.savings_service import SavingsService
from sqlalchemy import Numeric, create_engine, inspect, text


def test_cost_money_columns_are_numeric_with_foreign_keys():
    assert isinstance(CostRecord.__table__.c.net_cost.type, Numeric)
    assert isinstance(CostRecord.__table__.c.cost.type, Numeric)
    referred = {fk.column.table.name for fk in CostRecord.__table__.c.project_id.foreign_keys}
    assert referred == {"projects"}
    index_columns = {tuple(index.columns.keys()) for index in CostRecord.__table__.indexes}
    assert ("usage_date",) in index_columns


def test_lifecycle_round_trip(tmp_path):
    database_url = f"sqlite:///{tmp_path}/lifecycle.db"
    first = SavingsService()
    first._recommendations_state.clear()
    first._audit_log.clear()
    bind_lifecycle(first, database_url)

    recommendation_id = recommendation_service.generate_recommendations()[0]["id"]
    first.approve(recommendation_id, "engineer")

    second = SavingsService()
    second._recommendations_state.clear()
    second._audit_log.clear()
    bind_lifecycle(second, database_url)

    state = second.get_recommendation_state(recommendation_id)
    assert state is not None
    assert state["status"] == "APPROVED"
    assert state["approved_by"] == "engineer"
    assert second.get_audit_log()[0]["actor"] == "engineer"

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert "recommendation_states" in inspector.get_table_names()
        cost_fks = inspector.get_foreign_keys("cost_records")
        assert any(fk["referred_table"] == "projects" for fk in cost_fks)
        usage_indexes = inspector.get_indexes("cost_records")
        assert any("usage_date" in index["column_names"] for index in usage_indexes)
    finally:
        cost_service.use_stored_aggregates(None)
        engine.dispose()
        first._persister.engine.dispose()
        second._persister.engine.dispose()


def test_cost_aggregates_survive_and_match_the_explorer(tmp_path):
    database_url = f"sqlite:///{tmp_path}/aggregates.db"
    service = SavingsService()
    service._recommendations_state.clear()
    service._audit_log.clear()
    engine = None
    try:
        bind_lifecycle(service, database_url)
        engine = create_engine(database_url)
        inspector = inspect(engine)
        assert "cost_daily_aggregates" in inspector.get_table_names()
        assert isinstance(CostDailyAggregate.__table__.c.net_cost.type, Numeric)
        assert isinstance(CostDailyAggregate.__table__.c.cost.type, Numeric)
        foreign_keys = inspector.get_foreign_keys("cost_daily_aggregates")
        referred = {fk["referred_table"] for fk in foreign_keys}
        assert {"projects", "services"} <= referred
        indexes = inspector.get_indexes("cost_daily_aggregates")
        assert any("usage_date" in index["column_names"] for index in indexes)

        with engine.connect() as connection:
            count = connection.execute(text("SELECT COUNT(*) FROM cost_daily_aggregates")).scalar()
        assert count and count > 0

        from_store = cost_service.get_summary(reference_date=date(2026, 8, 26))
        cost_service.use_stored_aggregates(None)
        from_lines = cost_service.get_summary(reference_date=date(2026, 8, 26))
        assert from_store["current_month_cost"] == from_lines["current_month_cost"]
        assert from_store["previous_month_cost"] == from_lines["previous_month_cost"]
        assert from_store["projected_month_cost"] == from_lines["projected_month_cost"]
    finally:
        cost_service.use_stored_aggregates(None)
        if engine is not None:
            engine.dispose()
        if getattr(service, "_persister", None) is not None:
            service._persister.engine.dispose()
