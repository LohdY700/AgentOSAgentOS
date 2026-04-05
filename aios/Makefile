.PHONY: demo bench report test learning replay-store store-prune demo-lowram bench-lowram demo-throughput bench-throughput doctor ci-smoke release-check dashboard

PYTHONPATH_SRC=PYTHONPATH=src

demo:
	$(PYTHONPATH_SRC) python3 -m aios_core.cli demo

bench:
	$(PYTHONPATH_SRC) python3 -m aios_core.cli benchmark

report:
	python3 scripts/benchmark_report.py

test:
	$(PYTHONPATH_SRC) python3 -m unittest discover -s tests -v

learning:
	$(PYTHONPATH_SRC) python3 -m aios_core.cli --guard-config config/guard-learning.json demo

replay-store:
	$(PYTHONPATH_SRC) python3 -m aios_core.cli replay-store

store-prune:
	python3 scripts/prune_event_store.py --path data/events.jsonl --keep-last 1000

demo-lowram:
	$(PYTHONPATH_SRC) python3 -m aios_core.cli --store-config config/event-store.low-ram.json demo

bench-lowram:
	$(PYTHONPATH_SRC) python3 -m aios_core.cli --store-config config/event-store.low-ram.json benchmark

demo-throughput:
	$(PYTHONPATH_SRC) python3 -m aios_core.cli --store-config config/event-store.high-throughput.json demo

bench-throughput:
	$(PYTHONPATH_SRC) python3 -m aios_core.cli --store-config config/event-store.high-throughput.json benchmark

doctor:
	$(PYTHONPATH_SRC) python3 -m aios_core.cli doctor

ci-smoke:
	$(MAKE) test
	$(MAKE) doctor
	$(MAKE) bench

release-check:
	$(MAKE) ci-smoke
	$(MAKE) report
	$(MAKE) replay-store

dashboard:
	fuser -k 8787/tcp 2>/dev/null || true
	$(PYTHONPATH_SRC) python3 -m aios_core.cli dashboard --host 127.0.0.1 --port 8787
