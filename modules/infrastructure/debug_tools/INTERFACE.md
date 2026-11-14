# Import diagnostic interfaces

[import_tracer.py](src/import_tracer.py) defines ImportTimer(MetaPathFinder),
whose find_spec(fullname, path, target=None) prints timing observations and returns
None to let ordinary import discovery continue. The reported interval runs from
the previous hook callback, not a fully isolated import duration.

[stderr_wrapper.py](src/stderr_wrapper.py) defines StderrWatchingFinder with the
same find_spec arguments. It records import names, reports the first observed
stderr replacement and returns None. The observation cannot identify the exact
statement that changed a stream.

Both modules install their finder into sys.meta_path and import repository main
at top level. They do not remove the finder afterward. Importing either module
runs the diagnostic and may execute main's transitive import effects. There is
no passive-library or bounded/no-write execution contract. No dedicated tracked
tests were found; documentation is based on source inspection, not a live run.
