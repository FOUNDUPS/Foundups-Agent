'use strict';

function deepFreeze(value) {
  if (!value || typeof value !== 'object' || Object.isFrozen(value)) return value;
  Object.values(value).forEach(deepFreeze);
  return Object.freeze(value);
}

function createOwnerProof(matchesReceipt) {
  if (typeof matchesReceipt !== 'function') {
    throw new TypeError('owner receipt matcher required');
  }
  const observed = new WeakSet();
  const verified = new WeakSet();
  return Object.freeze({
    observe(result) {
      deepFreeze(result);
      observed.add(result);
      if (matchesReceipt(result)) verified.add(result);
      return result;
    },
    isObserved(result) {
      return !!result && observed.has(result);
    },
    isAccepted(result) {
      return !!result && verified.has(result) && matchesReceipt(result);
    }
  });
}

module.exports = { createOwnerProof };
