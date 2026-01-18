Responses

Copy as Markdown
Create responses with support for streaming, reasoning, prior response state, and optional Remote MCP tools.

Method: POST
See OpenAI docs: https://platform.openai.com/docs/api-reference/responses
cURL (non‑streaming)
curl http://localhost:1234/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "input": "Provide a prime number less than 50",
    "reasoning": { "effort": "low" }
  }'

Stateful follow‑up
Use the id from a previous response as previous_response_id.

curl http://localhost:1234/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "input": "Multiply it by 2",
    "previous_response_id": "resp_123"
  }'

Streaming
curl http://localhost:1234/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "input": "Hello",
    "stream": true
  }'

You will receive SSE events such as response.created, response.output_text.delta, and response.completed.