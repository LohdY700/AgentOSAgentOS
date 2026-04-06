# Obsidian / Second Brain references (GitHub shortlist)

Đã quét GitHub theo từ khóa `obsidian second brain`, `obsidian rag`, `obsidian knowledge base ai`.

## Repos đáng tham khảo
- `khoj-ai/khoj` — https://github.com/khoj-ai/khoj
- `your-papa/obsidian-Smart2Brain` — https://github.com/your-papa/obsidian-Smart2Brain
- `ForLoopCodes/contextplus` — https://github.com/ForLoopCodes/contextplus
- `smixs/agent-second-brain` — https://github.com/smixs/agent-second-brain
- `ParthSareen/obsidian-rag` — https://github.com/ParthSareen/obsidian-rag

## Cách áp dụng vào AIOS
- Không phụ thuộc cloud trước: index markdown local từ Obsidian vault.
- Dùng `second-brain-index` để ingest markdown thành index JSONL.
- Dùng `second-brain-search` để truy xuất local trước khi gọi LLM, giảm token usage.
- Khi cần semantic search mạnh hơn, push chunk mới vào memory backend langchain (config bật/tắt).
