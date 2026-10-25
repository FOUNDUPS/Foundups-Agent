const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

test('temporal insights render external content as text and replace previous results', () => {
    const source = fs.readFileSync(path.join(__dirname, '../extension/src/quantum-temporal-interface.ts'), 'utf8');
    const start = source.indexOf('function updateTemporalInsights(insights)');
    assert.ok(start >= 0);
    const end = source.indexOf('</script>', start);
    assert.ok(end > start);
    const element = () => ({
        children: [],
        append(...children) { this.children.push(...children); },
        appendChild(child) { this.children.push(child); },
        replaceChildren() { this.children = []; },
        set innerHTML(value) { throw new Error('External content must not enter innerHTML'); },
    });
    const container = element();
    const context = vm.createContext({ document: {
        getElementById: () => container,
        createElement: element,
        createTextNode: text => ({ textContent: text }),
    } });
    vm.runInContext(source.slice(start, end), context);
    const attack = '<img src=x onerror=alert(1)>';
    const insight = { insight_type: attack, explanation: '<script>alert(1)</script>', confidence: 0.8 };
    context.updateTemporalInsights([insight]);
    assert.equal(container.children.length, 1);
    assert.equal(container.children[0].children[0].textContent, attack);
    assert.equal(container.children[0].children[2].textContent, insight.explanation);
    context.updateTemporalInsights([insight]);
    assert.equal(container.children.length, 1);
});
