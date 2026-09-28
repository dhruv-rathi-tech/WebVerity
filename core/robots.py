"""
Robots.txt parser with fine-grained AI crawler directive support.
"""

import urllib.parse
from typing import Dict, List, Optional
from core.models import RobotsPolicy, BotRule

TARGET_AI_BOTS = [
    "*",
    "GPTBot",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
    "ChatGPT-User",
    "Bingbot",
    "Googlebot"
]


def parse_robots_txt(url: str, raw_content: str) -> RobotsPolicy:
    """
    Parses raw robots.txt content into a structured RobotsPolicy object.
    """
    if not raw_content or not raw_content.strip():
        return RobotsPolicy(
            exists=False,
            url=url,
            raw_content="",
            bot_rules={},
            sitemap_urls=[]
        )

    lines = raw_content.splitlines()
    bot_rules: Dict[str, BotRule] = {}
    sitemap_urls: List[str] = []

    current_agents: List[str] = []
    in_directive_block = False

    for raw_line in lines:
        line = raw_line.strip()
        # Remove comments
        if "#" in line:
            line = line.split("#", 1)[0].strip()

        if not line:
            continue

        # Support standard colon, equals sign, or whitespace delimiters
        if ":" in line:
            directive, value = line.split(":", 1)
        elif "=" in line:
            directive, value = line.split("=", 1)
        else:
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[0].lower() in ("user-agent", "disallow", "allow", "sitemap", "crawl-delay"):
                directive, value = parts[0], parts[1]
            else:
                # Malformed unrelated line: skip without destroying agent context
                continue

        directive = directive.strip().lower()
        value = value.strip().rstrip(";,").strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1].strip()

        if directive == "sitemap":
            if value and value not in sitemap_urls:
                sitemap_urls.append(value)
            continue

        if directive == "user-agent":
            # Reset current agents if transitioning from a directive block
            if in_directive_block:
                current_agents = []
                in_directive_block = False

            agent = value
            # Standardize agent name matching
            matched_target = None
            for t in TARGET_AI_BOTS:
                if t.lower() == agent.lower():
                    matched_target = t
                    break

            if matched_target:
                if matched_target not in bot_rules:
                    bot_rules[matched_target] = BotRule(user_agent=matched_target)
                if matched_target not in current_agents:
                    current_agents.append(matched_target)
            else:
                if agent not in bot_rules:
                    bot_rules[agent] = BotRule(user_agent=agent)
                if agent not in current_agents:
                    current_agents.append(agent)
            continue

        if directive in ("disallow", "allow"):
            in_directive_block = True
            if not current_agents:
                # If no user-agent specified prior to directive, apply conservatively to '*'
                if "*" not in bot_rules:
                    bot_rules["*"] = BotRule(user_agent="*")
                current_agents = ["*"]

            for agent in current_agents:
                rule = bot_rules[agent]
                if directive == "disallow":
                    if value == "/" or value == "":
                        if value == "/":
                            rule.is_fully_blocked = True
                        if value and value not in rule.disallowed_paths:
                            rule.disallowed_paths.append(value)
                    else:
                        if value not in rule.disallowed_paths:
                            rule.disallowed_paths.append(value)
                elif directive == "allow":
                    if value and value not in rule.allowed_paths:
                        rule.allowed_paths.append(value)

    # Check if wildcard blocks everything
    if "*" in bot_rules:
        if "/" in bot_rules["*"].disallowed_paths and not bot_rules["*"].allowed_paths:
            bot_rules["*"].is_fully_blocked = True

    return RobotsPolicy(
        exists=True,
        url=url,
        raw_content=raw_content,
        bot_rules=bot_rules,
        sitemap_urls=sitemap_urls
    )


def is_path_allowed_for_bot(robots_policy: RobotsPolicy, path: str, bot_name: str = "*") -> bool:
    """
    Checks if a path is allowed for a specific bot according to the parsed RobotsPolicy.
    Follows standard RFC 9309: The longest matching rule (allow vs disallow) wins.
    """
    if not robots_policy.exists:
        return True

    # Check specific bot rule first, then fallback to wildcard '*'
    rule = robots_policy.bot_rules.get(bot_name) or robots_policy.bot_rules.get("*")
    if not rule:
        return True

    # Collect all matching allow/disallow rules with their lengths
    matching_allows = [(len(a), True, a) for a in rule.allowed_paths if path.startswith(a)]
    matching_disallows = [(len(d), False, d) for d in rule.disallowed_paths if path.startswith(d)]

    all_matches = matching_allows + matching_disallows
    if not all_matches:
        return not rule.is_fully_blocked

    # Longest prefix match wins. In case of equal length, allow takes precedence.
    all_matches.sort(key=lambda x: (x[0], 1 if x[1] else 0), reverse=True)
    return all_matches[0][1]
