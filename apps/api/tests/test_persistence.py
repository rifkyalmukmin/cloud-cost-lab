"""Lifecycle persistence through Alembic-created tables."""

from app.models.database import CostRecord
from app.persistence import bind_lifecycle
from app.services.recommendation_service import recommendation_service
from app.services.savings_service import SavingsService
from sqlalchemy import Numeric, create_engine, inspect


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
        engine.dispose()
        first._persister.engine.dispose()
        second._persister.engine.dispose()
