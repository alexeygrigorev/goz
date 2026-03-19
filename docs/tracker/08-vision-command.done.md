# Issue 08: Vision Command in TUI - Groomed

## Status
.done

## Description
Implement the Vision screen in the TUI with all vision subcommands from zai-cli reference. The screen should provide an intuitive interface for image/video analysis with configurable prompts and options.

## Dependencies
- Issue 04 (Vision API implementation)
- Issue 07 (TUI foundation + main menu)

## Reference
- zai-cli/packages/zai-cli/src/commands/vision.ts
- docs/spec.md

---

## User Scenarios

### Scenario 1: Quick Image Analysis
**User Story**: As a developer, I want to quickly analyze a screenshot to understand what's shown.

**Steps**:
1. User presses F1 or selects "Vision" from main menu
2. Vision screen opens with default "analyze" preset selected
3. User enters image file path (e.g., `./screenshot.png`)
4. User accepts default prompt or enters custom prompt
5. User presses Enter to submit
6. Loading indicator shows while processing
7. Result displays in scrollable output area

**Success Criteria**: User gets detailed image description within 30 seconds

### Scenario 2: UI to Code Conversion
**User Story**: As a frontend developer, I want to convert a design mockup into production code.

**Steps**:
1. User opens Vision screen
2. Selects "ui-to-code" preset from dropdown
3. Enters path to design mockup image
4. Optionally selects output type (code, prompt, spec, description)
5. Optionally modifies the default prompt
6. Submits and receives formatted code output

**Success Criteria**: Code output is properly syntax-highlighted and can be copied

### Scenario 3: OCR for Code/Terminal Screenshots
**User Story**: As a developer, I want to extract text from a terminal screenshot I don't have the history for.

**Steps**:
1. User opens Vision screen
2. Selects "extract-text" preset
3. Enters path to terminal/code screenshot
4. Optionally specifies programming language hint
5. Receives extracted text with preserved formatting

**Success Criteria**: Extracted text maintains code structure and indentation

### Scenario 4: Error Diagnosis
**User Story**: As a developer, I want to paste an error screenshot and get explanation and fixes.

**Steps**:
1. User opens Vision screen
2. Selects "diagnose-error" preset
3. Enters path to error screenshot
4. Optionally adds context (e.g., "during npm install")
5. Receives error explanation and suggested fixes

**Success Criteria**: Response includes both error cause and actionable solutions

### Scenario 5: Technical Diagram Explanation
**User Story**: As a developer, I want to understand a complex architecture diagram.

**Steps**:
1. User opens Vision screen
2. Selects "diagram" preset
3. Enters path to diagram image
4. Optionally specifies diagram type (flowchart, sequence, architecture, etc.)
5. Receives detailed explanation of components and relationships

**Success Criteria**: Explanation breaks down all major components and their interactions

### Scenario 6: Chart Analysis
**User Story**: As a data analyst, I want to understand trends in a chart screenshot.

**Steps**:
1. User opens Vision screen
2. Selects "chart" preset
3. Enters path to chart image
4. Optionally specifies focus area (trends, anomalies, comparisons)
5. Receives detailed analysis of data patterns

**Success Criteria**: Analysis identifies key trends, outliers, and insights

### Scenario 7: UI Diff Comparison
**User Story**: As a QA engineer, I want to compare two screenshots to find visual differences.

**Steps**:
1. User opens Vision screen
2. Selects "diff" preset
3. Enters path to expected/baseline image
4. Enters path to actual/current image
5. Optionally adds custom prompt
6. Receives list of differences with locations

**Success Criteria**: Differences are clearly identified with visual locations

### Scenario 8: Video Analysis
**User Story**: As a product manager, I want to get a summary of a demo video.

**Steps**:
1. User opens Vision screen
2. Selects "video" preset
3. Enters path to video file (MP4/MOV/M4V) or URL
4. Optionally customizes prompt
5. Receives video content summary

**Success Criteria**: Summary captures key actions and transitions in video

### Scenario 9: Cancel In-Progress Request
**User Story**: As a user, I want to cancel a long-running vision request.

**Steps**:
1. User submits a vision request
2. Loading indicator shows
3. User changes mind or realizes input was wrong
4. User presses Esc or Ctrl+C
5. Request is cancelled and user returns to input state

**Success Criteria**: Clean cancellation without error messages

### Scenario 10: Result Navigation and Copy
**User Story**: As a user, I want to navigate long results and copy portions to clipboard.

**Steps**:
1. Vision request completes with multi-paragraph result
2. User scrolls through result
3. User selects text to copy
4. User presses Ctrl+C to copy
5. Text is available in clipboard

**Success Criteria**: Full text selection and copy functionality works

---

## Acceptance Criteria

### Core Functionality

#### AC1: Vision Screen Navigation
- [ ] Vision screen accessible from main menu via F1 key
- [ ] Screen has consistent header with "Vision" title
- [ ] Esc key returns to main menu
- [ ] Screen layout follows TUI design standards

#### AC2: Image/Video Input
- [ ] File path input field accepts absolute and relative paths
- [ ] File path supports tab completion (if feasible in Textual)
- [ ] Input validation shows error for non-existent files
- [ ] Input validation shows error for unsupported file types
- [ ] Video commands accept both local files and URLs

#### AC3: Prompt Selection and Editing
- [ ] Preset dropdown with all 8 vision subcommands:
  - analyze
  - ui-to-code
  - extract-text
  - diagnose-error
  - diagram
  - chart
  - diff
  - video
- [ ] Default prompt pre-populated based on preset
- [ ] Prompt is editable for all presets
- [ ] Prompt field supports multi-line input
- [ ] Prompt history accessible (up/down arrows)

#### AC4: Command-Specific Options
- [ ] **ui-to-code**: Output type selector (code, prompt, spec, description)
- [ ] **extract-text**: Language hint input field
- [ ] **diagnose-error**: Context input field
- [ ] **diagram**: Diagram type dropdown or input
- [ ] **chart**: Focus area input field
- [ ] **diff**: Two file path inputs (expected, actual)
- [ ] **video**: Video source input (file or URL)

#### AC5: Request Submission
- [ ] Enter key submits form
- [ ] Submit button also available for mouse users
- [ ] Validation prevents submission without required fields
- [ ] Clear loading indicator during processing
- [ ] Timeout after 120 seconds with error message

#### AC6: Result Display
- [ ] Results displayed in scrollable text area
- [ ] Code output syntax highlighted when applicable
- [ ] Markdown rendering for formatted responses
- [ ] Word wrapping for long lines
- [ ] Status line shows processing time

#### AC7: Error Handling
- [ ] File not found: Clear error with file path
- [ ] File too large: Error with size limit info
- [ ] Invalid file type: Error with supported types
- [ ] API error: User-friendly error message
- [ ] Network timeout: Clear timeout message with retry option
- [ ] Auth error: Message suggesting to check API key

### File Size and Type Constraints
- [ ] Images: Max 5MB
- [ ] Videos: Max 8MB
- [ ] Supported image formats: JPG, PNG, JPEG
- [ ] Supported video formats: MP4, MOV, M4V
- [ ] URLs accepted for video source

### User Experience
- [ ] Keyboard shortcuts documented on screen
- [ ] Help text accessible via F1 or ? key
- [ ] Examples shown for each preset
- [ ] Previous results remain visible until new submission
- [ ] Clear visual distinction between input and output areas

---

## E2E Test Requirements

### Test Environment Setup
- Mock Vision API server for deterministic responses
- Test images directory with various image types
- Test video file (small MP4)
- Invalid/corrupt test files for error cases

### E2E Test Cases

#### Test Suite 1: Screen Navigation
1. **Navigate to Vision screen**
   - Start TUI, press F1
   - Verify Vision screen title visible
   - Verify preset dropdown has "analyze" selected

2. **Return to main menu**
   - From Vision screen, press Esc
   - Verify main menu displayed

#### Test Suite 2: Analyze Preset
3. **Successful analyze request**
   - Enter valid image path
   - Keep default prompt
   - Press Enter
   - Verify loading indicator shows
   - Verify result displayed
   - Verify result contains image description

4. **Custom prompt**
   - Enter valid image path
   - Change prompt to custom text
   - Press Enter
   - Verify result reflects custom prompt

#### Test Suite 3: UI-to-Code Preset
5. **Default ui-to-code request**
   - Select "ui-to-code" preset
   - Enter valid UI screenshot path
   - Keep default output type "code"
   - Press Enter
   - Verify code output syntax highlighted

6. **Different output types**
   - For each output type (code, prompt, spec, description):
     - Select output type
     - Submit request
     - Verify output format matches selection

#### Test Suite 4: Extract-Text Preset
7. **OCR without language hint**
   - Select "extract-text" preset
   - Enter code/terminal screenshot path
   - Submit
   - Verify text extracted with formatting

8. **OCR with language hint**
   - Select "extract-text" preset
   - Enter language (e.g., "python")
   - Submit
   - Verify extraction considers language

#### Test Suite 5: Diagnose-Error Preset
9. **Error diagnosis without context**
   - Select "diagnose-error" preset
   - Enter error screenshot path
   - Submit
   - Verify error explanation and fixes shown

10. **Error diagnosis with context**
    - Select "diagnose-error" preset
    - Enter error screenshot path
    - Enter context (e.g., "during deployment")
    - Submit
    - Verify context incorporated in response

#### Test Suite 6: Diagram Preset
11. **Diagram analysis without type**
    - Select "diagram" preset
    - Enter diagram image path
    - Submit
    - Verify diagram explanation

12. **Diagram analysis with type hint**
    - Select "diagram" preset
    - Enter diagram type (e.g., "sequence")
    - Submit
    - Verify type-specific terminology used

#### Test Suite 7: Chart Preset
13. **Chart analysis without focus**
    - Select "chart" preset
    - Enter chart image path
    - Submit
    - Verify general analysis

14. **Chart analysis with focus**
    - Select "chart" preset
    - Enter focus (e.g., "trends")
    - Submit
    - Verify focused analysis

#### Test Suite 8: Diff Preset
15. **Successful diff**
    - Select "diff" preset
    - Enter expected image path
    - Enter actual image path
    - Submit
    - Verify differences listed

16. **Diff with custom prompt**
    - Select "diff" preset
    - Enter both image paths
    - Enter custom prompt
    - Submit
    - Verify custom prompt reflected

#### Test Suite 9: Video Preset
17. **Video file analysis**
    - Select "video" preset
    - Enter local video file path
    - Submit
    - Verify video summary

18. **Video URL analysis**
    - Select "video" preset
    - Enter video URL
    - Submit
    - Verify video summary

#### Test Suite 10: Error Handling
19. **File not found**
    - Enter non-existent file path
    - Submit
    - Verify clear error message

20. **File too large**
    - Submit image > 5MB
    - Verify error with size limit

21. **Invalid file type**
    - Submit unsupported format (e.g., .gif)
    - Verify error with supported types

22. **API timeout**
    - Mock API timeout
    - Submit request
    - Verify timeout message with retry option

23. **Auth error**
    - Mock API auth failure
    - Submit request
    - Verify helpful auth error message

#### Test Suite 11: User Experience
24. **Cancel request**
    - Submit request
    - Press Esc during loading
    - Verify returns to input state cleanly

25. **Preset switching**
    - Select different presets
    - Verify default prompt changes
    - Verify relevant options show/hide

26. **Help access**
    - Press F1 or ? on Vision screen
    - Verify help overlay shows
    - Verify all keyboard shortcuts listed

#### Test Suite 12: Edge Cases
27. **Empty prompt**
    - Clear prompt field
    - Submit
    - Verify validation error or default used

28. **Very long prompt**
    - Enter 1000+ character prompt
    - Submit
    - Verify request succeeds

29. **Special characters in prompt**
    - Enter prompt with quotes, brackets, etc.
    - Submit
    - Verify proper handling

30. **Whitespace-only paths**
    - Enter spaces in path field
    - Submit
    - Verify validation error

---

## Implementation Notes

### UI Components Needed
- Preset selector (dropdown)
- File path input (with validation)
- Prompt textarea (multi-line)
- Optional option fields (conditional display based on preset)
- Submit button
- Loading indicator
- Result display area (scrollable, syntax highlighting)
- Error message area

### Preset to Option Mapping
| Preset | Required Options | Optional Options |
|--------|-----------------|------------------|
| analyze | image | prompt |
| ui-to-code | image | prompt, outputType |
| extract-text | image | prompt, language |
| diagnose-error | image | prompt, context |
| diagram | image | prompt, diagramType |
| chart | image | prompt, focus |
| diff | expectedImage, actualImage | prompt |
| video | video | prompt |

### API Integration
- Use `ZaiClient.vision_analyze()` for analyze
- Use `ZaiClient.vision_ui_to_artifact()` for ui-to-code
- Use `ZaiClient.vision_extract_text()` for extract-text
- Use `ZaiClient.vision_diagnose_error()` for diagnose-error
- Use `ZaiClient.vision_diagram()` for diagram
- Use `ZaiClient.vision_chart()` for chart
- Use `ZaiClient.vision_diff()` for diff
- Use `ZaiClient.vision_video()` for video

### Default Prompts (from reference)
```python
DEFAULT_PROMPTS = {
    "analyze": "Describe this image in detail.",
    "ui-to-code": "Convert this UI to production-ready code.",
    "extract-text": "Extract all text from this image.",
    "diagnose-error": "Diagnose this error and suggest fixes.",
    "diagram": "Explain this technical diagram.",
    "chart": "Analyze this data visualization.",
    "diff": "Compare these two UI screenshots and identify differences.",
    "video": "Analyze this video content.",
}
```

---

## Success Metrics
- All 8 vision subcommands functional in TUI
- Average time from screen open to result < 10 seconds (excluding API time)
- Zero crashes on valid input
- Clear, actionable error messages for all failure modes
- Keyboard-only operation fully supported

## Log

### [PM] 2026-03-19
- Reviewed groomed specification
- All 270 tests pass
- Linting passes (ruff check goz/)
- Issue accepted and moved to .done.md
