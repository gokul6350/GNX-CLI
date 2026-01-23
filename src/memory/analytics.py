"""
Performance Analytics for Memory Operations.
Tracks retrieval times, hit rates, and tier statistics.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class RetrievalMetric:
    """Single retrieval operation metric."""
    timestamp: float
    query: str
    tier: str
    retrieval_time_ms: float
    results_count: int
    candidates_searched: int


class MemoryAnalytics:
    """
    Analytics system for memory operations.
    Tracks timing, hit rates, and provides performance reports.
    """
    
    def __init__(self, enable_live_logging: bool = True):
        self.enable_live_logging = enable_live_logging
        self.retrieval_metrics: List[RetrievalMetric] = []
        self.tier_stats: Dict[str, Dict] = {
            "HOT": {"hits": 0, "total_time_ms": 0},
            "WARM": {"hits": 0, "total_time_ms": 0},
            "COLD": {"hits": 0, "total_time_ms": 0},
        }
        self._start_time = time.time()
    
    def log_retrieval(
        self,
        query: str,
        tier: str,
        retrieval_time_ms: float,
        results_count: int,
        candidates_searched: int = 0,
    ):
        """Log a retrieval operation with timing."""
        metric = RetrievalMetric(
            timestamp=time.time(),
            query=query[:50] + "..." if len(query) > 50 else query,
            tier=tier,
            retrieval_time_ms=retrieval_time_ms,
            results_count=results_count,
            candidates_searched=candidates_searched,
        )
        self.retrieval_metrics.append(metric)
        
        # Update tier stats
        if tier in self.tier_stats:
            self.tier_stats[tier]["hits"] += 1
            self.tier_stats[tier]["total_time_ms"] += retrieval_time_ms
        
        # Live logging if enabled
        if self.enable_live_logging:
            self._print_retrieval(metric)
    
    def _print_retrieval(self, metric: RetrievalMetric):
        """Print retrieval info in real-time."""
        tier_colors = {"HOT": "red", "WARM": "yellow", "COLD": "blue"}
        color = tier_colors.get(metric.tier, "white")
        
        console.print(
            f"[dim]Memory[/dim] [{color}]{metric.tier}[/{color}] "
            f"[dim]->[/dim] {metric.results_count} results "
            f"[dim]in[/dim] [bold green]{metric.retrieval_time_ms:.2f}ms[/bold green] "
            f"[dim]({metric.candidates_searched} searched)[/dim]"
        )
    
    def get_average_retrieval_time(self, tier: Optional[str] = None) -> float:
        """Get average retrieval time in milliseconds."""
        if tier:
            stats = self.tier_stats.get(tier, {})
            hits = stats.get("hits", 0)
            if hits == 0:
                return 0.0
            return stats.get("total_time_ms", 0) / hits
        
        # Overall average
        if not self.retrieval_metrics:
            return 0.0
        total = sum(m.retrieval_time_ms for m in self.retrieval_metrics)
        return total / len(self.retrieval_metrics)
    
    def get_tier_hit_rate(self) -> Dict[str, float]:
        """Get hit rate percentage for each tier."""
        total = sum(s["hits"] for s in self.tier_stats.values())
        if total == 0:
            return {"HOT": 0, "WARM": 0, "COLD": 0}
        
        return {
            tier: (stats["hits"] / total) * 100
            for tier, stats in self.tier_stats.items()
        }
    
    def print_summary(self):
        """Print a summary table of analytics."""
        table = Table(title="Memory Analytics Summary")
        table.add_column("Tier", style="bold")
        table.add_column("Hits", justify="right")
        table.add_column("Avg Time (ms)", justify="right")
        table.add_column("Hit Rate", justify="right")
        
        hit_rates = self.get_tier_hit_rate()
        
        for tier, stats in self.tier_stats.items():
            avg_time = self.get_average_retrieval_time(tier)
            table.add_row(
                tier,
                str(stats["hits"]),
                f"{avg_time:.2f}",
                f"{hit_rates[tier]:.1f}%"
            )
        
        console.print(table)
        
        # Overall stats
        total_retrievals = len(self.retrieval_metrics)
        overall_avg = self.get_average_retrieval_time()
        uptime = time.time() - self._start_time
        
        console.print(f"\n[dim]Total Retrievals:[/dim] {total_retrievals}")
        console.print(f"[dim]Overall Avg Time:[/dim] {overall_avg:.2f}ms")
        console.print(f"[dim]Session Uptime:[/dim] {uptime:.1f}s")
    
    def reset(self):
        """Reset all analytics."""
        self.retrieval_metrics.clear()
        for tier in self.tier_stats:
            self.tier_stats[tier] = {"hits": 0, "total_time_ms": 0}
        self._start_time = time.time()
