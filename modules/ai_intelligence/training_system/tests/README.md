# Training adapter test scope

[test_utf8_import_boundary.py](test_utf8_import_boundary.py) contains seven tests:
callable imports from the launch/command/scanner owners, expected helper argument
names, a nonexistent-target scan and a summary with memory=None. The tests do not
invoke the training menu, automatic remediation, model training or clear-memory
action. Callable imports alone do not prove exclusion of every transitive import.

The file imports real modules, so review their current import boundaries before
a selected run. These checks do not validate corpus quality, persisted memory,
model availability or provider behavior. This documentation update did not
execute the tests or any operational entrypoint; it adds no placeholder tests.
