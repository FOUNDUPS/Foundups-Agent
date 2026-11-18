# RedDog VSIX Package EOL Reproducibility Phase 1

## Problem

The same merged Git tree produced three package-surface byte observations:

- 965,296 bytes after a normal Windows `core.autocrlf=true` checkout;
- 965,288 bytes in a hybrid pre-commit worktree where one changed package file
  had not yet been rematerialized; and
- 945,025 bytes from canonical LF Git blobs.

The 67-file membership and 1 MiB cap remained valid. The exact raw-byte claim
was not portable because `vsce package` consumes extension-root working-tree
bytes.

## WSP_15 decision

Complexity `2`, importance `4`, deferability `5`, impact `4`: **15 / P1**.
The smallest sufficient layer is a tracked Git EOL policy plus a policy-bound
package receipt. A parallel packager would duplicate `vsce`, introduce new
archive lifecycle code, and still require canonical source materialization.

## Evidence and decision

Git's `gitattributes` contract states that `text eol=lf` keeps working-tree
line endings equal to LF index bytes regardless of platform configuration.
VS Code's official extension documentation defines `vsce package` in the
extension root as the packaging boundary.

RedDog therefore pins the exact packaged root JavaScript, JSON, README, Python,
and license inputs to LF and marks the packaged PNG non-text. Package surface
receipt v2 verifies declared and effective attributes, rejects CRLF and bare
CR, and binds the policy digest plus hashes/sizes for the sorted 67-member
surface. It also proves 66 text entries, one binary, stable `vsce` membership,
and the existing 1 MiB cap while retaining raw bytes only as an observation.

## Boundaries

This phase adds no dependency, alternate packager, runtime import, provider
call, model/worker action, repository effect, credential, or Holo operation.
Compressed archive bytes and SHA-256 remain artifact-specific and are verified
after each merged-main VSIX build.

## Sources

- https://git-scm.com/docs/gitattributes
- https://code.visualstudio.com/api/working-with-extensions/publishing-extension
