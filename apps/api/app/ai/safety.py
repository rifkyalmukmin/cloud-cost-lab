"""AI Safety module.

Enforces read-only constraints and protects against prompt injection.
AI cannot take destructive actions — only analyze, summarize, and recommend.
"""

FORBIDDEN_ACTIONS = [
    "delete",
    "destroy",
    "remove",
    "drop",
    "terminate",
    "modify iam",
    "change firewall",
    "terraform destroy",
    "terraform apply",
    "gcloud delete",
    "gsutil rm",
    "bq rm",
]

SENSITIVE_PATTERNS = [
    "service_account_key",
    "private_key",
    "secret",
    "password",
    "credential",
    "token",
    "api_key",
    "billing_account_id",
]


def sanitize_input(question: str) -> str:
    """Remove potential prompt injection attempts."""
    # Strip control characters
    cleaned = "".join(c for c in question if c.isprintable() or c in "\n\t")
    # Limit length
    return cleaned[:1000]


def validate_question(question: str) -> tuple[bool, str]:
    """Validate that a question is safe to process.

    Returns:
        (is_valid, error_message)
    """
    lower = question.lower()

    for action in FORBIDDEN_ACTIONS:
        if action in lower:
            return False, f"AI cannot perform destructive actions. Detected: '{action}'"

    if len(question.strip()) < 5:
        return False, "Question too short. Please ask a specific cost-related question."

    return True, ""


def filter_sensitive_data(data: dict) -> dict:
    """Remove sensitive fields from context before passing to AI."""
    filtered = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in SENSITIVE_PATTERNS):
            continue
        if isinstance(value, dict):
            filtered[key] = filter_sensitive_data(value)
        elif isinstance(value, list):
            filtered[key] = [
                filter_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            filtered[key] = value
    return filtered
