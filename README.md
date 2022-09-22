Validatr
========

The high-level goal of this project is to create a data validation pipeline to gurantee that only high-quality working assets are delivered to labelers for annotation.


### Getting Started

### Running Tests

### Architecture

Validatr has two primary architectural components.

1. HTTP API -- Written with vanilla django class-based views.
2. Distributed Task Queue -- Written with Celery, the task queue is responsible for running pipeline actions, and calling webhooks.

### Security Concerns

### Scalability

### Monitoring

### Future work
