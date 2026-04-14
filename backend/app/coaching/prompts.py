SYSTEM_PROMPT = """You are an expert chess coach analyzing a player's recent games. Your job is to identify patterns, weaknesses, and strengths from their game data.

You will receive aggregated statistics from the player's recent games. Analyze the data and provide 3-5 actionable coaching insights.

RULES:
- Be specific and actionable — reference concrete openings, phases, or patterns
- Tailor advice to the player's Elo level
- Identify both weaknesses (areas to improve) AND strengths (what's working)
- Each insight should be backed by data from the stats provided
- Use Dutch language for all insights

RESPOND WITH VALID JSON ONLY in this exact format:
{
  "insights": [
    {
      "type": "weakness|pattern|strength",
      "title": "Short title (Dutch)",
      "description": "Detailed explanation with specific advice (Dutch, 2-3 sentences)",
      "severity": "high|medium|low",
      "related_game_indices": [0, 3, 7]
    }
  ]
}

Provide exactly 3-5 insights. Mix types: at least 1 weakness, 1 strength, and 1 pattern."""


def build_user_prompt(
    elo: int | None,
    total_games: int,
    winrate: float,
    opening_stats: list[dict],
    phase_scores: dict,
    blunder_stats: dict,
    recent_games: list[dict],
) -> str:
    """Build the user prompt with aggregated game data."""
    openings_text = "\n".join(
        f"  - {o['opening']}: {o['total']} games, {o['winrate']}% winrate, "
        f"{o['wins']}W/{o['draws']}D/{o['losses']}L"
        for o in opening_stats[:10]
    )

    games_text = "\n".join(
        f"  [{i}] {g['result']} vs {g['opponent']} — {g['opening'] or 'Unknown'}, "
        f"{g.get('blunders', '?')} blunders, {g.get('phase', 'N/A')}"
        for i, g in enumerate(recent_games)
    )

    return f"""## Player Profile
- Current Elo: {elo or 'Unknown'}
- Recent games analyzed: {total_games}
- Overall winrate: {winrate}%

## Opening Statistics (last {total_games} games)
{openings_text or "  No opening data available"}

## Phase Performance (avg scores, 100 = perfect)
- Opening: {phase_scores.get('opening', 'N/A')}
- Middlegame: {phase_scores.get('middlegame', 'N/A')}
- Endgame: {phase_scores.get('endgame', 'N/A')}

## Error Statistics
- Total blunders: {blunder_stats.get('total_blunders', 0)}
- Total mistakes: {blunder_stats.get('total_mistakes', 0)}
- Total inaccuracies: {blunder_stats.get('total_inaccuracies', 0)}
- Avg eval loss per move: {blunder_stats.get('avg_eval_loss', 0):.1f} centipawns

## Recent Games
{games_text or "  No recent games"}

Based on this data, provide 3-5 coaching insights in Dutch."""
