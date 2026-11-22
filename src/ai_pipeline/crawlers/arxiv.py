import asyncio
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

from ai_pipeline.crawlers.http_client import AsyncHTTPClient


ARXIV_API = "https://export.arxiv.org/api/query"

ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass
class PaperData:
    title: str
    abstract: str
    authors: list[str]
    paper_url: str
    published_date: datetime
    source_name: str = "arxiv"


def parse_arxiv_xml(xml_text: str) -> list[PaperData]:
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall(f"{ATOM}entry"):
        title = " ".join(
            (entry.findtext(f"{ATOM}title") or "").split()
        )

        abstract = " ".join(
            (entry.findtext(f"{ATOM}summary") or "").split()
        )

        paper_url = entry.findtext(f"{ATOM}id") or ""

        published_text = entry.findtext(f"{ATOM}published")

        if not title or not paper_url or not published_text:
            continue

        published_date = datetime.fromisoformat(
            published_text.replace("Z", "+00:00")
        )

        authors = [
            author.findtext(f"{ATOM}name")
            for author in entry.findall(f"{ATOM}author")
        ]

        authors = [name for name in authors if name]

        papers.append(
            PaperData(
                title=title,
                abstract=abstract,
                authors=authors,
                paper_url=paper_url,
                published_date=published_date,
            )
        )

    return papers


async def fetch_arxiv_papers(
    max_results: int = 5,
    query: str = "cat:cs.AI",
) -> list[PaperData]:
    if not 1 <= max_results <= 100:
        raise ValueError("max_results must be between 1 and 100")

    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    async with AsyncHTTPClient() as client:
        response = await client.get(
            ARXIV_API,
            params=params,
        )

    return parse_arxiv_xml(response.text)


if __name__ == "__main__":
    async def main():
        papers = await fetch_arxiv_papers(max_results=5)

        for paper in papers:
            print(f"\nTitle: {paper.title}")
            print(f"Authors: {', '.join(paper.authors)}")
            print(f"Published: {paper.published_date}")
            print(f"URL: {paper.paper_url}")

    asyncio.run(main())