"""Single pure entrypoint for the supported, deliberately limited story gate."""
from __future__ import annotations

from dataclasses import dataclass
from .contracts import EvidenceKey, StoryStabilityFacts, StoryStabilityResult
from .stability import check_nonsway_ts500_7_13


@dataclass(frozen=True, slots=True)
class FirstPassResult:
    evidence: EvidenceKey
    stories: tuple[StoryStabilityResult, ...]
    full_column_design_completed: bool = False


def execute_first_pass(stories: tuple[StoryStabilityFacts, ...]) -> FirstPassResult:
    if not stories:
        raise ValueError("No story data provided")
    if len({(s.story_id, s.direction) for s in stories}) != len(stories):
        raise ValueError("Duplicate story-direction pair")
    evidence = stories[0].evidence
    if any(s.evidence != evidence for s in stories):
        raise ValueError("Cannot mix source, epoch, analysis generation or load state")
    return FirstPassResult(
        evidence=evidence,
        stories=tuple(check_nonsway_ts500_7_13(s) for s in stories),
    )
