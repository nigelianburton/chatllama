# Chat bubble UI (SIMPLE)

## Overview
Chat message bubbles are implemented in [SIMPLE/column_chat_messages.py](../column_chat_messages.py). They render a bordered message container, optional attachments, optional details grid, and a top-left type label.

## Structure
- **Main rectangle**: no fill, no border; stretches to column width and fits content height.
- **Border frame**: 2px black border, 5px radius, 3px inner margin, fill color based on message type.
- **Content row**:
  - **Message text**: left aligned, wraps; expands horizontally; height fits text or attachments.
  - **Attachment strip** (optional): right aligned, horizontal stack; each thumbnail is 32x32 with 3px padding.
- **Details grid** (optional): two-column layout, hidden by default; 3px padding; can be shown to display MCP request/response pairs.
- **Type label**: 8pt text, white background, 3px padding; drawn on top-left of the main rectangle.

## Usage
Create bubbles via the factory:
- `create_message_widget(MessageType.USER, text, attachments=None)`
- `create_message_widget(MessageType.ASSISTANT, text)`
- `create_message_widget(MessageType.MCP_REQUEST, text)`
- `create_message_widget(MessageType.MCP_UI_REQUEST, text)`
- `create_message_widget(MessageType.THINKING, text)`
- `create_message_widget(MessageType.MCP_RESPONSE, text)`
- `create_message_widget(MessageType.MCP_UI_RESPONSE, text)`
- `create_message_widget(MessageType.ERROR, text)`
- `create_message_widget(MessageType.PROGRESS, text)`

Streaming text:
- Use `MessageBubble.append_text(chunk)` to append streamed text to the current assistant bubble.

Attachments:
- Pass `attachments=[Path(...), ...]` (image paths). Each image is rendered as a 32x32 thumbnail.

Details:
- Call `MessageBubble.set_details([("Key", "Value"), ...])` to populate the two-column grid.
- Call `MessageBubble.set_details_visible(True/False)` to show or hide the grid.
