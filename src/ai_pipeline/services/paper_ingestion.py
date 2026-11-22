from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from ai_pipeline.crawlers.arxiv import PaperData


@dataclass
class NormalizedPaper:
    title: str
    normalized_title: str
    abstract: str
    authors: list[str]
    paper_url: str
    published_date: datetime
    source_name: str


def normalize_title(title: str) -> str:
    return " ".join(title.casefold().split())


def validate_paper_url(url: str) -> bool:
    parsed = urlparse(url)

    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"arxiv.org", "export.arxiv.org"}
        and parsed.path.startswith("/abs/")
    )


def normalize_paper(paper: PaperData) -> NormalizedPaper:

    title = " ".join(paper.title.split())

    original_url = paper.paper_url.strip()

    if not title:
        raise ValueError("Paper title is missing")

    if not validate_paper_url(original_url):
        raise ValueError(
            f"Invalid arXiv URL: {original_url}"
        )

    parsed = urlparse(original_url)

    # Convert arXiv HTTP URLs into canonical HTTPS URLs.
    paper_url = urlunparse(
        parsed._replace(
            scheme="https",
            netloc="arxiv.org",
            fragment="",
        )
    )

    return NormalizedPaper(
        title=title,
        normalized_title=normalize_title(title),
        abstract=paper.abstract.strip(),
        authors=paper.authors,
        paper_url=paper_url,
        published_date=paper.published_date,
        source_name=paper.source_name,
    )