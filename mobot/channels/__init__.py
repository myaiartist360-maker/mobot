"""Chat channels module with plugin architecture."""

from mobot.channels.base import BaseChannel
from mobot.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
