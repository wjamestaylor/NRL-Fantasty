from .feed_ingestion import load_feed_bundle

_FEED_BUNDLE = load_feed_bundle()

PLAYERS = _FEED_BUNDLE.players
FIXTURES = _FEED_BUNDLE.fixtures
NEWS_SIGNALS = _FEED_BUNDLE.news_signals
DATA_SOURCE_HEALTH = _FEED_BUNDLE.source_health
DATA_LOADED_AT = _FEED_BUNDLE.loaded_at
