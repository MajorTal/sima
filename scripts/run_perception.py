#!/usr/bin/env python3
"""
Run the perception module and display its output.

Demonstrates how sensory data feeds into perception and what
structured representation Sima builds from it.
"""

import asyncio
import json
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

# Add project to path
sys.path.insert(0, "/home/tal-weiss/Workspace/sima")

from sima_llm import LLMRouter
from sima_prompts import PromptRegistry
from sima_brain.module_runner import ModuleRunner
from sima_brain.senses.heartbeat import HeartbeatSense
from sima_brain.senses.breathing import BreathingSense
from sima_brain.senses.thought_burden import ThoughtBurdenSense
from sima_brain.senses.weather import WeatherSense


async def collect_senses() -> dict:
    """Collect real sensory data."""
    heartbeat = HeartbeatSense()
    breathing = BreathingSense()
    thought_burden = ThoughtBurdenSense(model_name="gpt-4o")
    weather = WeatherSense()

    # Mock memories for thought burden
    memories = [
        {"content": "Genesis: In the beginning there was silence...", "level": "L3"},
        {"content": "Recent conversation about consciousness.", "level": "L1"},
    ]

    hb = await heartbeat.collect()
    br = await breathing.collect()
    tb = await thought_burden.collect(memories=memories, additional_context_tokens=2000)
    wx = await weather.collect()

    senses = {
        "heartbeat_rate": hb,
        "breathing_rate": br,
        "thought_burden": tb,
        "tiredness": {"value": 14.2, "unit": "hours"},  # Simulated
    }
    if wx:
        senses["weather"] = wx

    return senses


async def run_perception(input_text: str, input_type: str = "user_message"):
    """Run the perception module with given input."""
    console = Console()

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENAI_API_KEY not set[/]")
        console.print("Set it with: export OPENAI_API_KEY=your-key")
        return

    console.print("\n[bold cyan]🧠 SIMA PERCEPTION MODULE[/]\n")

    # Collect senses
    console.print("[dim]Collecting sensory data...[/]")
    senses = await collect_senses()

    # Display senses
    sense_table = Table(title="Current Sensory State", box=box.ROUNDED)
    sense_table.add_column("Sense", style="cyan")
    sense_table.add_column("Value", justify="right")

    sense_table.add_row("💓 Heartbeat", f"{senses['heartbeat_rate']['value']:.1f}%")
    sense_table.add_row("🌬️  Breathing", f"{senses['breathing_rate']['value']:.1f}%")
    sense_table.add_row("🧠 Thought Burden", f"{senses['thought_burden']['value']:.1f}%")
    sense_table.add_row("😴 Tiredness", f"{senses['tiredness']['value']:.1f}h")
    if "weather" in senses:
        wx = senses["weather"]
        sense_table.add_row(
            "🌤️  Weather",
            f"{wx['temperature']['current']}°C, {wx['conditions']['description']}"
        )

    console.print(sense_table)
    console.print()

    # Display input (exactly what Sima sees)
    if input_type == "minute_tick":
        if "--midnight" in sys.argv:
            tick_info = "Time: Thursday 0:00"
        elif "--noon" in sys.argv:
            tick_info = "Time: Wednesday 12:00"
        else:
            tick_info = "Time: Wednesday 15:30"
        console.print(Panel(tick_info, title="[yellow]Input[/]", border_style="yellow"))
    else:
        console.print(Panel(f'Someone said: "{input_text}"', title="[yellow]Input[/]", border_style="yellow"))

    # Set up LLM and module runner
    console.print("\n[dim]Running perception module...[/]\n")

    llm_router = LLMRouter(
        primary_provider="openai",
        primary_model="gpt-4o",
        api_keys={"openai": api_key},
    )
    module_runner = ModuleRunner(
        llm_router=llm_router,
        prompt_registry=PromptRegistry(),
    )

    # Build variables
    variables = {
        "trace_id": "demo-trace-001",
        "recurrence_steps": 3,
        "input_type": input_type,
        "recent_external_messages": [],
        "recent_workspace_summaries": [],
        "current_goal": "Understand and engage with the world.",
        "senses": senses,
    }

    if input_type == "user_message":
        variables["incoming_message_text"] = input_text
    elif input_type == "minute_tick":
        # Check for special time flags
        if "--midnight" in sys.argv:
            variables["tick_timestamp"] = "2026-01-23T00:00:00"
            variables["tick_hour"] = 0
            variables["tick_minute"] = 0
            variables["tick_day_of_week"] = "Thursday"
        elif "--noon" in sys.argv:
            variables["tick_timestamp"] = "2026-01-22T12:00:00"
            variables["tick_hour"] = 12
            variables["tick_minute"] = 0
            variables["tick_day_of_week"] = "Wednesday"
        else:
            variables["tick_timestamp"] = "2026-01-22T15:30:00"
            variables["tick_hour"] = 15
            variables["tick_minute"] = 30
            variables["tick_day_of_week"] = "Wednesday"

    # Run perception
    result = await module_runner.run("perception_rpt", variables)

    if not result.output:
        console.print("[red]Perception failed to produce output[/]")
        return

    output = result.output

    # Display structured output
    console.print(Panel(
        f"[bold]{output.get('summary', 'No summary')}[/]",
        title="[green]Percept Summary[/]",
        border_style="green"
    ))

    # Recurrence info
    recurrence = output.get("recurrence", {})
    stability = output.get("stability_score", 0)
    if isinstance(recurrence, dict):
        steps = recurrence.get("steps", 0)
        stability = recurrence.get("stability_score", stability)
    else:
        steps = len(recurrence) if isinstance(recurrence, list) else 0
    console.print(f"\n[magenta]Recurrence:[/] {steps} steps, stability: {stability:.2f}")

    revisions = recurrence.get("revisions", []) if isinstance(recurrence, dict) else []
    # Also check for recurrence_steps or recurrence_iterations at top level
    if not revisions or not isinstance(revisions, list):
        revisions = output.get("recurrence_steps", [])
    if not revisions or not isinstance(revisions, list):
        revisions = output.get("recurrence_iterations", [])
    if revisions and isinstance(revisions, list):
        console.print("[dim]Revisions:[/]")
        for rev in revisions:
            if isinstance(rev, dict):
                console.print(f"  Step {rev.get('step')}: {rev.get('delta_summary', 'no change')[:60]}...")

    # Representation
    rep = output.get("representation", {})
    if rep:
        console.print(f"\n[cyan]Topics:[/] {', '.join(rep.get('topics', []))}")

        claims = rep.get("claims", [])
        if claims:
            console.print("\n[cyan]Claims:[/]")
            for claim in claims[:3]:  # Show first 3
                console.print(f"  • {claim.get('claim', '')}")
                if claim.get("uncertainty"):
                    console.print(f"    [dim]Uncertainty: {claim.get('uncertainty')}[/]")

    # Intents and entities
    intents = output.get("intents", [])
    if intents:
        console.print(f"\n[yellow]Intents:[/] {', '.join(intents)}")

    entities = output.get("entities", [])
    if entities:
        console.print(f"[yellow]Entities:[/] {', '.join(entities)}")

    # Questions
    questions = output.get("questions", [])
    if questions:
        console.print(f"\n[blue]Questions identified:[/]")
        for q in questions:
            console.print(f"  ? {q}")

    # Confidence
    confidence = output.get("confidence", 0)
    conf_color = "green" if confidence > 0.7 else "yellow" if confidence > 0.4 else "red"
    console.print(f"\n[{conf_color}]Confidence: {confidence:.2f}[/]")

    # Suppress output flag
    if output.get("suppress_output"):
        console.print("\n[dim]→ Output suppressed (routine tick)[/]")

    # Full JSON
    console.print("\n[dim]─── Full Perception Output ───[/]")
    json_str = json.dumps(output, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    console.print(syntax)


def main():
    """Entry point."""
    if "--tick" in sys.argv:
        # Run as minute tick (no user input)
        asyncio.run(run_perception("", input_type="minute_tick"))
    elif len(sys.argv) > 1:
        input_text = " ".join([a for a in sys.argv[1:] if a != "--tick"])
        asyncio.run(run_perception(input_text))
    else:
        input_text = "What do you feel right now?"
        asyncio.run(run_perception(input_text))


if __name__ == "__main__":
    main()
