Validatr
========

The high-level goal of this project is to create a data validation pipeline to gurantee that only high-quality working assets are delivered to labelers for annotation.

### Getting Started

To get started with this repository, you'll need to make sure that you've got [Docker Compose](https://docs.docker.com/compose/) installed.

We use `docker compose` to spin-up the entire stack; including Postgresql, Redis, Celery Workers, and a Django HTTP API.

Everything is configured via environment variables, so the first thing you'll want to do is copy the `.env-example` file to `.env-docker`, and customize any values you'd like changed

```shell
cp .env-example .env-docker
```

Now that everything is configured, you'll want to build docker container images and run components of the Validatr system. This can take a few minutes, as you'll be downloading all of the dependencies before the first run, but you do it all with this single command:

```shell
make server
```

### Running Tests

This project is lightly tested using a small functional test suite, as well as a full end-to-end integration test suite.

You can kick off the functional tests by running the following command:

```shell
make test
```

You can kick off the end-to-end integration tests using the following command:

```shell
make test-e2e
```

### API Tour

* **Asset Index** -- non-paginated list of assets, and errors if they exist http://localhost:8000/assets/

```shell
curl http://localhost:8000/assets/
```

* **Asset GET:** -- fetch a specific asset by id, along with its status and errors http://localhost:8000/assets/:uuid

``` shell
# replace uuid with a real id from your environment.
curl http://localhost:8000/assets/image/7500c31e-42f4-4f96-860b-bbc57f3beb77
```

* **Create Asset:** -- POST to this endpoint to create a new asset http://localhost:8000/assets/image

``` shell
curl --request POST 'http://localhost:8000/assets/image/' \
--header 'Content-Type: application/json' \
--data-raw '{
	"assetPath": {
		"location": "local",
		"path": "/Users/jakedahn/Desktop/projects/validatr/assets/200-ok.jpg"
	},
	"notifications": {
		"onStart": "https://requestbin.io/wtn344wt",
		"onSuccess": "https://requestbin.io/tvn363tv",
		"onFailure": "https://requestbin.io/11fq7f41"
	}
}'

# returns:
# => {"id":"7500c31e-42f4-4f96-860b-bbc57f3beb77","state":"queued"}
```

### Architecture

Validatr is comprised of two primary components.

1. **HTTP API** -- Written with [Django](https://www.djangoproject.com/) and [Django Rest Framework](https://www.django-rest-framework.org/).

  * Data is persisted to Postgresql
  * HTTP request bodies, and responses are validated and structured using Django Rest Framework serializers [validatr/api/assets/serializers.py](https://github.com/functionss/validatr/blob/main/validatr/api/assets/serializers.py)
  * HTTP endpoints are implemented as Django Rest Framework Viewsets: [validatr/api/assets/views.py](https://github.com/functionss/validatr/blob/main/validatr/api/assets/views.py)

2. **Distributed Task Queue** -- Written with [Celery](https://docs.celeryq.dev/en/stable/getting-started/introduction.html)

  * The task queue is responsible for both running the validation pipeline, as well as reporting statuses to webhook endpoints.
  * The "pipeline" is several Celery tasks chained together.
  * Each validation step is its own Celery task.
  * [Redis](https://redis.io/) is being used as the queue backend for Celery.
  * Tasks and pipeline are all implemented in [validatr/pipeline/tasks.py](https://github.com/functionss/validatr/blob/main/validatr/pipeline/tasks.py)

### Security Concerns

* **No Authentication.** -- As this was implemented for a take-home technical test, there is zero user authentication in the app itself, as well as the backing services (redis + postgres). This would need to be addressed before deploying to production.

* **Webhook Abuse** -- If this were a public service, I would want to monitor webhook usage, and ensure that the distributed task queue system isn't being abused by malicious use. An attacker could spam the creation of assets that send thousands of requests to the defined webhook endpoints.


### Scalability

The primary reason I chose an HTTP API and a distributed task queue was the ease of scaling.

With the naiive minimal codebase as-is, you would probably get 500-1000 API requests and celery validations per second, if you ran everything on a small AWS/GCP instance (t3.small/n2-standard-2) -- something like 2vcpu and 2gb ram.

To scale further, I would vertically scale, by using a more powerful AWS/GCP instance (t3.2xlarge / n2-standard-8) -- something like 8vcpu, 32gb ram. My guess is this would get you to the 5000 API request/celery validations per second range.

To scale further, I would begin to scale horizontally. This means running multiple django HTTP API instances behind a load balancer, adding more dedicated celery worker hosts, moving db to a dedicated/hosted service like RDS/CloudSQL. The horizontal scaling strategy should get to 20,000-50,000 requests/validations per second.

Going beyond this, I think we would probably want to explore a fundamental redesign. Pushing beyond this point with python web apps can be tedious and painful -- so it could be better to rewrite in a more performant language like rust or golang. Perhaps investigate an autoscaling kinesis/kafka ingest, with s3 persistence, and serverless lambda processing.

### Monitoring

If I were to implement monitoring for this project, I would start with the ["Four Golden Signals"](https://sre.google/sre-book/monitoring-distributed-systems/), and focus on Latency, Traffic, Errors, and Saturation.

These concerns typically boil down to some of the following metrics:

* **HTTP Metrics** - per-request latency, p95 latency, request counter, error counter (split up 4xx and 5xx errors), etc.
* **User Experience Metrics** - p95 latency, apdex score, uptime, availability, etc
* **Standard host metrics** - cpu utilization, ram utilization, disk use, disk io, disk iops, etc.
* **Task Queue Metrics** - task count (per-task and total sum), runtime per task, runtime for end-to-end pipeline, error counts, etc.


### Future work

If I were to contine iterating on this project, there are a handful of improvements I would make.

* **CI/CD Pipeline.** The next thing I would want to do is setup a CI/CD pipeline using github actions, travis, or circleci.
* **More frontend validation.** The user experience of enqueueing an asset for validation, and then not finding out the URL/path was incorrect can be frustrating. Reachability should be validated at the time of queueing.
* **Improve DB reads.** Each task does an asset lookup from the db, if we were having db load issues, it might make more sense to serialize the asset record once, and pass it around between tasks.
* **Alternate storage backends.** Right now image assets must be on the local filesystem, but it'd be nice pull from an object store (S3 or GCS), or even download assets from remote URLs.