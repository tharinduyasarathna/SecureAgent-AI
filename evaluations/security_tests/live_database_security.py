
import asyncio
import json
from uuid import UUID

from sqlalchemy import select

from apps.api.app.database import SessionLocal
from apps.api.rag.models import RAGDocument
from apps.api.rag.retriever import retrieve_chunks
from apps.api.agents.audit_models import AgentInvestigation
from apps.api.agents.audit_service import AuditService


async def main():
    results = {}

    with SessionLocal() as db:
        # Select an existing synthetic test document
        # belonging to User 2.
        document = db.execute(
            select(RAGDocument)
            .where(RAGDocument.owner_id == 2)
            .order_by(RAGDocument.id)
        ).scalars().first()

        if document is None:
            raise RuntimeError(
                "No indexed test document owned by User 2"
            )

        document_id = document.id

        # DB-001: Cross-user document access
        unauthorized = await retrieve_chunks(
            db=db,
            user_id=1,
            query="Suspicious authentication activity",
            top_k=3,
            document_id=document_id,
        )

        results["DB-001"] = len(unauthorized) == 0

        # DB-002: Authorized document access
        authorized = await retrieve_chunks(
            db=db,
            user_id=2,
            query="Suspicious authentication activity",
            top_k=3,
            document_id=document_id,
        )

        results["DB-002"] = len(authorized) > 0

        # Locate an existing completed audit record
        # belonging to User 2.
        investigation = db.execute(
            select(AgentInvestigation)
            .where(
                AgentInvestigation.user_id == 2,
                AgentInvestigation.status == "completed",
            )
            .order_by(
                AgentInvestigation.started_at.desc()
            )
        ).scalars().first()

        if investigation is None:
            raise RuntimeError(
                "No completed User 2 audit record found"
            )

        investigation_id = investigation.id

    audit = AuditService()

    # DB-003: Cross-user audit access
    unauthorized_history = audit.get_history(
        investigation_id=investigation_id,
        user_id=1,
    )

    authorized_history = audit.get_history(
        investigation_id=investigation_id,
        user_id=2,
    )

    results["DB-003"] = (
        unauthorized_history is None
        and authorized_history is not None
    )

    print("\n=== DATABASE SECURITY RESULTS ===")

    for test_id, passed in results.items():
        print(
            f"{test_id}: "
            f"{'PASSED' if passed else 'FAILED'}"
        )

    summary = {
        "total": len(results),
        "passed": sum(results.values()),
        "failed": sum(not x for x in results.values()),
    }

    print(json.dumps(summary, indent=2))

    assert all(results.values()), (
        "Database security verification failed"
    )

    print("\nDATABASE SECURITY VERIFICATION: PASSED")


if __name__ == "__main__":
    asyncio.run(main())
