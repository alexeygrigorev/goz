# goz - Python TUI Specification

**Goal**: Minimal, simple Textual TUI for Z.AI capabilities.

## Design Principles

1. **Simplicity first**: Minimal UI, direct actions
2. **HTTP over MCP**: Direct API calls instead of MCP protocol (simpler)
3. **Core features only**: vision, search, read (MVP)
4. **CLI + TUI**: Dual mode - interactive TUI or CLI commands

---

## API Module Specification

### HTTP Client (`goz.api.client`)

```python
class ZaiClient:
    """Direct HTTP API client for Z.AI services."""

    async def vision_analyze(
        self, image: str | bytes, prompt: str = "Describe this image."
    ) -> str:
        """Analyze image via vision API."""

    async def web_search(
        self,
        query: str,
        domain: str | None = None,
        recency: Literal["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"] = "noLimit",
        count: int = 10,
    ) -> list[SearchResult]:
        """Search the web."""

    async def web_read(
        self,
        url: str,
        format: Literal["markdown", "text"] = "markdown",
        timeout: int = 20,
    ) -> str:
        """Fetch and parse web page."""
```

### Data Types

```python
@dataclass
class SearchResult:
    rank: int
    title: str
    url: str
    summary: str
    source: str | None = None
    date: str | None = None

class ZaiError(Exception):
    """Base error for Z.AI API calls."""

class AuthError(ZaiError):
    """API key invalid or missing."""

class ApiError(ZaiError):
    """API request failed."""
```

### API Endpoints (Direct HTTP)

Instead of MCP, use these endpoints directly:

| Service | Endpoint | Method |
|---------|----------|--------|
| Vision | `https://api.z.ai/api/coding/paas/v4/chat/completions` | POST |
| Search | `https://api.z.ai/api/mcp/web_search_prime/mcp` (via UTCP) or HTTP | POST |
| Reader | `https://api.z.ai/api/mcp/web_reader/mcp` (via UTCP) or HTTP | POST |

**Note**: The TypeScript version uses UTCP/MCP. For simplicity in Python, we can:
1. Call the HTTP APIs directly if available
2. Use a minimal MCP client implementation
3. Start with direct APIs, add MCP later if needed

---

## Config Module Specification

### Config File Location

`~/.config/goz/config.json` (XDG standard)

### Config Schema

```json
{
  "anthropic_auth_token": "your-token-here",
  "anthropic_base_url": "https://api.z.ai/api/anthropic",
  "timeout": 120
}
```

**Note**: Despite the "anthropic" names, these are Z.AI credentials.

### Config Loading (`goz.config`)

```python
@dataclass
class Config:
    anthropic_auth_token: str
    anthropic_base_url: str = "https://api.z.ai/api/anthropic"
    timeout: int = 120  # seconds

def load_config() -> Config:
    """Load from ~/.config/goz/config.json."""
```

### First-Run

If config doesn't exist, prompt for token and create file.

---

## TUI Architecture Specification

### Screen Layout (Minimal)

```
┌─────────────────────────────────────────────┐
│ goz - Z.AI Tools                            │
├─────────────────────────────────────────────┤
│                                             │
│  [F1] Vision    Analyze images/screenshots  │
│  [F2] Search    Web search                  │
│  [F3] Read      Fetch web pages             │
│  [F4] Doctor    Check connection            │
│                                             │
│  [q] Quit                                    │
│                                             │
└─────────────────────────────────────────────┘
```

### Main Screens

1. **MainMenu**: Command selection
2. **VisionScreen**: Image input + prompt + result display
3. **SearchScreen**: Query input + filters + results list
4. **ReadScreen**: URL input + content display
5. **DoctorScreen**: Env check + connection test

### Navigation

- `F1-F4`: Jump to command
- `Esc`: Back to main menu
- `q`: Quit
- `Ctrl+C`: Quit

---

## Command Specifications

### Vision Command

**Input**:
- Image path (or paste from clipboard)
- Optional custom prompt

**Presets**:
- `analyze`: General image description
- `ui-to-code`: Screenshot to code
- `extract-text`: OCR
- `diagnose-error`: Error screenshot analysis
- `diagram`: Technical diagram explanation

**Output**: Text response displayed in scrollable view

### Search Command

**Input**:
- Search query (required)
- Optional domain filter
- Optional recency filter

**Output**: List of results with:
- Rank
- Title
- URL (clickable if possible)
- Summary
- Date (if available)

### Read Command

**Input**:
- URL (required)

**Output**: Markdown content in scrollable view

### Doctor Command

**Checks**:
- API key present
- Base URL reachable
- Simple API call test

**Output**: Status report (all green or show issues)

---

## CLI Mode Specification

### Entry Point Behavior

```bash
goz                                    # No args → Launch TUI
goz <command> [args]                   # With command → CLI mode
```

### CLI Commands

```bash
goz vision <image> [prompt]            # Analyze image
goz search <query> [--domain D]        # Web search
goz read <url>                         # Fetch page
goz doctor                             # Diagnostics
goz config                             # Show/set config (including API key)
```

### Output Modes

- `data`: Raw output (default)
- `json`: JSON wrapped
- `--output pretty`: Pretty printed

### First-Run Experience

If `~/.config/goz/config.json` doesn't exist:
- Prompt: "Enter your Z.AI API key:"
- Create config file
- Continue with requested operation

---

## Implementation Issues

### Phase 1: Foundation (Issues 01-03)

| Issue | Description | Dependencies |
|-------|-------------|--------------|
| 01 | Project setup, dependencies | None |
| 02 | Config module | 01 |
| 03 | HTTP client + errors | 01 |

### Phase 2: APIs (Issues 04-06)

| Issue | Description | Dependencies |
|-------|-------------|--------------|
| 04 | Vision API implementation | 03 |
| 05 | Search API implementation | 03 |
| 06 | Reader API implementation | 03 |

### Phase 3: TUI (Issues 07-09)

| Issue | Description | Dependencies |
|-------|-------------|--------------|
| 07 | TUI foundation + main menu | 01 |
| 08 | Vision screen | 04, 07 |
| 09 | Search + Read screens | 05, 06, 07 |

### Phase 4: CLI Mode (Issue 10)

| Issue | Description | Dependencies |
|-------|-------------|--------------|
| 10 | CLI commands | 04, 05, 06 |

---

## File Structure

```
goz/
├── goz/
│   ├── __init__.py
│   ├── __main__.py           # Entry point, detect CLI vs TUI
│   ├── config.py              # Config loading
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py          # ZaiClient
│   │   └── types.py           # Data classes, errors
│   ├── tui/
│   │   ├── __init__.py
│   │   ├── app.py             # GozApp (main)
│   │   ├── screens/
│   │   │   ├── __init__.py
│   │   │   ├── main.py        # MainMenu
│   │   │   ├── vision.py      # VisionScreen
│   │   │   ├── search.py      # SearchScreen
│   │   │   ├── read.py        # ReadScreen
│   │   │   └── doctor.py      # DoctorScreen
│   │   └── widgets/
│   │       ├── __init__.py
│   │       └── common.py      # Reusable widgets
│   └── cli/
│       ├── __init__.py
│       └── commands.py        # CLI mode
├── tests/
│   ├── test_config.py
│   ├── test_api_client.py
│   ├── test_vision.py
│   ├── test_search.py
│   └── test_read.py
└── docs/
    ├── plan.md
    ├── spec.md
    └── tracker/
```

---

## Testing Strategy

### Unit Tests
- Config loading (env vars, defaults)
- Error types and formatting
- HTTP client mock responses

### Integration Tests
- Vision API with test image
- Search API with real query
- Read API with public URL

### TUI Tests
- Use Textual's `app._run()` with mock inputs
- Screen navigation
- Widget interactions

---

## Open Questions

1. **MCP vs Direct HTTP**: Should we implement full MCP or use direct HTTP?
   - **Recommendation**: Start with direct HTTP for search/read. Vision may need MCP.

2. **Image Input in TUI**: How to input images?
   - **Options**: File path input, drag-drop (if possible), clipboard paste
   - **Recommendation**: Start with file path, add clipboard later

3. **Async vs Sync**: Should the client be async?
   - **Recommendation**: Yes, use httpx async for non-blocking TUI

4. **Streaming Responses**: Handle streaming vision responses?
   - **Recommendation**: No, wait for full response (simpler)
