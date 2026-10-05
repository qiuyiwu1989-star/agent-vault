import test from 'node:test';
import assert from 'node:assert/strict';
import { context, locate } from '../src/anchor.js';
test('Unicode positions and relocation across changed body', () => {
  const a=context('前言😀重点正文',2,5);
  assert.equal(a.quote,'😀重点');
  assert.deepEqual(locate('前言😀重点正文',a),{start:2,end:5,status:'exact'});
  assert.deepEqual(locate('新前言😀重点正文',a),{start:3,end:6,status:'relocated'});
});
test('ambiguous quote stays unresolved', () => {
  assert.equal(locate('重点 然后 重点',{quote:'重点'}).status,'unresolved');
});
test('bad range is rejected', () => assert.throws(()=>context('abc',2,1),RangeError));
