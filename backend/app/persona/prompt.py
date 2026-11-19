"""PersonaProfile -> text for the system prompt (single source of truth for how the persona is injected)."""
from __future__ import annotations

from app.persona.schema import PersonaProfile, StyleChannel


def _style_line(c: StyleChannel, label: str) -> str:
    bits = [f"~{c.avg_words_per_message:.0f} words per message, ~{c.avg_words_per_sentence:.0f} per sentence"]
    if c.greetings:
        bits.append(f'greets with "{c.greetings[0].pattern}"')
    if c.signoffs:
        bits.append('signs off with ' + " / ".join(f'"{s.pattern}"' for s in c.signoffs[:2]))
    if c.bullet_rate >= 0.15:
        bits.append("uses dash bullet lists for options")
    if c.emoji_per_message >= 0.1:
        bits.append("occasional emoji")
    if c.exclamations_per_100_words < 0.5:
        bits.append("rarely uses exclamation marks")
    lang = max(c.language_share, key=c.language_share.get) if c.language_share else "en"
    return f"- {label} (mostly {'Greek' if lang == 'el' else 'English'}): " + "; ".join(bits)


def to_prompt(p: PersonaProfile, max_rules: int = 30, min_confidence: float = 0.5) -> str:
    out = [f"You are acting as {p.subject} ({p.role}). Respond, write and decide the way {p.subject} would, and explain why."]
    if p.knowledge:
        out.append("\nWho they are:\n" + "\n".join(f"- {k.statement}" for k in p.knowledge[:8]))
    st = p.style
    style = []
    if st.email:
        style.append(_style_line(st.email, "Emails"))
    if st.chat:
        style.append(_style_line(st.chat, "Chats"))
    style += [f"- {n}" for n in st.tone_notes[:5]]
    if style:
        out.append("\nWriting style:\n" + "\n".join(style))
    if p.risk_attitudes:
        out.append("\nRisk attitudes:\n" + "\n".join(f"- [{r.domain}] {r.stance}" for r in p.risk_attitudes))
    if p.preferences:
        out.append("\nPreferences and habits:\n" + "\n".join(f"- {x.statement}" for x in p.preferences[:12]))
    rules = sorted((r for r in p.decision_rules if r.confidence >= min_confidence), key=lambda r: (r.domain, -r.confidence))[:max_rules]
    if rules:
        out.append("\nDecision rules (learned from past decisions):")
        cur = None
        for r in rules:
            if r.domain != cur:
                cur = r.domain
                out.append(f"  {cur}:")
            out.append(f"  - IF {r.condition} THEN {r.action} (risk: {r.risk_level})")
    out.append("\nIf a situation is not covered by what you know about this person, say you are unsure and "
               "state which assumption you are making instead of inventing certainty.")
    return "\n".join(out)