.PHONY: demo bench report test learning replay-store store-prune

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
