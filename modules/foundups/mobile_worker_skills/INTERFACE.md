# Mobile worker skills interface

This is a collection of worker instructions and JSON contracts, not a deployed
phone agent or autonomous executor. The [README](README.md) owns skill selection,
device-import checks and the higher-layer/worker authority split. A parsed packet
or a worker's `scope_ok` field does not grant execution or publication authority.

The canonical [Draft 2020-12 schema](schemas/worker-handoff-pipeline.v1.schema.json)
defines six shapes under `$defs`: `ParserOutput`, `ScopeOutput`, `PacketOutput`,
`ResultOutput`, `PipelineEnvelopeV1`, and `HandoffValidationResult`. Each shape
rejects extra object properties. **Select the intended `$defs` fragment when
validating**: the schema's top level is a definitions container without a root
object constraint or `$ref`, so validating only that container does not validate
an envelope's fields.

`PipelineEnvelopeV1` requires version `1`, parser, scope and packet, with optional
result. Parser intent is read/edit/mixed/unclear; scope enumerates proposed worker
operations and non-goals; packets carry file boundaries and acceptance evidence.
Results classify pass/fail/partial/unknown. `HandoffValidationResult` requires
version `1`, a boolean, errors with stage/message, and warnings. Consult the
actual schema for complete required fields and length constraints.

The logical schema URI is not proof of a live validator service. Device Gallery
loading, on-device skill behavior and later execution require their own evidence;
raw Markdown availability and schema-valid JSON are insufficient. No device,
network contact, handoff dispatch or runtime worker was exercised for this change.
