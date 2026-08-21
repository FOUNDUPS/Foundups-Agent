'use strict';

const assert = require('assert');
const surface = require('./reddog_package_surface_contract');

const first = surface.runVsceList();
const second = surface.runVsceList();

assert.deepStrictEqual(second, first, 'two vsce listings must be byte-order stable');
assert.strictEqual(new Set(first).size, first.length, 'package surface must not contain duplicates');
assert.deepStrictEqual([...first].sort(), surface.EXPECTED_PACKAGE_FILES);
assert.strictEqual(first.length, 65);
const receipt = surface.packageSurfaceReceipt(first);
assert.strictEqual(receipt.file_count, 65);
assert.strictEqual(receipt.raw_byte_cap, 1024 * 1024);
assert.strictEqual(receipt.within_cap, true);

console.log('RedDog deterministic 65-file package surface: PASS ' + JSON.stringify(receipt));
