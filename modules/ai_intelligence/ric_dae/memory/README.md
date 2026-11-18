# ricDAE Module Memory

This directory is the WSP 60 memory boundary for `ric_dae`.

The current module does not require checked-in session, cache, configuration,
or operational-log data. Runtime writers must create only the minimum required
subdirectory below this boundary, document its schema and retention policy,
and exclude generated or sensitive data from Git. Cross-module reads require a
public interface; this directory grants no direct access to another module's
memory.

Persistent behavior changes must be recorded in the module `ModLog.md`. Tests
must use temporary directories and must not treat this README as runtime state.
