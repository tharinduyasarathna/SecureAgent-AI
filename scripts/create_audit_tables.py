
from sqlalchemy import inspect

from apps.api.app.database import Base, engine
from apps.api.app.models import User
from apps.api.agents.audit_models import (
    AgentInvestigation,
    AgentAuditEvent,
)


def main():
    inspector = inspect(engine)

    existing = set(inspector.get_table_names())

    required = {
        "agent_investigations",
        "agent_audit_events",
    }

    print("Existing audit tables:", existing & required)

    Base.metadata.create_all(
        bind=engine,
        tables=[
            AgentInvestigation.__table__,
            AgentAuditEvent.__table__,
        ],
        checkfirst=True,
    )

    inspector = inspect(engine)
    current = set(inspector.get_table_names())

    for table in sorted(required):
        if table not in current:
            raise RuntimeError(
                f"Failed to create table: {table}"
            )

        print(f"Verified: {table}")

    print("Audit table initialization completed.")


if __name__ == "__main__":
    main()
