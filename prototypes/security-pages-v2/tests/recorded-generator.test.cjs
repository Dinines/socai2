'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');
const {spawnSync} = require('node:child_process');
const generator = require('../scripts/generate-socai2-recorded.cjs');
const script = path.resolve(__dirname, '../scripts/generate-socai2-recorded.cjs');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const plain = value => JSON.parse(JSON.stringify(value));

function temporaryFixture(t, overrides={}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'socai2-recorded-generator-'));
  t.after(() => fs.rmSync(dir, {recursive:true, force:true}));
  const database = overrides.database || {cases:[], runs:[], alerts:[], artifacts:[], run_steps:[]};
  const databaseBytes = Buffer.from(JSON.stringify(database, null, 2) + '\n');
  const manifest = {schema_version:'socai2.page-export.v1', batch_id:'unit-generator', source_environment:'unit-only', exported_at:'2026-11-05T12:00:00Z', source_sha256:hash(databaseBytes), input_kind:'synthetic', ...overrides.manifest};
  const files = {database:path.join(dir, 'database.json'), manifest:path.join(dir, 'manifest.json'), output:path.join(dir, 'recorded.js')};
  fs.writeFileSync(files.database, databaseBytes);
  fs.writeFileSync(files.manifest, JSON.stringify(manifest, null, 2) + '\n');
  return {files, dir, database, manifest};
}

test('generator accepts only three explicit file arguments and offers no overwrite switch', () => {
  assert.deepEqual(generator.parseArgs(['--database','db.json','--manifest','manifest.json','--output','out.js']), {database:'db.json',manifest:'manifest.json',output:'out.js'});
  assert.deepEqual(generator.parseArgs(['--help']), {help:true});
  for (const args of [[], ['db.json'], ['--database'], ['--database','db.json','--database','again.json'], ['--force','out.js'], ['--database','db.json','--manifest','m.json']]) assert.throws(() => generator.parseArgs(args));
});

test('manifest requires source identity, synthetic input declaration, SHA256 and timestamp timezone', t => {
  const {manifest} = temporaryFixture(t);
  assert.doesNotThrow(() => generator.validateManifest(manifest));
  for (const patch of [{source_sha256:null},{source_sha256:'A'.repeat(64)},{schema_version:'wrong'},{input_kind:'real'},{batch_id:' '},{source_environment:''},{exported_at:'2026-11-05T12:00:00'},{exported_at:'not-a-date'},{answer_key:{expected:'benign'}}]) assert.throws(() => generator.validateManifest({...manifest,...patch}));
});

test('generated JavaScript safely preserves HTML terminators and Unicode line separators', () => {
  const value={text:'</script><script>bad()</script>\u2028next\u2029line', cases:[]};
  const output=generator.serializeRecordedData(value);
  assert.doesNotMatch(output, /</);
  assert.doesNotMatch(output, /\u2028|\u2029/);
  assert.match(output, /\\u003c\/script>/);
  const sandbox={window:{}};vm.runInNewContext(output,sandbox);
  assert.deepEqual(plain(sandbox.window.socai2RecordedData),value);
});

test('wrong database hash and audit truth are rejected without creating a page artifact', t => {
  const wrong=temporaryFixture(t,{manifest:{source_sha256:'0'.repeat(64)}});
  assert.throws(() => generator.generate(wrong.files), /SHA256 does not match/);
  assert.equal(fs.existsSync(wrong.files.output),false);
  const truth=temporaryFixture(t,{database:{cases:[],runs:[],alerts:[],artifacts:[],run_steps:[],ground_truth:{answer:'benign'}}});
  assert.throws(() => generator.generate(truth.files), /Audit truth must remain separate/);
  assert.equal(fs.existsSync(truth.files.output),false);
});

test('invalid JSON errors do not echo source text', t => {
  const fixture=temporaryFixture(t);
  fs.writeFileSync(fixture.files.manifest, '{"sensitive":"unit-secret-placeholder"');
  assert.throws(() => generator.generate(fixture.files), error => error.message==='Manifest is not valid JSON.' && !error.message.includes('unit-secret-placeholder'));
  assert.equal(fs.existsSync(fixture.files.output),false);
});

test('real adapter generation keeps source bytes unchanged and emits a verifiable output receipt', t => {
  const {files}=temporaryFixture(t);
  const beforeDatabase=fs.readFileSync(files.database),beforeManifest=fs.readFileSync(files.manifest);
  const receipt=generator.generate(files);
  const output=fs.readFileSync(files.output);
  const sandbox={window:{}};vm.runInNewContext(output.toString('utf8'),sandbox);
  assert.deepEqual(plain(sandbox.window.socai2RecordedData.cases),[]);
  assert.deepEqual(plain(sandbox.window.socai2RecordedData.runs),[]);
  assert.deepEqual(fs.readFileSync(files.database),beforeDatabase);
  assert.deepEqual(fs.readFileSync(files.manifest),beforeManifest);
  assert.equal(receipt.source_sha256,hash(beforeDatabase));
  assert.equal(receipt.manifest_sha256,hash(beforeManifest));
  assert.equal(receipt.output_sha256,hash(output));
  assert.equal(receipt.output,path.resolve(files.output));
  assert.equal(receipt.counts.cases,0);
  assert.equal(receipt.counts.runs,0);
});

test('existing edited output and symlink output are never replaced', t => {
  const {files,dir}=temporaryFixture(t);
  const saved='Existing manually reviewed export.\n';fs.writeFileSync(files.output,saved);
  assert.throws(() => generator.generate(files), /Output already exists/);
  assert.equal(fs.readFileSync(files.output,'utf8'),saved);
  const link=path.join(dir,'linked.js'),before=fs.readFileSync(files.database);
  fs.symlinkSync(files.database,link);
  assert.throws(() => generator.generate({...files,output:link}), /Output already exists/);
  assert.deepEqual(fs.readFileSync(files.database),before);
  assert.equal(fs.lstatSync(link).isSymbolicLink(),true);
  assert.throws(() => generator.generate({...files,output:files.database}), /separate from both sources/);
});

test('CLI uses the actual adapter and prints only the receipt, never imported titles or bodies', t => {
  const title='</script>仅单元测试\u2028原件\u2029';
  const fixture=temporaryFixture(t,{database:{cases:[{id:'case-1',tenant_id:'tenant-1',title,handling_status:'new',severity:'high',current_assessment_id:null}],runs:[],alerts:[],artifacts:[],run_steps:[]}});
  const {files}=fixture;
  const result=spawnSync(process.execPath,[script,'--database',files.database,'--manifest',files.manifest,'--output',files.output],{encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
  assert.equal(result.stderr,'');
  const receipt=JSON.parse(result.stdout);assert.equal(receipt.counts.cases,1);
  assert.doesNotMatch(result.stdout,/仅单元测试|script>/);
  const output=fs.readFileSync(files.output,'utf8');assert.doesNotMatch(output,/<|\u2028|\u2029/);
  const sandbox={window:{}};vm.runInNewContext(output,sandbox);
  assert.equal(sandbox.window.socai2RecordedData.cases[0].title,title);
});

test('verified Case GET companion supplies freshness while per-run SQL remains separate', t => {
  const tenant_id='unit-tenant';
  const database={cases:[{id:'case-1',tenant_id,title:'unit',current_assessment_id:'judge-1'}],runs:[],alerts:[],artifacts:[],run_steps:[],case_assessments:[{id:'judge-1',tenant_id,case_id:'case-1',conclusion:'Unit saved judgment'}]};
  const f=temporaryFixture(t,{database}),api=Buffer.from(JSON.stringify([{method:'GET',path:'/api/v1/socai2/cases/case-1',status:200,body:{case:{id:'case-1',current_assessment_id:'judge-1'},current_assessment:{value:{id:'judge-1'},input_freshness:{state:'stale',reasons:['unit_changed']}}}}])),sql=Buffer.from(JSON.stringify({state:'current',reasons:[]}));
  fs.writeFileSync(path.join(f.dir,'api-responses.json'),api);fs.writeFileSync(path.join(f.dir,'input-freshness.json'),sql);
  f.manifest.sources=[{role:'database',file:'database.json',sha256:f.manifest.source_sha256},{role:'api_responses',file:'api-responses.json',sha256:hash(api)},{role:'run_input_freshness',file:'input-freshness.json',sha256:hash(sql)}];
  fs.writeFileSync(f.files.manifest,JSON.stringify(f.manifest));generator.generate(f.files);
  const sandbox={window:{}};vm.runInNewContext(fs.readFileSync(f.files.output,'utf8'),sandbox);
  assert.equal(sandbox.window.socai2RecordedData.cases[0].assessment.inputFreshness.state,'stale');
  assert.equal(hash(fs.readFileSync(path.join(f.dir,'api-responses.json'))),hash(api));
});

test('companion hash, duplicate role and external paths fail before any output is created', t => {
  for(const change of ['hash','duplicate','path']){
    const f=temporaryFixture(t),api=Buffer.from('[]');fs.writeFileSync(path.join(f.dir,'api.json'),api);
    const entry={role:'api_responses',file:change==='path'?'../api.json':'api.json',sha256:change==='hash'?'0'.repeat(64):hash(api)};
    f.manifest.sources=change==='duplicate'?[entry,entry]:[entry];fs.writeFileSync(f.files.manifest,JSON.stringify(f.manifest));
    assert.throws(()=>generator.generate(f.files));assert.equal(fs.existsSync(f.files.output),false);
  }
});

test('separately generated batches register additively without replacing earlier records or local edits',()=>{
  const {adaptExport}=require('../socai2-recorded-import.js');
  const db={cases:[{id:'same-case',tenant_id:'same-tenant',title:'unit original'}],runs:[],alerts:[],artifacts:[],run_steps:[]};
  const base={schema_version:'socai2.page-export.v1',source_environment:'unit-only',exported_at:'2026-11-05T12:00:00Z',source_sha256:'a'.repeat(64),input_kind:'synthetic'};
  const a=adaptExport(db,{...base,batch_id:'unit-a'}),b=adaptExport(db,{...base,batch_id:'unit-b'}),sandbox={window:{}};
  vm.createContext(sandbox);vm.runInContext(fs.readFileSync(path.resolve(__dirname,'../socai2-recorded-import.js'),'utf8'),sandbox);
  vm.runInContext(generator.serializeRecordedData(a),sandbox);const store={cases:[{id:'legacy',title:'legacy local edit'}]};sandbox.window.mergeSocai2RecordedData(store);store.cases.find(c=>c.id===a.cases[0].id).title='local edit A';
  vm.runInContext(generator.serializeRecordedData(b),sandbox);sandbox.window.mergeSocai2RecordedData(store);sandbox.window.mergeSocai2RecordedData(store);
  assert.equal(store.cases.length,3);assert.equal(store.cases.find(c=>c.id===a.cases[0].id).title,'local edit A');assert.equal(store.cases.find(c=>c.id===b.cases[0].id).title,'unit original');assert.equal(store.cases[0].title,'legacy local edit');assert.equal(sandbox.window.socai2RecordedDataSets.length,2);
});
