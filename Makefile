.PHONY: setup run test lint docker-build docker-run bq-run analysis clean

setup:            ## install pipeline + dev + analysis dependencies
	pip install -r requirements-dev.txt

run:              ## full pipeline on local DuckDB: ingest -> dbt build -> export
	python -m pipeline run

test: lint        ## unit tests + end-to-end run
	pytest -q
	python -m pipeline run

lint:
	ruff check pipeline tests

docker-build:
	docker build -t qsr-pipeline .

docker-run: docker-build   ## same as CI: run the container against DuckDB
	mkdir -p warehouse exports
	docker run --rm --user "$$(id -u):$$(id -g)" \
	  -v "$$PWD/data/landing:/app/data/landing:ro" \
	  -v "$$PWD/warehouse:/app/warehouse" -v "$$PWD/exports:/app/exports" \
	  qsr-pipeline run

bq-run:           ## run against BigQuery with your gcloud login (gcloud auth application-default login)
	WAREHOUSE=bigquery GCP_PROJECT=$${GCP_PROJECT:?set GCP_PROJECT} python -m pipeline run

analysis:         ## re-execute the analysis notebook against the warehouse
	jupyter nbconvert --to notebook --execute --inplace analysis/revenue_growth_analysis.ipynb

clean:
	rm -rf warehouse dbt/target dbt/logs .pytest_cache
