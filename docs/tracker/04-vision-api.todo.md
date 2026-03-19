# Issue 04: Vision API Implementation

## Status
.todo

## Description
Implement vision analysis API (image and video analysis via Z.AI).

## User Stories / Use Scenarios

1. **User analyzes a screenshot**
   - Runs: `goz vision analyze screenshot.png`
   - Gets description of what's in the image

2. **User converts UI to code**
   - Runs: `goz vision ui-to-code design.png`
   - Gets production-ready code for the UI

3. **User extracts text from image**
   - Runs: `goz vision extract-text code.png`
   - Gets all text from the image

4. **User diagnoses error screenshot**
   - Runs: `goz vision diagnose-error error.png`
   - Gets explanation and fix suggestions

## Tasks
1. Vision client with analyze method
2. Image source resolution (file paths, URLs)
3. Multimodal message building
4. Video support

## Acceptance Criteria
1. `goz vision analyze <image>` works with local files
2. `goz vision ui-to-code <image>` returns code
3. `goz vision extract-text <image>` returns text
4. `goz vision diagnose-error <image>` returns diagnosis
5. Images ≤5MB supported

## QA Requirements
- [ ] End-to-end: Analyze a test image
- [ ] End-to-end: Extract text from code screenshot
- [ ] Error handling: Invalid image path
- [ ] Error handling: Image too large

## Dependencies
Issue 03 (api client)

## Reference
zai-cli/packages/zai-cli/src/lib/api-client.ts (visionComplete)
zai-cli/packages/zai-cli/src/lib/image.ts
