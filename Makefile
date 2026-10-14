.PHONY: help setup install run test db-upgrade clean

help:            ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: install   ## Instalar todo y arrancar la web (make setup)
	./run.sh

install:         ## Instalar dependencias y preparar la base (sin arrancar)
	./setup.sh --no-run

run:             ## Arrancar la web
	./run.sh

test:            ## Correr los tests
	./venv/bin/python -m pytest tests/ -q

usuario:         ## Crear/actualizar una cuenta (make usuario EMAIL=x@y.com NOMBRE="Ana Perez")
	./venv/bin/python create_user.py $(EMAIL) --nombre "$(NOMBRE)" --si

db-upgrade:      ## Aplicar migraciones pendientes
	./venv/bin/python -m flask --app app.py db upgrade

clean:           ## Borrar entorno virtual, cachés y logs (NO toca la base de datos)
	rm -rf venv
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
