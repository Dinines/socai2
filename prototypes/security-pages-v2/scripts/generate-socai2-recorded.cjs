#!/usr/bin/env node
/* Offline only: verified database export -> existing recorded-data page contract. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const USAGE = 'Usage: node scripts/generate-socai2-recorded.cjs --database DATABASE.json --manifest MANIFEST.json --output RECORDED.js';
const REQUIRED = ['database', 'manifest', 'output'];
const AUDIT_ONLY_KEYS = new Set(['truth', 'ground_truth', 'answer_key']);
const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function parseArgs(args) {
  if (args.length === 1 && args[0] === '--help') return {help: true};
  const options = {};
  for (let i = 0; i < args.length; i += 2) {
    const flag = args[i];
    const key = flag.startsWith('--') ? flag.slice(2) : '';
    if (!REQUIRED.includes(key)) throw new Error('Unknown argument. ' + USAGE);
    if (Object.hasOwn(options, key)) throw new Error('Duplicate argument: --' + key);
    if (!args[i + 1] || args[i + 1].startsWith('--')) throw new Error('Missing value for --' + key);
    options[key] = args[i + 1];
  }
  if (REQUIRED.some(key => !options[key])) throw new Error('All three file arguments are required. ' + USAGE);
  return options;
}

function validateManifest(manifest) {
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) throw new Error('Manifest must be a JSON object.');
  if (manifest.schema_version !== 'socai2.page-export.v1') throw new Error('Unsupported manifest schema_version.');
  for (const key of ['batch_id', 'source_environment']) {
    if (typeof manifest[key] !== 'string' || !manifest[key].trim()) throw new Error('Manifest requires a nonempty ' + key + '.');
  }
  if (typeof manifest.exported_at !== 'string' || !Number.isFinite(Date.parse(manifest.exported_at)) || !/(?:Z|[+-]\d{2}:\d{2})$/.test(manifest.exported_at)) {
    throw new Error('Manifest exported_at must be a timestamp with an explicit timezone.');
  }
  if (typeof manifest.source_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(manifest.source_sha256)) throw new Error('Manifest requires a lowercase SHA256 of the database file.');
  if (manifest.input_kind !== 'synthetic') throw new Error('This import requires explicitly identified synthetic inputs.');
  rejectAuditTruth(manifest);
}

function rejectAuditTruth(value) {
  if (value && typeof value === 'object' && Object.keys(value).some(key => AUDIT_ONLY_KEYS.has(key))) {
    throw new Error('Audit truth must remain separate from the database export and page manifest.');
  }
}

function parseJson(bytes, label) {
  try { return JSON.parse(bytes.toString('utf8')); }
  catch { throw new Error(label + ' is not valid JSON.'); }
}

function readSource(file, label) {
  try { return fs.readFileSync(file); }
  catch { throw new Error(label + ' could not be read.'); }
}

function serializeRecordedData(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Adapter did not return a recorded-data object.');
  const serialized = JSON.stringify(data, null, 2)
    .replace(/</g, '\\u003c')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
  return '/* Verified offline export; source records unchanged, no live requests. */\nwindow.socai2RecordedData = ' + serialized + ';\nwindow.socai2RecordedDataSets = [...(window.socai2RecordedDataSets || []), window.socai2RecordedData];\n';
}

function generate(options) {
  if (!options || REQUIRED.some(key => typeof options[key] !== 'string' || !options[key])) throw new Error('All three file paths are required.');
  const files = Object.fromEntries(REQUIRED.map(key => [key, path.resolve(options[key])]));
  if (files.database === files.output || files.manifest === files.output) throw new Error('Output must be a new file, separate from both sources.');
  const manifestBytes = readSource(files.manifest, 'Manifest');
  const manifest = parseJson(manifestBytes, 'Manifest');
  validateManifest(manifest);
  const databaseBytes = readSource(files.database, 'Database export');
  const sourceHash = sha256(databaseBytes);
  if (sourceHash !== manifest.source_sha256) throw new Error('Database SHA256 does not match the manifest.');
  const database = parseJson(databaseBytes, 'Database export');
  rejectAuditTruth(database);
  const related = [];
  if (manifest.sources !== undefined && !Array.isArray(manifest.sources)) throw new Error('Manifest sources must be an array.');
  const roles = new Set();
  for (const entry of manifest.sources || []) {
    if (!entry || !['database', 'api_responses', 'run_input_freshness', 'failure_classification', 'case_page_data'].includes(entry.role) || roles.has(entry.role)) throw new Error('Invalid or duplicate source role.');
    roles.add(entry.role);
    if (typeof entry.file !== 'string' || !/^[A-Za-z0-9_.-]+$/.test(entry.file) || ['.', '..'].includes(entry.file) || !/^[a-f0-9]{64}$/.test(entry.sha256 || '')) throw new Error('Source requires a local filename and SHA256.');
    const file = path.join(path.dirname(files.manifest), entry.file);
    if (fs.lstatSync(file).isSymbolicLink()) throw new Error('Source symlinks are not supported.');
    const bytes = readSource(file, 'Related source');
    if (sha256(bytes) !== entry.sha256) throw new Error('Related source SHA256 does not match the manifest.');
    if (entry.role === 'database' && (file !== files.database || entry.sha256 !== sourceHash)) throw new Error('Database source entry does not match the input.');
    related.push({file, hash: entry.sha256, role: entry.role, value: parseJson(bytes, 'Related source')});
  }
  const responses = related.find(item => item.role === 'api_responses')?.value || [];
  if (!Array.isArray(responses)) throw new Error('API responses must be an array.');
  // Load the real adapter only after the source identity has been verified.
  const {adaptExport} = require('../socai2-recorded-import.js');
  if (typeof adaptExport !== 'function') throw new Error('Recorded-data adapter is unavailable.');
  const pageData = related.find(item => item.role === 'case_page_data')?.value || [];
  if (!Array.isArray(pageData)) throw new Error('Case page data must be an array.');
  const data = adaptExport(database, manifest, responses, pageData);
  const output = serializeRecordedData(data);
  const manifestHash = sha256(manifestBytes);
  const assertUnchanged = () => {
    if (sha256(readSource(files.database, 'Database export')) !== sourceHash || sha256(readSource(files.manifest, 'Manifest')) !== manifestHash) {
      throw new Error('Source files changed during generation.');
    }
    if (related.some(item => sha256(readSource(item.file, 'Related source')) !== item.hash)) throw new Error('Related source changed during generation.');
  };
  assertUnchanged();
  let fd, created = false;
  try {
    // Atomic exclusive creation also rejects existing symlinks. No force mode.
    fd = fs.openSync(files.output, 'wx', 0o644);
    created = true;
    fs.writeFileSync(fd, output, 'utf8');
    fs.closeSync(fd);
    fd = undefined;
    assertUnchanged();
  } catch (error) {
    if (fd !== undefined) fs.closeSync(fd);
    if (created) fs.unlinkSync(files.output);
    if (error.code === 'EEXIST') throw new Error('Output already exists; refusing to replace it.');
    throw error;
  }
  const counts = Object.fromEntries(Object.entries(data).filter(([,value]) => Array.isArray(value)).map(([key,value]) => [key, value.length]));
  return {output: files.output, source_sha256: sourceHash, manifest_sha256: manifestHash, output_sha256: sha256(Buffer.from(output)), counts};
}

function main(args) {
  const options = parseArgs(args);
  if (options.help) { process.stdout.write(USAGE + '\n'); return; }
  process.stdout.write(JSON.stringify(generate(options)) + '\n');
}
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write('Recorded export generation failed: ' + error.message + '\n'); process.exitCode = 1; }
}
module.exports = {parseArgs, validateManifest, serializeRecordedData, generate};
