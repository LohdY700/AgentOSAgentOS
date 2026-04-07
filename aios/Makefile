.PHONY: demo bench report test learning replay-store store-prune demo-lowram bench-lowram demo-throughput bench-throughput doctor bench-memory bench-memory-check second-brain-index second-brain-search wiki-ingest wiki-index wiki-slide ci-smoke release-check dashboard

PYTHON_BIN:=$(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
PYTHONPATH_SRC=PYTHONPATH=src

demo:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli demo

bench:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli benchmark

report:
	$(PYTHON_BIN) scripts/benchmark_report.py

test:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m unittest discover -s tests -v

learning:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli --guard-config config/guard-learning.json demo

replay-store:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli replay-store

store-prune:
	$(PYTHON_BIN) scripts/prune_event_store.py --path data/events.jsonl --keep-last 1000

demo-lowram:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli --store-config config/event-store.low-ram.json demo

bench-lowram:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli --store-config config/event-store.low-ram.json benchmark

demo-throughput:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli --store-config config/event-store.high-throughput.json demo

bench-throughput:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli --store-config config/event-store.high-throughput.json benchmark

doctor:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli doctor

bench-memory:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli memory-benchmark --query "sếp" --loops 20

bench-memory-check:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) scripts/check_memory_benchmark.py --python $(PYTHON_BIN) --query "sếp" --loops 20 --threshold-ms 80

second-brain-index:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli second-brain-index

second-brain-search:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli second-brain-search --query "sếp" --limit 5

wiki-ingest:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli wiki-ingest --title "Demo Wiki" --content "Nội dung demo từ pipeline." --tags "demo,wiki"

wiki-index:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli wiki-index

wiki-slide:
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli wiki-slide --slug demo-wiki

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
	$(PYTHONPATH_SRC) $(PYTHON_BIN) -m aios_core.cli dashboard --host 127.0.0.1 --port 8787
