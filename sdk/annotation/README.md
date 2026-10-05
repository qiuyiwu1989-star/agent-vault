# Web Annotation SDK (0.1.0 local prototype)

A host page mounts the SDK on one article element and supplies a stable `{namespace,id,revision}` plus three asynchronous methods: `list(identity)`, `create(identity,annotation)`, and `update(identity,note,change)`. The SDK owns selection, side panel, saved-note list and CSS highlights. The host owns authentication and storage. Call `destroy()` when leaving a client-side route; call `refresh()` when article text or saved notes change.

```js
import {mountAnnotations} from './src/index.js';
const instance=await mountAnnotations({
  container:document.querySelector('article'),
  document:{namespace:'example',id:'article-42',revision:'v1'},
  api:{list:async()=>[],create:async(_,note)=>save(note),update:async(_,note,change)=>edit(note.id,change)}
});
```

Offsets are Unicode code points. Saved records should include `quote`, `prefix`, `suffix`, `start`, `end`, content revision and owner scope. Ambiguous relocation remains unresolved. Styling is isolated in Shadow DOM and saved text enters the UI via `textContent`. CSS Highlight is used when available; the notes list remains usable in browsers without it. The host must choose a stable article container and must authorize every server request.

`examples/vault-adapter.js` maps the SDK to Vault's authenticated, owner-scoped `/api/inside/annotations/v1` service. The host adapter resolves a selected quote uniquely against the server's canonical text and rejects ambiguous selections. The legacy Vault knowledge-note API remains separate. The initial production database was verified to have zero legacy notes before deployment; future migration must reconcile nonzero legacy rows by owner.

Run tests: `node --test test/*.test.js`. This directory is intentionally local to the Vault repository until a second host integrates through the public SDK interface and the project is split out.
