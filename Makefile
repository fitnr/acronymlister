PIP ?= pip3.5
PYTHON ?= python3.5

CREATE = CREATE TABLE tmp ( \
	name VARCHAR(3) \
	); \
	CREATE TABLE acronyms ( \
		acronym VARCHAR(3), \
		link TEXT, \
		description TEXT, \
		tweeted VARCHAR(1) \
	)

.PHONY: all develop install

all: alpha.db

install develop: %: requirements.txt alpha.db
	$(PIP) -q install $(INSTALLFLAGS) -r $<
	$(PYTHON) setup.py $(SETUPFLAGS) $* $(INSTALLFLAGS)

alpha.db: alpha.txt
	sqlite3 $@ "$(CREATE);"
	sqlite3 $@ ".import '/dev/stdin' tmp" < $<
	sqlite3 $@ "CREATE TABLE combinations AS SELECT name, 0 tweeted FROM tmp;"
	sqlite3 $@ "DROP TABLE tmp;"
	$(PYTHON) aaa.py $@

alpha.txt:
	echo {A..Z}{A..Z}{A..Z} | tr ' ' '\n' > $@
