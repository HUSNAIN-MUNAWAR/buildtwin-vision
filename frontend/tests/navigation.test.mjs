import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
const source=fs.readFileSync(new URL("../src/components/AppShell.tsx", import.meta.url),"utf8");
test("operations navigation exposes required modules",()=>{
  for (const item of ["Command Center","Digital Twin","4D Schedule","Progress Review","Change Analysis","Safety","Quality","Risk Forecast","Reports","Cameras","Alerts","Audit Log"]) assert.ok(source.includes(item));
});
