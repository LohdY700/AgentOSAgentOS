# Context Memory Architecture (v1)

## 3 tầng memory
- User memory: `/memories/users/{user_id}/...` (read-write, user-scoped)
- Agent memory: `/memories/agent/...` (read-write có kiểm soát)
- Organization memory: `/policies/...` (read-only)

## Read/Write policy
- Default: user-scoped trước.
- Shared/org memory: read-only.
- Ghi vào shared memory cần gate (approval hoặc background consolidation).

## Update mode
- Hot path: ghi nhanh trong phiên khi fact rõ ràng.
- Background consolidation: gom nhiều phiên, hợp nhất, tránh last-write-wins conflict.
