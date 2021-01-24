# Make a virtual env for running the app. This tries to use the initial venv setup as a make
# artefact so that subsequent venv invocations only need to install/check for updated dependecies.
# TODO; make it actually work, doesn't on my end.
VENV_DIR:=".venv.d"
VENV_BIN_DIR:=$(VENV_DIR)/bin
# Indicates that the step is "build".
VENV_REQUIREMENTS:=requirements.txt
VENV_MARKER:=$(VENV_DIR)/.venv.init
VENV_BIN_MARKER:=$(VENV_BIN_DIR)/.venv.init

# Nice venv command name.
.PHONY: venv
venv: $(VENV_MARKER)

# Actual venv artefact.
$(VENV_BIN_MARKER):
	@printf "\e[36m--- Creating runtime venv ---\e[39m\n"
	python3 -m venv $(VENV_DIR)
	bash -c "source $(VENV_BIN_DIR)/activate && python -m pip install --upgrade pip setuptools wheel"
	touch $(VENV_BIN_MARKER)
	@printf "\e[36m--- Finished runtime venv ---\e[39m\n"

# Actual venv artefact but with deps installed/updated.
$(VENV_MARKER): $(VENV_REQUIREMENTS) | $(VENV_BIN_MARKER)
	@printf "\e[36m--- Installing runtime deps ---\e[39m\n"
	bash -c "source $(VENV_BIN_DIR)/activate && pip install -r $(VENV_REQUIREMENTS)"
	touch $(VENV_MARKER)
	@printf "\e[36m--- Finished runtime deps ---\e[39m\n"


# Interactive.

.PHONY: python
python:
	bash -c "source $(VENV_BIN_DIR)/activate && \
	export PYTHONPATH=\$${PYTHONPATH:+\$$PYTHONPATH:}src && \
	exec python"

.PHONY: bash
bash:
	bash -c "source $(VENV_BIN_DIR)/activate && \
	export PYTHONPATH=\$${PYTHONPATH:+\$$PYTHONPATH:}src && \
	exec bash"

.PHONY: run
run:
	bash -c "source $(VENV_BIN_DIR)/activate && \
	export PYTHONPATH=\$${PYTHONPATH:+\$$PYTHONPATH:}src && \
	python -m ikabot"


# Clean.

.PHONY: clean
clean:
	$(RM) -r $(VENV_DIR)
