# PUBLISH_CHECK (60s)

## 1) Sanity
```bash
cd /home/lohd/.openclaw/workspace-main/aios
make release-check
```

## 2) Confirm release docs exist
- `docs/CHANGELOG.md`
- `docs/RELEASE_NOTES_v0.1.1.md`
- `docs/RELEASE_COMMANDS.md`
- `docs/LAUNCH_POST_SHORT_VN.md` (hoặc EN)

## 3) Confirm tags
```bash
cd /home/lohd/.openclaw/workspace-main
git tag --list "v0.1.*"
git show v0.1.1 --oneline --no-patch
```

## 4) Publish (nếu có remote)
```bash
git push origin master
git push origin v0.1.1
```

## 5) Post launch
- Chọn 1 bản ngắn: `docs/LAUNCH_POST_SHORT_VN.md` hoặc `docs/LAUNCH_POST_SHORT_EN.md`
- Chọn 1 bản dài: `docs/LAUNCH_POST_LONG_VN.md` hoặc `docs/LAUNCH_POST_LONG_EN.md`

Done.
