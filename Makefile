PY ?= python
BLENDER ?= blender

.PHONY: setup env stills render assemble qa clean

setup:
	$(PY) scripts/fetch_source.py
	$(PY) scripts/check_env.py

env:
	$(PY) scripts/check_env.py

stills:
	$(BLENDER) -b --factory-startup --python blender/build.py -- open --stills 1,80,170

render:
	$(PY) tools/render_all.py --workers 3

assemble:
	$(PY) tools/assemble.py

qa:
	$(PY) tools/qa.py

clean:
	rm -rf out
