# Issue 19: File Tools

## Status
.todo

## Description
Implement file operation tools: view_file, create_file, str_replace_editor.

## User Scenarios

### Scenario 1: View Entire File
- User asks: "Show me main.py"
- Agent calls view_file(file_path="main.py")
- Tool reads file from filesystem
- Returns content with line numbers
- Agent displays to user

### Scenario 2: View File Range
- User asks: "Show lines 10-20 of main.py"
- Agent calls view_file(file_path="main.py", line_range=[10, 20])
- Tool reads only specified lines
- Returns content with correct line numbers
- Agent displays to user

### Scenario 3: Create New File
- User asks: "Create utils.py with a hello function"
- Agent calls create_file(file_path="utils.py", content="...")
- Tool checks if file exists
- File doesn't exist, creates it
- Returns success message
- Agent confirms to user

### Scenario 4: Create File Fails (Already Exists)
- User asks: "Create main.py"
- Agent calls create_file(file_path="main.py", content="...")
- Tool checks if file exists
- File exists, returns error
- Agent explains to user

### Scenario 5: String Replace
- User asks: "Replace the hello function with a goodbye function"
- Agent calls str_replace_editor(
    file_path="utils.py",
    old_text="def hello():\n    print('hello')",
    new_text="def goodbye():\n    print('goodbye')"
  )
- Tool finds old_text in file
- Replaces with new_text
- Returns confirmation with diff
- Agent shows change to user

### Scenario 6: String Replace Fails (Not Found)
- Agent calls str_replace_editor with old_text that doesn't exist
- Tool returns error
- Agent asks user for clarification

### Scenario 7: String Replace Fails (Multiple Matches)
- Agent calls str_replace_editor with old_text that appears twice
- Tool returns error
- Agent asks user to be more specific

## Acceptance Criteria

### view_file
1. `ViewFileTool` class in `goz/agent/tools/file_tools.py`
2. Reads file content with line numbers
3. Supports optional line_range parameter
4. Returns formatted content with line numbers
5. Raises FileNotFoundError if file doesn't exist
6. Handles binary files gracefully

### create_file
7. `CreateFileTool` class in `goz/agent/tools/file_tools.py`
8. Creates new file with content
9. Creates parent directories if needed
10. Returns success message with file path
11. Returns error if file already exists
12. Returns error if permission denied

### str_replace_editor
13. `StrReplaceEditorTool` class in `goz/agent/tools/file_tools.py`
14. Finds old_text in file
15. Replaces with new_text
16. Returns diff-style confirmation
17. Returns error if old_text not found
18. Returns error if old_text appears multiple times
19. Returns error if file doesn't exist
20. Supports unicode content correctly

### General
21. All tools validate inputs against schema
22. All tools use working_dir from config
23. All tools handle relative paths correctly
24. All tools handle Windows/Unix paths correctly

## Technical Details

### File Structure
```
goz/agent/tools/
└── file_tools.py   # ViewFileTool, CreateFileTool, StrReplaceEditorTool
```

### Tool Definitions

#### view_file
```python
class ViewFileTool(BaseTool):
    name = "view_file"
    description = (
        "View a file's contents with line numbers. "
        "Use this to read existing files and understand code structure. "
        "For large files, use line_range to focus on specific sections."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to view"
            },
            "line_range": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 2,
                "description": "Optional [start, end] line range (1-indexed, inclusive)"
            }
        },
        "required": ["file_path"]
    }

    async def execute(
        self,
        file_path: str,
        line_range: list[int] | None = None,
    ) -> str:
        """View file contents."""
```

#### create_file
```python
class CreateFileTool(BaseTool):
    name = "create_file"
    description = (
        "Create a new file with content. "
        "Use this to create new source files, configs, etc. "
        "If the file already exists, this will fail."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path for the new file"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "required": ["file_path", "content"]
    }

    async def execute(self, file_path: str, content: str) -> str:
        """Create new file."""
```

#### str_replace_editor
```python
class StrReplaceEditorTool(BaseTool):
    name = "str_replace_editor"
    description = (
        "Replace text in an existing file. "
        "Best for making targeted edits to existing code. "
        "The old_text must be unique in the file - use more context if needed."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit"
            },
            "old_text": {
                "type": "string",
                "description": "Text to replace (must be unique in file)"
            },
            "new_text": {
                "type": "string",
                "description": "Replacement text"
            }
        },
        "required": ["file_path", "old_text", "new_text"]
    }

    async def execute(
        self,
        file_path: str,
        old_text: str,
        new_text: str,
    ) -> str:
        """Replace text in file."""
```

### Output Format

#### view_file output
```
File: main.py (42 lines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

     1→ def main():
     2→     app = GozApp()
     3→     app.run()
     4→
     5→
     6→ if __name__ == "__main__":
     7→     main()
```

#### str_replace_editor output
```
Edited: utils.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- def hello():
-     print('hello')
+ def goodbye():
+     print('goodbye')
```

### Error Messages
- "File not found: {file_path}"
- "File already exists: {file_path}. Use str_replace_editor to modify."
- "Could not find the specified text to replace. It may have changed."
- "Found multiple matches for the specified text. Include more context."
- "Permission denied: {file_path}"

## Dependencies
- Issue 18: Tool Base + Registry

## Related Issues
- Issue 20: Bash Tool
- Issue 21: Search/Read/Repo Tools

## Log
