"""Message bus module for decoupled channel-agent communication."""

from mobot.bus.events import InboundMessage, OutboundMessage
from mobot.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
