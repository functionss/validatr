Validatr
========

The high-level goal of this project is to create a data validation pipeline to gurantee that only high-quality working assets are delivered to labelers for annotation.

### Getting Started

The only prerequisite to getting started is to install `docker-compose`.

```shell
# Kicks off `docker-compose up --build`
make server
```

### Running Tests

To kick off the unit tests, simply run

```shell
make test
```

To run the end-to-end test suite, run

```shell
make test-e2e
```

### Architecture

Validatr is comprised of two primary components.

1. HTTP API -- Written with [Django](https://www.djangoproject.com/) and [Django Rest Framework](https://www.django-rest-framework.org/).

  * Data is persisted to Postgresql
  * Strict HTTP interface is enforced by [Serializers](https://github.com/functionss/validatr/blob/main/validatr/api/assets/serializers.py)
  * HTTP endpoints are implemented in [validatr/api/assets/views.py](https://github.com/functionss/validatr/blob/main/validatr/api/assets/views.py)

2. Distributed Task Queue -- Written with [Celery](https://docs.celeryq.dev/en/stable/getting-started/introduction.html)

  * The task queue is responsible for both running the validation pipeline, as well as reporting statuses to webhook endpoints.
  * Each validation step is its own Celery task.
  * [Redis](https://redis.io/) is being used as the queue backend for Celery.
  * Tasks and pipeline are all implemented in [validatr/pipeline/tasks.py](https://github.com/functionss/validatr/blob/main/validatr/pipeline/tasks.py)

### Security Concerns

Several security shortcuts were taken, as this was implemented as a proof-of-concept take-home technical test.

If this were a real project, some of my security concerns going forward would be:

* User authentication (either api keys, or JWT)


### Scalability

The chosen architecture of an HTTP API for customer use, and a distributed task queue for behind-the-scenes validation pipelines lends itself to simple scalability. Even with this current proof of concept, it should scale up to 1000-5000 requests per second with a fairly small postgres db, and single-node Redis server.

You could continue to scale out horizontally by using a larger database server, larger multi-node Redis cluster, and running several instances of the django HTTP API behind a load balancer. This would get you to the 20,000 request per second range.

For next-level scaling, a fundamental redesign would probably make sense. One idea I had for far-out scale would be to use a large-scale AWS Kinesis or DIY Kafka cluster as means of enqueueing assets (up to 1million writes per second). Then you could persist those keys to an object store like AWS S3, which supports mass parallelization.

### Monitoring

There is currently no monitoring, as this was implemented as a proof-of-concept take-home technical test.

However, if I were to roll this out to production, there are several metrics I would be interested in tracking; roughly following Google's SRE "Four Golden Signals" guidelines.

* *HTTP Metrics* - per-request latency, p95 latency, request counter, error counter (split up 4xx and 5xx errors), etc.
* *Standard host metrics* - cpu utilization, ram utilization, disk use, disk io, disk iops, etc.
* *Task Queue Metrics* - task count (per-task and total sum), runtime per task, runtime for end-to-end pipeline, error counts, etc.


### Future work

If I were to contine iterating on this project, there are a handful of improvements I would make.

* More frontend validation. The user experience of enqueueing an asset for validation, and then not finding out the URL/path was incorrect can be frustrating. Reachability should be validated at the time of queueing.
* Improve DB reads. Each task does an asset lookup from the db, if we were having db load issues, it might make more sense to serialize the asset record once, and pass it around between tasks.
