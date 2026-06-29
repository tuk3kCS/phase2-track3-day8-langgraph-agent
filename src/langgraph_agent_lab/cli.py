"""CLI for the lab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml  # type: ignore
from langchain_core.runnables import RunnableConfig

from .graph import build_graph
from .metrics import MetricsReport, metric_from_state, summarize_metrics, write_metrics
from .persistence import build_checkpointer
from .report import write_report
from .scenarios import load_scenarios
from .state import initial_state

app = typer.Typer(no_args_is_help=True)


@app.command("run-scenarios")
def run_scenarios(
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
) -> None:
    """Run all grading scenarios and write metrics JSON."""
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    scenarios = load_scenarios(cfg["scenarios_path"])
    checkpointer = build_checkpointer(cfg.get("checkpointer", "memory"), cfg.get("database_url"))
    graph = build_graph(checkpointer=checkpointer)
    metrics = []
    traces = []
    for scenario in scenarios:
        state = initial_state(scenario)
        run_config: RunnableConfig = {"configurable": {"thread_id": state["thread_id"]}}
        final_state = graph.invoke(state, config=run_config)
        
        # Resume loop in case of interrupts
        while True:
            state_info = graph.get_state(run_config)
            if not state_info.next:
                break
            from langgraph.types import Command
            resume_val = {
                "approved": True,
                "reviewer": "cli-auto",
                "comment": "Auto-approved by CLI",
            }
            final_state = graph.invoke(
                Command(resume=resume_val),
                config=run_config
            )
            
        scenario_metric = metric_from_state(
            final_state,
            scenario.expected_route.value,
            scenario.requires_approval,
        )
        metrics.append(scenario_metric)
        
        # Collect trace info for JSON export
        traces.append({
            "scenario_id": scenario.id,
            "query": scenario.query,
            "expected_route": scenario.expected_route.value,
            "actual_route": final_state.get("route"),
            "success": scenario_metric.success,
            "attempts": final_state.get("attempt", 0),
            "max_attempts": final_state.get("max_attempts"),
            "messages": final_state.get("messages", []),
            "tool_results": final_state.get("tool_results", []),
            "errors": final_state.get("errors", []),
            "events": final_state.get("events", []),
            "proposed_action": final_state.get("proposed_action"),
            "approval": final_state.get("approval"),
            "final_answer": final_state.get("final_answer"),
            "pending_question": final_state.get("pending_question"),
        })

    report = summarize_metrics(metrics)
    write_metrics(report, output)
    
    # Save traces to execution_traces.json
    traces_path = output.parent / "execution_traces.json"
    traces_json = json.dumps(traces, indent=2, ensure_ascii=False)
    traces_path.write_text(traces_json, encoding="utf-8")
    
    # Inject real traces into report.html
    report_html_path = Path("report.html")
    if report_html_path.exists():
        html_content = report_html_path.read_text(encoding="utf-8")
        start_tag = '<script id="real-traces-data" type="application/json">'
        end_tag = '</script>'
        if start_tag in html_content and end_tag in html_content:
            before, rest = html_content.split(start_tag, 1)
            _, after = rest.split(end_tag, 1)
            new_html = f"{before}{start_tag}\n{traces_json}\n{end_tag}{after}"
            report_html_path.write_text(new_html, encoding="utf-8")
        
    if cfg.get("report_path"):
        write_report(report, cfg["report_path"])
    typer.echo(f"Wrote metrics to {output}, traces to {traces_path}, and updated report.html")


@app.command("validate-metrics")
def validate_metrics(metrics: Annotated[Path, typer.Option("--metrics")]) -> None:
    """Validate metrics JSON schema for grading."""
    payload = json.loads(metrics.read_text(encoding="utf-8"))
    report = MetricsReport.model_validate(payload)
    if report.total_scenarios < 6:
        raise typer.BadParameter("Expected at least 6 scenarios")
    typer.echo(f"Metrics valid. success_rate={report.success_rate:.2%}")


if __name__ == "__main__":
    app()
