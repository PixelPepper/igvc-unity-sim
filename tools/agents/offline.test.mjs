import test from 'node:test';
import assert from 'node:assert/strict';
import { prepareTask, selectGrok } from './runner.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
test('catalog selects requested mode without silent effort fallback', () => {
  const models = [{id:'grok-4.6',displayName:'Grok 4.6',parameters:[{id:'fast',values:[{value:'true'},{value:'false'}]},{id:'reasoning_effort',values:[{value:'high'},{value:'medium'},{value:'low'}]}]}];
  assert.deepEqual(selectGrok(models), {id:'grok-4.6',params:[{id:'fast',value:'false'},{id:'reasoning_effort',value:'medium'}]});
  assert.deepEqual(selectGrok(models, {effort:'high',fast:true}), {id:'grok-4.6',params:[{id:'fast',value:'true'},{id:'reasoning_effort',value:'high'}]});
  assert.throws(() => selectGrok(models, {effort:'xhigh'}));
  assert.throws(() => selectGrok([{id:'auto',displayName:'Auto'}]));
  assert.throws(() => selectGrok([{id:'grok-4.6-fast',displayName:'Grok 4.6 Fast'}]));
});
test('template fits bounded numbered prompt', async () => {
  const task = await prepareTask(path.join(here,'review-motion.task.json'));
  assert.equal(task.files.length, 2);
  assert.ok(task.prompt.length <= 24000);
  assert.match(task.prompt, /1: /);
});
test('traversal is rejected before file access', async () => {
  const fixture = path.join(here, '.invalid-task-test.json');
  try {
    await fs.writeFile(fixture, JSON.stringify({instructions:'review',paths:['../secret.txt']}));
    await assert.rejects(prepareTask(fixture));
  } finally { await fs.unlink(fixture); }
});
