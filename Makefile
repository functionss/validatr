# Runs end-to-end test suite.
# NOTE: this will take ~20s to run, as there are sleeps in every test.
test-e2e:
	@echo "Running e2e tests"
	docker exec -it validatr_app_1 python manage.py test validatr.api.tests_e2e


# Runs unit-ish tests inside the django container.
test:
	@echo "Running unit tests"
	docker exec -it validatr_app_1 python manage.py test validatr/pipeline

# Kicks off docker-compose stack
#    * postgres
#    * redis
#    * celery workers
#    * django app
server:
	@echo "Starting docker compose stack"
	docker-compose up --build
