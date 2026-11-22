import asyncio

from sqlalchemy import select

from ai_pipeline.crawlers.arxiv import fetch_arxiv_papers
from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import ResearchPaper
from ai_pipeline.services.paper_ingestion import normalize_paper


async def collect_and_store(max_results: int = 5):
    print(f"\nFetching up to {max_results} papers from arXiv...")

    papers = await fetch_arxiv_papers(max_results=max_results)

    print(f"\nSuccessfully fetched {len(papers)} papers.\n")

    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        for index, paper in enumerate(papers, start=1):
            print(f"\n--- Processing Paper {index} ---")
            print(f"Title: {paper.title}")
            print(f"Original URL: {paper.paper_url}")

            try:
                normalized = normalize_paper(paper)

                print(f"Normalized URL: {normalized.paper_url}")

            except ValueError as exc:
                print(f"[SKIPPED] Validation failed: {exc}")
                skipped += 1
                continue

            result = await session.execute(
                select(ResearchPaper).where(
                    ResearchPaper.paper_url == normalized.paper_url
                )
            )

            existing = result.scalar_one_or_none()

            if existing is not None:
                print("[SKIPPED] Paper already exists in database")
                skipped += 1
                continue

            record = ResearchPaper(
                title=normalized.title,
                normalized_title=normalized.normalized_title,
                abstract=normalized.abstract,
                authors=normalized.authors,
                paper_url=normalized.paper_url,
                published_date=normalized.published_date,
                source_name=normalized.source_name,
            )

            session.add(record)
            inserted += 1

            print("[INSERTED] Paper added to database session")

        await session.commit()

    print("\nCOLLECTION SUMMARY")
    print("=" * 40)
    print(f"Fetched:  {len(papers)}")
    print(f"Inserted: {inserted}")
    print(f"Skipped:  {skipped}")
    print("=" * 40)


if __name__ == "__main__":
    asyncio.run(collect_and_store(max_results=5))
