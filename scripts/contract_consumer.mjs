import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const metadata = JSON.parse(fs.readFileSync(path.join(root, 'schemas/boundary.json')));
const ajv = new Ajv2020({strict: false, allErrors: true, coerceTypes: false, useDefaults: false});
addFormats(ajv);
const validators = new Map(metadata.contracts.map(name => [name,
  ajv.compile(JSON.parse(fs.readFileSync(path.join(root, 'schemas', name + '.json'))))]));

function check(value) {
  if (typeof value === 'number' && (!Number.isFinite(value) ||
      (Number.isInteger(value) && !Number.isSafeInteger(value)))) throw Error('portable_number');
  if (typeof value === 'string' && !value.isWellFormed()) throw Error('unicode');
  if (!value || typeof value !== 'object') return;
  if (Array.isArray(value)) { value.forEach(check); return; }
  if ('envelope' in value && value.envelope.operation !== ('work_objective_id' in value ? 'discover' : 'event' in value ? 'report' : 'route')) throw Error('request_operation');
  if (value.schema_version === '2' && 'route_inputs' in value && value.route_inputs.catalog_query != null) throw Error('linked_catalog_query');
  if ('guidance_refs' in value) {
    const ids = value.guidance_refs.map(x => JSON.stringify([x.resource_id, x.revision]));
    if (ids.length > 2 || new Set(ids).size !== ids.length) throw Error('discovery_guidance_consistency');
  }
  if (value.details?.discovery_id) {
    if ((value.status === 'selected_guidance') !== (value.details.guidance_refs.length > 0)) throw Error('discovery_result_consistency');
    if (value.status === 'no_optional_guidance' && value.details.uncertainty.length) throw Error('incomplete_empty_discovery');
  }
  if (value.code === 'capability_mismatch' && 'effective' in value &&
      value.effective.some(x => !value.declared.includes(x) || !value.runtime.includes(x))) throw Error('effective_capabilities');
  if ('optional_guidance' in value) {
    const ids = [...value.optional_guidance, ...value.required_guidance].map(x => JSON.stringify([x.resource_id,x.revision]));
    const roles = value.optional_guidance.map(x => x.role);
    if (new Set(ids).size !== ids.length || new Set(roles).size !== roles.length ||
        (value.guidance_action === 'none') !== (value.optional_guidance.length === 0)) throw Error('guidance_consistency');
  }
  if (value.counting_semantics === 'subset' && value.parent_metric_id === null) throw Error('measurement_subset');
  if ('share_user_wide' in value && value.share_user_wide && !value.local_analysis_enabled) throw Error('learning_consent');
  if ('minimum_batch' in value && (value.action === 'record') !== (value.context !== null)) throw Error('learning_action');
  if ('experiment_state' in value) {
    if (['accepted','queued','running','completed','incomplete'].includes(value.experiment_state) &&
       (!value.authorization_revision || (value.execution_path === 'harness_assisted' && !value.host_accepted))) throw Error('experiment_authority');
    const ids = value.candidate_plans.map(x => x.execution_plan_id);
    const probs = value.assignment_probabilities;
    if (ids.length > value.limits.max_candidates || new Set(ids).size !== ids.length) throw Error('experiment_authority');
    if (Object.keys(probs).length && (Object.keys(probs).length !== ids.length ||
        Object.keys(probs).some(x => !ids.includes(x)) ||
        Math.abs(Object.values(probs).reduce((a,b)=>a+b,0)-1) > 1e-12)) throw Error('experiment_authority');
  }
  if (value.supersedes_event_id != null && value.supersedes_event_id === value.event_id) throw Error('event_correction');
  Object.entries(value).forEach(([key,item]) => {check(key);check(item);});
}
function codepointCompare(a,b) {
  const x=Array.from(a, c=>c.codePointAt(0)), y=Array.from(b, c=>c.codePointAt(0));
  for(let i=0;i<Math.min(x.length,y.length);i++) if(x[i]!==y[i]) return x[i]-y[i];
  return x.length-y.length;
}
function tag(value) {
  if(value===null) return ['null'];
  if(typeof value==='boolean') return ['boolean',value];
  if(typeof value==='number') {const b=Buffer.alloc(8);b.writeDoubleBE(value===0?0:value);return ['number',b.toString('hex')];}
  if(typeof value==='string') return ['string',value];
  if(Array.isArray(value)) return ['array',value.map(tag)];
  return ['object',Object.keys(value).sort(codepointCompare).map(k=>[k,tag(value[k])])];
}
const fixtureDir = path.resolve(process.argv[2] || path.join(root,'tests/contracts/fixtures'));
const fixtures = fs.readdirSync(fixtureDir).filter(name=>name.endsWith('.json')).sort()
  .flatMap(name=>JSON.parse(fs.readFileSync(path.join(fixtureDir,name))));
const results=fixtures.map(f=>{
  let accepted=false,digest=null;
  try {if(!validators.get(f.contract)?.(f.payload)) throw Error('schema');check(f.payload);accepted=true;
    digest=crypto.createHash('sha256').update(JSON.stringify(tag(f.payload))).digest('hex');
  } catch { /* Fail closed; payload content must not appear in diagnostics. */ }
  return {id:f.id,accepted,digest};
});
console.log(JSON.stringify(results));
if(results.some((r,i)=>r.accepted!==fixtures[i].accepted ||
   (r.accepted && fixtures[i].digest && r.digest!==fixtures[i].digest))) process.exitCode=1;
