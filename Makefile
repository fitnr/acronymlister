.PHONY: develop install

install develop: %:
	python setup.py $(SETUPFLAGS) $* $(PYTHONFLAGS)

CREATE = CREATE TABLE tmp ( \
	name VARCHAR(3) \
	); \
	CREATE TABLE acronyms ( \
		acronym VARCHAR(3), \
		link TEXT, \
		description TEXT, \
		tweeted VARCHAR(1) \
	)

alpha.db: alpha.txt
	sqlite3 $@ "$(CREATE);"
	sqlite3 $@ ".import '/dev/stdin' tmp" < $<
	sqlite3 $@ "CREATE TABLE combinations AS SELECT name, 0 tweeted FROM tmp;"
	sqlite3 $@ "DROP TABLE tmp;"

alpha.txt:
	echo {A..Z}{A..Z}{A..Z} | tr ' ' '\n' > $@
