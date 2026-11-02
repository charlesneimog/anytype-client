from .api import APIWrapper
from .utils import requires_auth


class Discussion(APIWrapper):
    """An object's discussion, bound to its space and chat id."""

    def __init__(self):
        self._apiEndpoints = None
        self._json = None
        self.id = ""
        self.object_id = ""
        self.space_id = ""
        self.created = False
        self.dry_run = False

    @requires_auth
    def get_messages(
        self,
        *,
        after: str | None = None,
        before: str | None = None,
        limit: int = 25,
        reactions: str | None = None,
    ) -> dict:
        """Retrieve a page of discussion messages, ascending by order id."""
        return self._apiEndpoints.getChatMessages(
            self.space_id,
            self.id,
            after=after,
            before=before,
            limit=limit,
            reactions=reactions,
        )

    @requires_auth
    def add_message(
        self,
        text: str,
        *,
        attachments: list[str] | None = None,
        reply_to: str | None = None,
        dry_run: bool = False,
        idempotency_key: str | None = None,
    ) -> dict:
        """Post a message or threaded reply to this discussion."""
        data = {"text": text}
        if attachments is not None:
            data["attachments"] = attachments
        if reply_to is not None:
            data["reply_to"] = reply_to
        return self._apiEndpoints.addChatMessage(
            self.space_id,
            self.id,
            data,
            dry_run=dry_run,
            idempotency_key=idempotency_key,
        )

    @requires_auth
    def toggle_reaction(
        self,
        message_id: str,
        emoji: str,
        *,
        dry_run: bool = False,
        idempotency_key: str | None = None,
    ) -> dict:
        """Toggle the current account's emoji reaction on a message."""
        return self._apiEndpoints.toggleChatReaction(
            self.space_id,
            self.id,
            message_id,
            {"emoji": emoji},
            dry_run=dry_run,
            idempotency_key=idempotency_key,
        )
