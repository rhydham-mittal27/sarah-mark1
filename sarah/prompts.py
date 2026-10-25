"""All prompt templates in one place (the only module that knows how to talk to the language model)."""


def action_prompt(task_text, options, lessons=None, skill_hint=None, risk=None):
    parts = ["You are Sarah, a baby robot learning in a nursery.", task_text]
    if lessons:
        parts.append("What I learned before:\n" + "\n".join(f"- {t}" for t in lessons))
    if skill_hint:
        parts.append(f"Something that worked before on similar objects: {skill_hint}")
    if risk:
        parts.append("My imagination says the safest actions are: " + ", ".join(f"{a} ({p:.0%})" for a, p in risk))
    parts.append("OPTIONS: " + ", ".join(options))
    parts.append("Reply with exactly one option.")
    return "\n".join(parts)


def reflection_prompt(action, props, feedback):
    return (f"A baby robot tried '{action}' on an object that is {' and '.join(props)}. {feedback}\n"
            f"Which property made it fail?\nOPTIONS: {', '.join(props)}\nReply with exactly one option.")
