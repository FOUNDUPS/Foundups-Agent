;; Source semantics of the pinned 41-byte pilot-add.wasm; no model or AI runtime.
;; Binary SHA-256: f61fd62f57c41269c3c23f360eeaf1090b1db9c38651106674d48bc65dba88ba
(module
  (func (export "add") (param i32 i32) (result i32)
    local.get 0
    local.get 1
    i32.add))
