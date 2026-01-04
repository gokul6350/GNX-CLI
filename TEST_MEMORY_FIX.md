# Memory and Context Fix Verification

I have applied a fix to the `GNX Engine` to resolve the issue where the AI was forgetting context, specifically screenshots and tool outputs, between turns.

## The Issue
Previously, the engine was only storing the User's input and the AI's final text response in the chat history. The intermediate steps—such as tool calls (e.g., `computer_screenshot`, `mobile_control`) and their results (including the actual images)—were being discarded after each turn.

This caused the AI to:
1. "Forget" it had taken a screenshot.
2. Lose access to the image data for comparison in the next turn.
3. Claim it didn't have a chat history of actions.

## The Fix
1. **Updated `NativeToolAdapter`**: Modified to return the **full conversation history** (including all tool calls and results) instead of just the final answer.
2. **Updated `GNXEngine`**: Modified to store this full history. Now, when you ask "try again", the AI has the complete record of what it just did and saw.
3. **Increased Context**: Bumped `MAX_IMAGES_IN_CONTEXT` from `1` to `3`. The AI can now retain the last 3 screenshots in its active memory, allowing for better multi-step reasoning and comparisons.

## How to Verify
1. Restart the GNX CLI.
2. Run a command that involves a screenshot, e.g., `computer_screenshot`.
3. Ask a follow-up question about that screenshot, e.g., "What did you just see?".
4. The AI should now be able to reference the previous action and image.
5. Try the calculator task again. If it fails to see the app, ask it to "look again" or "try the mobile app", and it should retain the context of the previous attempt.
