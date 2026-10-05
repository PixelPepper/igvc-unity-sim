// Private stdio MCP: frozen text reads and named offline checks, no generic shell.
import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
import {roles} from './review-handoff.mjs';
const execute=promisify(execFile);
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const area=path.join(root,'artifacts/reviews/2026-09-30');
const baseline=path.join(area,'baseline');
const role=process.argv[2],cfg=roles[role];
if(!cfg)throw Error('Unknown review role');
const job=path.join(area,`claude-${role}`);
const manifest=JSON.parse(await fs.readFile(path.join(baseline,'manifest.json'),'utf8'));
const allowed=['README.md','AGENTS.md','trial-summary.json','docs/NAVIGATION_INVESTIGATION.md',...cfg.files]
 .filter(p=>Object.hasOwn(manifest.files,p));
let reads=0,characters=0,requested=false;
const checks=new Set();
let queue=Promise.resolve();
const schemas=[
 {name:'read_file',description:'Read frozen allowlisted source, numbered lines. Up to 160 lines per call, 24 reads total.',inputSchema:{type:'object',properties:{path:{type:'string',enum:allowed},start:{type:'integer',minimum:1},lines:{type:'integer',minimum:1,maximum:160}},required:['path'],additionalProperties:false}},
 {name:'run_check',description:'Run one fixed offline unit-test group or recorded replay. Each check once, max3. No live ROS/Unity or source edits.',inputSchema:{type:'object',properties:{name:{type:'string',enum:cfg.checks}},required:['name'],additionalProperties:false}},
 {name:'request_experiment',description:'Queue one bounded experiment for coordinator; does not execute it.',inputSchema:{type:'object',properties:{hypothesis:{type:'string'},procedure:{type:'string'},expected_discrimination:{type:'string'}},required:['hypothesis','procedure','expected_discrimination'],additionalProperties:false}}
];
async function log(data){await fs.appendFile(path.join(job,'tools.jsonl'),JSON.stringify(data)+'\n');}
async function call(name,a){
 if(name==='read_file'){
  if(!allowed.includes(a.path))throw Error('Path not allowed');
  const start=a.start??1,count=a.lines??120;
  if(!Number.isInteger(start)||start<1||!Number.isInteger(count)||count<1||count>160||reads>=24)throw Error('Read bounds exceeded');
  const bytes=await fs.readFile(path.join(baseline,a.path));
  if(createHash('sha256').update(bytes).digest('hex')!==manifest.files[a.path])throw Error('Baseline drift');
  const lines=bytes.toString('utf8').split('\n');
  const text=lines.slice(start-1,start-1+count).map((s,i)=>`${start+i}: ${s}`).join('\n').slice(0,14000);
  if(characters+text.length>100000)throw Error('Text budget exhausted');
  reads++;characters+=text.length;await log({tool:name,path:a.path,start,count,characters:text.length});
  return {path:a.path,total_lines:lines.length,text};
 }
 if(name==='run_check'){
  if(!cfg.checks.includes(a.name)||checks.has(a.name)||checks.size>=3)throw Error('Check unavailable or already used');
  checks.add(a.name);
  const script=path.join(baseline,'tools/agents/review-check.sh');
  const linux='/mnt/'+script[0].toLowerCase()+script.slice(2).replaceAll('\\','/');
  const env={};for(const k of ['SystemRoot','WINDIR','PATH','TEMP','TMP','COMSPEC','USERPROFILE','LOCALAPPDATA'])if(process.env[k])env[k]=process.env[k];
  let stdout='',stderr='',code=0;
  try{({stdout,stderr}=await execute('wsl.exe',['-d','Ubuntu-24.04','--','bash',linux,a.name],{cwd:baseline,env,timeout:150000,maxBuffer:256000,windowsHide:true}));}
  catch(e){stdout=e.stdout??'';stderr=e.stderr??'';code=Number.isInteger(e.code)?e.code:1;}
  const result={check:a.name,exit_code:code,stdout:stdout.slice(-16000),stderr:stderr.slice(-2000)};
  await fs.writeFile(path.join(job,`${a.name}.json`),JSON.stringify(result,null,2));
  await log({tool:name,check:a.name,exit_code:code});return result;
 }
 if(name==='request_experiment'){
  if(requested||JSON.stringify(a).length>8000||!['hypothesis','procedure','expected_discrimination'].every(k=>typeof a[k]==='string'))throw Error('Invalid or repeated experiment request');
  requested=true;await fs.writeFile(path.join(job,'requested-experiment.json'),JSON.stringify(a,null,2));
  await log({tool:name});return 'Queued for coordinator; not executed.';
 }
 throw Error('Unknown tool');
}
async function handle(m){
 if(m.id===undefined)return;
 let result;
 if(m.method==='initialize')result={protocolVersion:m.params.protocolVersion,capabilities:{tools:{}},serverInfo:{name:'igvc-frozen-review',version:'1.0.0'}};
 else if(m.method==='ping')result={};
 else if(m.method==='tools/list')result={tools:schemas};
 else if(m.method==='tools/call'){
  try{result={content:[{type:'text',text:JSON.stringify(await call(m.params.name,m.params.arguments??{}))}]};}
  catch(e){result={isError:true,content:[{type:'text',text:String(e.message).slice(0,250)}]};}
 }else{process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:m.id,error:{code:-32601,message:'Method unavailable'}})+'\n');return;}
 process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:m.id,result})+'\n');
}
const rl=readline.createInterface({input:process.stdin});
rl.on('line',line=>{queue=queue.then(async()=>{try{await handle(JSON.parse(line));}catch{process.stderr.write('Invalid review RPC\n');}});});
