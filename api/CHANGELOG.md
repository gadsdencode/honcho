# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.0.3] — 2024-02-15

### Added

* Collections table to reference a collection of embedding documents
* Documents table to hold vector embeddings for RAG workflows
* Local scripts for running a postgres database with pgvector installed
* OpenAI Dependency for embedding models
* PGvector dependency for vector db support

### Changed

* session_data is now metadata
* session_data is a JSON field used python `dict` for compatability


## [0.0.2] — 2024-02-01

### Added

* Pagination for requests via `fastapi_pagination`
* Metamessages
* `get_message` routes
* `created_at` field added to each Table
* Message size limits

### Changed

* IDs are now UUIDs
* default rate limit now 100 requests per minute

### Removed

* Removed messages from session response model


## [0.0.1] — 2024-02-01

### Added

* Rate limiting of 10 requests for minute
* Application level scoping

