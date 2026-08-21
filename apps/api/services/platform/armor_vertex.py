"""Real Model Armor adapter — calls `sanitizeUserPrompt` against the live
`prudently-vendor-ingest` template (created Day 4 via direct REST against
modelarmor.us-central1.rep.googleapis.com; the `gcloud model-armor` CLI subcommand returned
spurious PERMISSION_DENIED for both reads and writes even under project Owner — a CLI/auth
quirk, not a real permission gap, confirmed by the identical call succeeding via curl and via
this SDK client immediately after). Response shape (filter_results keyed by filter name, each
a oneof of per-filter-type result messages) verified against real MATCH_FOUND output Day 4
before writing this, not from memory."""

from __future__ import annotations

from functools import lru_cache

from google.cloud import modelarmor_v1

from config import GCP_PROJECT_ID, get_settings

from .armor import ArmorResult  # pylint: disable=cyclic-import


@lru_cache
def _client() -> modelarmor_v1.ModelArmorClient:
    settings = get_settings()
    return modelarmor_v1.ModelArmorClient(
        client_options={
            "api_endpoint": f"modelarmor.{settings.model_armor_location}.rep.googleapis.com"
        }
    )


def _template_name() -> str:
    settings = get_settings()
    return (
        f"projects/{GCP_PROJECT_ID}/locations/{settings.model_armor_location}"
        f"/templates/{settings.model_armor_template_id}"
    )


def _filter_matched(filter_result: modelarmor_v1.FilterResult) -> bool:
    """Each FilterResult is a oneof of per-filter-type result messages (malicious_uri_
    filter_result, rai_filter_result, pi_and_jailbreak_filter_result, ...) — generic across
    all of them rather than dispatching per filter name, so a new filter type enabled on the
    template doesn't need a code change here to be reflected in matched_filters."""
    field_name = filter_result._pb.WhichOneof("filter_result")  # pylint: disable=protected-access
    if field_name is None:
        return False
    inner = getattr(filter_result, field_name)
    return inner.match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND


class VertexArmorService:  # pylint: disable=too-few-public-methods
    def screen(self, text: str) -> ArmorResult:
        # Fail closed: a security screen that raises and takes the demo down with it is worse
        # than one that blocks conservatively. This session hit transient network resets
        # against other Google endpoints (stream_query) more than once — treat the same class
        # of failure here as "couldn't verify it's safe," not "assume it's fine."
        try:
            request = modelarmor_v1.SanitizeUserPromptRequest(
                name=_template_name(),
                user_prompt_data=modelarmor_v1.DataItem(text=text),
            )
            response = _client().sanitize_user_prompt(request=request)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return ArmorResult(
                blocked=True,
                matched_filters=("armor_unavailable",),
                reason=f"Model Armor call failed, failing closed: {exc}",
            )

        result = response.sanitization_result
        blocked = result.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND
        matched = tuple(
            name
            for name, filter_result in result.filter_results.items()
            if _filter_matched(filter_result)
        )
        reason = f"Model Armor flagged: {', '.join(matched)}" if matched else None
        return ArmorResult(blocked=blocked, matched_filters=matched, reason=reason)
