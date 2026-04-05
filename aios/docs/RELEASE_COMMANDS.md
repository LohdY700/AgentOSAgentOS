# Release Commands

## 1) Preflight (all releases)

```bash
cd /home/lohd/.openclaw/workspace-main/aios
make test
make bench
make report
```

## 2) Patch release (hotfix), ví dụ v0.1.1

```bash
cd /home/lohd/.openclaw/workspace-main
git tag -a v0.1.1 -m "AIOS v0.1.1"
git show v0.1.1 --stat --oneline
```

## 3) Minor release, ví dụ v0.2.0

```bash
cd /home/lohd/.openclaw/workspace-main
git tag -a v0.2.0 -m "AIOS v0.2.0"
git show v0.2.0 --stat --oneline
```

## 4) Push tags (nếu có remote)

```bash
git push origin master
git push origin v0.1.1
# hoặc
# git push origin v0.2.0
```
