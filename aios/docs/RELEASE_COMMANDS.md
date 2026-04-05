# Release Commands (v0.1.0)

```bash
cd /home/lohd/.openclaw/workspace-main

# sanity
cd aios
make test
make bench
make report

# tag release in repo root
cd ..
git tag -a v0.1.0 -m "AIOS v0.1.0"
git show v0.1.0 --stat --oneline
```

If you use remote:
```bash
git push origin master
git push origin v0.1.0
```
