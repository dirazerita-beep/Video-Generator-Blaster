"""Variation recipe generator for Video Generator Blaster."""

import random
from typing import Optional


def generate_recipes(
    n: int,
    hooks: list[str],
    benefits: list[str],
    ctas: list[str],
    tts_scripts: list[str],
    music_files: list[str],
    num_segments: int,
    shuffle_enabled: bool,
    seed: Optional[int] = None,
) -> list[dict]:
    """Generate N variation recipes, each describing one video output.

    Each recipe is a dict with:
      - hook_text: str or ""
      - benefit_text: str or ""
      - cta_text: str or ""
      - tts_script: str or None
      - music_file: str or None
      - segment_order: list[int] (shuffled indices of segments)
      - intro_text: str (same as hook_text)
      - outro_text: str (same as cta_text)
      - seed: int (per-recipe seed for reproducibility)

    Recipes are unique: no two recipes will be exactly identical if
    there is enough combinatorial variation; otherwise duplicates are
    allowed after all unique combinations are exhausted.

    Args:
        n: Number of recipes to generate.
        hooks: List of hook text strings.
        benefits: List of benefit text strings.
        ctas: List of CTA text strings.
        tts_scripts: List of TTS script strings (may be empty).
        music_files: List of music file paths (may be empty).
        num_segments: Number of segments to split the video into.
        shuffle_enabled: Whether segment shuffling is enabled.
        seed: Optional master seed for reproducibility.

    Returns:
        List of recipe dicts.
    """
    rng = random.Random(seed)

    def _pick(lst: list, rng: random.Random):
        """Pick a random element from a list, or return empty string if empty."""
        if not lst:
            return ""
        return rng.choice(lst)

    def _make_segment_order(num_segments: int, rng: random.Random) -> list[int]:
        order = list(range(num_segments))
        if shuffle_enabled:
            rng.shuffle(order)
        return order

    recipes = []
    seen: set[str] = set()

    attempts = 0
    max_attempts = n * 20  # Guard against infinite loops

    while len(recipes) < n and attempts < max_attempts:
        attempts += 1
        recipe_seed = rng.randint(0, 2**31 - 1)
        recipe_rng = random.Random(recipe_seed)

        hook = _pick(hooks, recipe_rng) if hooks else ""
        benefit = _pick(benefits, recipe_rng) if benefits else ""
        cta = _pick(ctas, recipe_rng) if ctas else ""
        tts_script = _pick(tts_scripts, recipe_rng) if tts_scripts else None
        music_file = _pick(music_files, recipe_rng) if music_files else None
        segment_order = _make_segment_order(num_segments, recipe_rng)

        recipe = {
            "hook_text": hook,
            "benefit_text": benefit,
            "cta_text": cta,
            "tts_script": tts_script,
            "music_file": music_file,
            "segment_order": segment_order,
            "intro_text": hook,
            "outro_text": cta,
            "seed": recipe_seed,
        }

        # Build a fingerprint to detect duplicates
        fingerprint = (
            hook,
            benefit,
            cta,
            tts_script or "",
            music_file or "",
            tuple(segment_order),
        )
        key = str(fingerprint)

        if key not in seen:
            seen.add(key)
            recipes.append(recipe)
        elif attempts >= max_attempts:
            # Add anyway if we've exhausted unique combinations
            recipes.append(recipe)

    # If we still haven't reached n (all unique combos exhausted), fill with duplicates
    if recipes:
        while len(recipes) < n:
            idx = rng.randint(0, len(recipes) - 1)
            base = dict(recipes[idx])
            base["seed"] = rng.randint(0, 2**31 - 1)
            recipes.append(base)

    return recipes[:n]
