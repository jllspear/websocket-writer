# WebSocket writer
Writer from a WebSocket to PostgreSQL - Bridge between STOMP topics and corresponding database tables.

## Customisation

### Modules to feed the lib
- `models` - Models SQLModel
- `parser` - Parsers et validators

## Configuration

Linking STOMP topics and parsers with an environment variable.

The keys must match the last path element from the STOMP topic :

```bash
STOMP__MAIN_TOPIC=/topic/trackers
STOMP__SUB_TOPIC=/positions
WEBSOCKET__PARSER_DICT={"trackers":"TrackerParser","positions":"PositionParser"}
```