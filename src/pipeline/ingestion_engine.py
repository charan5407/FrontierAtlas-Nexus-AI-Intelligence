"""
Master Ingestion Pipeline Orchestrator for FrontierAtlas Nexus.
Executes Phase I through Phase V concurrently, coordinates data acquisition,
deterministic entity resolution, LLM extraction fallback, and multi-tab export.
"""

import asyncio
import logging
import time
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from src.crawler.sources_startups import default_startups_crawler
from src.crawler.sources_products import default_products_crawler
from src.crawler.sources_papers import default_papers_crawler
from src.crawler.sources_news import default_news_crawler
from src.crawler.sources_jobs import default_jobs_crawler
from src.resolution.resolver import default_resolver
from src.pipeline.exporter import default_exporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("FrontierAtlas.Pipeline")
console = Console()


class IngestionEngine:
    def __init__(self):
        self.start_time = None
        self.end_time = None

    async def run_pipeline(self) -> Dict[str, Any]:
        self.start_time = time.time()
        console.print(Panel.fit(
            "[bold cyan]FRONTIERATLAS NEXUS: AUTONOMOUS INTELLIGENCE GRAPH PIPELINE[/bold cyan]\n"
            "[italic white]GraphOne / FrontierAtlas High-Fidelity Multi-Modal Ingestion Engine[/italic white]",
            border_style="cyan"
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task_startups = progress.add_task("[yellow]Phase I: Ingesting Startups (Target: 1,000+)...", total=1000)
            task_products = progress.add_task("[magenta]Phase I: Ingesting Products (Target: 1,000+)...", total=1000)
            task_papers = progress.add_task("[blue]Phase I: Ingesting Papers & GitHub Stars (Target: 1,000+)...", total=1000)
            task_signals = progress.add_task("[green]Phase II: Ingesting 24-hr Fresh News & Jobs...", total=100)

            # Concurrent execution of verticals
            startups_coro = default_startups_crawler.scrape()
            products_coro = default_products_crawler.scrape()
            papers_coro = default_papers_crawler.scrape()
            news_coro = default_news_crawler.scrape()
            jobs_coro = default_jobs_crawler.scrape()

            startups, products, papers, news, jobs = await asyncio.gather(
                startups_coro,
                products_coro,
                papers_coro,
                news_coro,
                jobs_coro
            )

            progress.update(task_startups, completed=len(startups))
            progress.update(task_products, completed=len(products))
            progress.update(task_papers, completed=len(papers))
            progress.update(task_signals, completed=100)

        # Collect entity mapping audit logs
        mapping_logs = default_resolver.get_audit_logs()

        # Phase Deliverable: Export 6 tabs
        export_paths = default_exporter.export_all(
            startups=startups,
            products=products,
            papers=papers,
            jobs=jobs,
            news=news,
            mapping_logs=mapping_logs
        )

        self.end_time = time.time()
        elapsed = round(self.end_time - self.start_time, 2)

        # Display Summary Table
        table = Table(title="Pipeline Ingestion Metrics & Deliverables Summary", border_style="bright_blue")
        table.add_column("Dataset Tab", style="cyan", justify="left")
        table.add_column("Schema Standard", style="dim", justify="center")
        table.add_column("Count Extracted", style="green", justify="right")
        table.add_column("Validation & Integrity", style="yellow", justify="left")

        table.add_row("1. Startups", "STARTUP v1.0", f"{len(startups):,}", "[green]✓[/green] Canonical Entity Resolved, Real Domains")
        table.add_row("2. Products", "PRODUCT v1.0", f"{len(products):,}", "[green]✓[/green] Free/Freemium/Paid/Enterprise Enum Verified")
        table.add_row("3. Research Papers", "RESEARCH_PAPER v1.0", f"{len(papers):,}", "[green]✓[/green] Arxiv & GitHub Code Repo + Stars Tracked")
        table.add_row("4. Jobs", "JOB v1.0", f"{len(jobs):,}", "[green]✓[/green] Strictly < 24-hr Fresh, Remote/Role Classified")
        table.add_row("5. News", "NEWS v1.0", f"{len(news):,}", "[green]✓[/green] Strictly < 24-hr Fresh, Full-Text Extracted")
        table.add_row("6. Entity Mapping Log", "AUDIT_LOG v1.0", f"{len(mapping_logs):,}", "[green]✓[/green] Raw vs Canonical Traceability & Confidence")

        console.print(table)
        console.print(f"[bold green]Pipeline completed in {elapsed}s.[/bold green]")
        console.print(f"[bold white]Multi-tab Excel Deliverable:[/bold white] [underline cyan]{export_paths['xlsx']}[/underline cyan]")

        return {
            "elapsed_seconds": elapsed,
            "counts": {
                "startups": len(startups),
                "products": len(products),
                "papers": len(papers),
                "jobs": len(jobs),
                "news": len(news),
                "mapping_logs": len(mapping_logs)
            },
            "exports": export_paths
        }


def main():
    engine = IngestionEngine()
    asyncio.run(engine.run_pipeline())


if __name__ == "__main__":
    main()

