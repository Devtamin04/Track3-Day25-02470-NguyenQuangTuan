"""Run report experiments without changing the submitted lab configuration."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gameday_lab.cache import CachingClient, SemanticCache
from gameday_lab.client import ResilientClient
from gameday_lab.sim.config import load_config
from gameday_lab.sim.engine import run_scenario


class UnsafeToolClient(ResilientClient):
    """Deliberately broken control client for the capability-filter experiment."""

    def ladder(self, task: str) -> list[str]:
        return list(self.order)


def run_resilient(label: str, scenarios: list[str], overrides: dict[str, object] | None = None,
                  unsafe_tools: bool = False) -> dict[str, object]:
    cfg = load_config()
    settings = deepcopy(cfg.client)
    for key, value in (overrides or {}).items():
        if key.startswith("breaker."):
            settings["breaker"][key.split(".", 1)[1]] = value  # type: ignore[index]
        else:
            settings[key] = value
    klass = UnsafeToolClient if unsafe_tools else ResilientClient
    client = klass(cfg.provider_infos(), cfg.fallback_order, settings, seed=25)
    return {key: run_scenario(cfg, key, client, 25).metrics() for key in scenarios}


def run_cache(label: str, overrides: dict[str, object]) -> dict[str, object]:
    cfg = load_config(scenarios_path="configs/scenarios_cache.yaml")
    cache_settings = deepcopy(cfg.cache)
    cache_settings.update(overrides)
    inner = ResilientClient(cfg.provider_infos(), cfg.fallback_order, cfg.client, seed=25)
    client = CachingClient(inner, SemanticCache(**cache_settings))
    return {"C1_faq_outage": run_scenario(cfg, "C1_faq_outage", client, 25).metrics()}


def main() -> None:
    results = {
        "budget_on": run_resilient("budget_on", ["G2_overload_storm", "G3_brownout"], {
            "breaker.min_calls": 1_000_000_000, "max_attempts_per_provider": 5,
        }),
        "budget_off": run_resilient("budget_off", ["G2_overload_storm", "G3_brownout"], {
            "breaker.min_calls": 1_000_000_000, "max_attempts_per_provider": 5,
            "retry_budget_ratio": 100.0, "retry_budget_max_tokens": 1_000_000_000.0,
            "retry_budget_min_per_s": 1_000_000.0,
        }),
        "timeout_30": run_resilient("timeout_30", ["G4_slow_region", "G6_provider_outage"], {
            "attempt_timeout_s": 30.0,
        }),
        "no_tool_filter": run_resilient("no_tool_filter", ["G6_provider_outage"], unsafe_tools=True),
        "cache_threshold_080": run_cache("cache_threshold_080", {"similarity_threshold": 0.80}),
        "cache_threshold_097": run_cache("cache_threshold_097", {"similarity_threshold": 0.97}),
        "cache_ttl_060": run_cache("cache_ttl_060", {"ttl_s": 60}),
        "cache_ttl_300": run_cache("cache_ttl_300", {"ttl_s": 300}),
        "cache_no_stale": run_cache("cache_no_stale", {"max_stale_s": 0}),
    }
    out = Path("reports/bonus.json")
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
