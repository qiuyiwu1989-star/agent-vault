import test from 'node:test';
import assert from 'node:assert/strict';
import { COLORS, DEFAULT_COLOR, colorKey } from '../src/colors.js';
test('five stable selectable colors and safe legacy fallback',()=>{
  assert.deepEqual(Object.keys(COLORS),['yellow','coral','mint','blue','violet']);
  assert.equal(colorKey(undefined),DEFAULT_COLOR);
  assert.equal(colorKey('coral'),'coral');
  assert.equal(colorKey('not-a-color'),DEFAULT_COLOR);
});
