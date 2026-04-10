"""Seed script for inserting initial findings.

This script is executed as part of the deployment process to ensure
there are baseline findings available for fine‑tuning. In Phase 1 this
script does nothing; it will be implemented in a later phase when the
models and database infrastructure are in place.
"""

import asyncio


async def main() -> None:
    """Insert the initial seed findings into the database.

    This function is idempotent: if any seed findings already exist,
    it exits without modifying the database.  A dedicated session is
    created to hold the seed findings.  Each finding is flagged with
    ``is_seed = True`` so that the application can distinguish seed
    data from user‑generated findings.  All fields other than the
    label, text and classification are left empty.
    """
    from ..database import async_session_factory
    if async_session_factory is None:
        print("Database is not configured; skipping seed insertion.")
        return
    from ..models import Session as SessionModel
    from ..models import Finding as FindingModel
    from sqlalchemy import select
    import datetime
    async with async_session_factory() as db:
        # Check if seeds already exist
        res = await db.execute(
            select(FindingModel).where(FindingModel.is_seed.is_(True))
        )
        existing = res.scalars().first()
        if existing:
            print("Seed findings already inserted. Skipping.")
            return
        # Create a session to contain seed findings
        seed_session = SessionModel(
            study_name="Seed Findings", study_type="Non-GLP", draft_maturity="Final", priority_notes=None, status="complete"
        )
        db.add(seed_session)
        await db.flush()  # generate session ID
        # Define a list of seed findings
        seeds = [
            {
                "finding_label": f"S-{i:03d}",
                "original_text": f"This is example finding {i} to seed the model.",
                "category": "General",
                "comment": "Example comment for seed finding.",
                "recommendation": "No action required for seed data.",
                "severity": "Minor",
                "source_reference": "N/A",
            }
            for i in range(1, 21)
        ]
        for seed in seeds:
            f = FindingModel(
                session_id=seed_session.id,
                chunk_id=None,
                document_id=None,
                finding_label=seed["finding_label"],
                original_text=seed["original_text"],
                category=seed["category"],
                comment=seed["comment"],
                recommendation=seed["recommendation"],
                severity=seed["severity"],
                source_reference=seed["source_reference"],
                confidence="standard",
                confirmed_correct=True,
                confirmed_at=datetime.datetime.utcnow(),
                is_seed=True,
            )
            db.add(f)
        await db.commit()
        print(f"Inserted {len(seeds)} seed findings into session {seed_session.id}")


if __name__ == "__main__":
    asyncio.run(main())