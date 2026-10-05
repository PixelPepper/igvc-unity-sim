import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline';
import {execFile,spawn} from 'node:child_process';
import {promisify} from 'node:util';
import {fileURLToPath} from 'node:url';
const execute=promisify(execFile);
const configPath=path.resolve(process.argv[2]);
const cfg=JSON.parse((await fs.readFile(configPath,'utf8')).replace(/^\uFEFF/,''));
const owned=cfg.role==='sonnet'?[
 'ros2/src/igvc_perception/igvc_perception/surface_projection.py',
 'ros2/src/igvc_perception/test/test_surface_projection.py',
 'ros2/src/igvc_perception/test/test_recorded_lane_projection.py']:[
 'tools/path_entry.py','tools/tests/test_path_entry.py'];
const reads=[...owned,'README.md','AGENTS.md','docs/AGENT_ITERATION.md',
 'docs/reviews/2026-09-30/REVIEW_SUMMARY.md',
 `docs/reviews/2026-09-30/${cfg.role.toUpperCase()}_FINDINGS.md`,
 'tools/swept_footprint.py','tools/execution_path.py','tools/sensor_route_policy.py',
 'tools/observed_navigation.py','tools/sensor_course.py',
 'ros2/src/igvc_perception/igvc_perception/lane_node.py',
 'ros2/src/igvc_perception/igvc_perception/surfaces.py',
 'ros2/src/igvc_perception/test/test_point_evidence.py',
 'fixtures/white_barrel_cap/metadata.json'];
const git=args=>execute('git',['-C',cfg.workspace,...args],{windowsHide:true,maxBuffer:400000});
const linux=p=>'/mnt/'+p[0].toLowerCase()+p.slice(2).replaceAll('\\','/');
let tests=0,liveRequested=false,readChars=0;
async function live(){try{return JSON.parse((await fs.readFile(path.join(cfg.job,'live.json'),'utf8')).replace(/^\uFEFF/,''));}catch{return null;}}
function checkLaunch(state){
 if(state?.stage==='launching'&&(!state.launch_requested_utc||!Number.isFinite(Date.parse(state.launch_requested_utc))||Date.now()-Date.parse(state.launch_requested_utc)>60000)){
  // A delayed process could still start; retain ownership and prohibit automatic retry.
  throw Error('No launcher startup acknowledgement within 60s. Stop polling and report to coordinator; inspect live-launcher.log/process ownership before any retry.');
 }
}
async function requireEditable(){
 if((await git(['branch','--show-current'])).stdout.trim()!==cfg.branch)throw Error('Unexpected branch');
 const s=await live();if(s&&s.stage!=='finished')throw Error('Do not edit or commit while simulation is queued/running');
}
const tools=[
 {name:'read_file',description:'Read assigned source/context, numbered lines; max200 lines/call and 160k characters total.',inputSchema:{type:'object',properties:{path:{type:'string',enum:reads},start:{type:'integer'},lines:{type:'integer'}},required:['path'],additionalProperties:false}},
 {name:'write_file',description:'Replace one owned source/test file. Only assigned files; no writes during live trial. Read first and preserve unrelated behavior.',inputSchema:{type:'object',properties:{path:{type:'string',enum:owned},content:{type:'string'}},required:['path','content'],additionalProperties:false}},
 {name:'run_tests',description:'Execute the relevant offline behavioral suite on your working tree. At most3 calls; fix demonstrated failures before another call.',inputSchema:{type:'object',properties:{},additionalProperties:false}},
 {name:'git_diff',description:'Review current scoped diff and status before committing.',inputSchema:{type:'object',properties:{},additionalProperties:false}},
 {name:'git_commit',description:'Commit only your assigned files on your assigned local branch. No push/reset/force operations.',inputSchema:{type:'object',properties:{message:{type:'string'}},required:['message'],additionalProperties:false}},
 {name:'run_simulation',description:'Start your one bounded live Unity/ROS trial with isolated build overlay and exclusive simulator lease. Commit and pass tests first. Returns immediately; poll simulation_status. Fixed seed2027, .6m/s, RPP, checked-path,600s. No oracle/guard changes.',inputSchema:{type:'object',properties:{},additionalProperties:false}},
 {name:'simulation_status',description:'Wait up to20s then return trial stage, measured progress and relevant log tail. A completed trial can still be a failed/partial lap.',inputSchema:{type:'object',properties:{},additionalProperties:false}}
];
let lastTestsPassed=false;
async function call(name,a){
 if(name==='read_file'){
  if(!reads.includes(a.path))throw Error('Path not allowed');
  const start=a.start??1,n=a.lines??140;
  if(!Number.isInteger(start)||start<1||!Number.isInteger(n)||n<1||n>200)throw Error('Invalid slice');
  const lines=(await fs.readFile(path.join(cfg.workspace,a.path),'utf8')).split('\n');
  const text=lines.slice(start-1,start-1+n).map((s,i)=>`${start+i}: ${s}`).join('\n');
  if(readChars+text.length>160000)throw Error('Read budget exhausted');readChars+=text.length;
  return {path:a.path,total_lines:lines.length,text};
 }
 if(name==='write_file'){
  await requireEditable();if(!owned.includes(a.path)||typeof a.content!=='string'||a.content.length>150000)throw Error('Invalid owned write');
  await fs.writeFile(path.join(cfg.workspace,a.path),a.content);lastTestsPassed=false;return 'Saved owned file; run behavioral tests before committing.';
 }
 if(name==='run_tests'){
  if(++tests>3)throw Error('Test-call budget exhausted');
  let result;try{result=await execute('wsl.exe',['-d','Ubuntu-24.04','--','bash',linux(path.join(cfg.coordinator,'tools/agents/iteration-check.sh')),linux(cfg.workspace),cfg.role],{windowsHide:true,timeout:180000,maxBuffer:400000});result.exit_code=0;}
  catch(e){result={exit_code:Number.isInteger(e.code)?e.code:1,stdout:e.stdout??'',stderr:e.stderr??''};}
  lastTestsPassed=result.exit_code===0;await fs.writeFile(path.join(cfg.job,`tests-${tests}.json`),JSON.stringify(result,null,2));
  return {exit_code:result.exit_code,output:(result.stdout+result.stderr).slice(-12000)};
 }
 if(name==='git_diff')return {status:(await git(['status','--short'])).stdout,diff:(await git(['diff','--',...owned])).stdout.slice(-30000)};
 if(name==='git_commit'){
  await requireEditable();if(!lastTestsPassed)throw Error('Focused tests must pass after latest write');
  if(typeof a.message!=='string'||a.message.length>300)throw Error('Invalid commit message');
  await git(['add','--',...owned]);
  const staged=(await git(['diff','--cached','--name-only'])).stdout.trim().split('\n').filter(Boolean);
  if(!staged.length||staged.some(p=>!owned.includes(p)))throw Error('No owned changes or unexpected staged paths');
  await git(['commit','-m',a.message]);return {commit:(await git(['rev-parse','HEAD'])).stdout.trim()};
 }
 if(name==='run_simulation'){
  await requireEditable();if(liveRequested||!lastTestsPassed)throw Error('One live trial only; tests must pass first');
  if((await git(['status','--porcelain'])).stdout.trim())throw Error('Commit all assigned edits first');
  if((await git(['rev-parse','HEAD'])).stdout.trim()===cfg.baseline)throw Error('Implement and commit candidate before trial');
  liveRequested=true;
  await fs.writeFile(path.join(cfg.job,'live.json'),JSON.stringify({status:'running',stage:'launching',launch_requested_utc:new Date().toISOString()}));
  const launchLog=await fs.open(path.join(cfg.job,'live-launcher.log'),'a');
  const child=spawn(process.execPath,[fileURLToPath(new URL('./iteration-launch.mjs',import.meta.url)),configPath],{windowsHide:true,detached:true,stdio:['ignore',launchLog.fd,launchLog.fd]});
  child.on('error',async()=>{await fs.writeFile(path.join(cfg.job,'live.json'),JSON.stringify({status:'failed',stage:'finished',error:'Background launcher could not start; inspect live-launcher.log'}));});
  child.on('exit',async(code)=>{
   const state=await live();
   if(state?.stage==='launching')await fs.writeFile(path.join(cfg.job,'live.json'),JSON.stringify({...state,status:'failed',stage:'finished',launcher_exit:code,error:'Background launcher exited before startup; inspect live-launcher.log. No automatic retry.'}));
  });
  child.unref();await launchLog.close();
  return {launched:true,pid:child.pid,note:'Poll simulation_status; do not edit during the trial. Lease serializes real Unity/ROS motion.'};
 }
 if(name==='simulation_status'){
  let s=await live();checkLaunch(s);if(s?.stage!=='finished')await new Promise(resolve=>setTimeout(resolve,20000));s=await live();checkLaunch(s);
  let progress=null;try{const p=JSON.parse((await fs.readFile(path.join(cfg.job,'run.progress.json'),'utf8')).replace(/^\uFEFF/,''));progress={status:p.status,completed_destinations:p.completed_destinations,pose:p.pose};}catch{}
  let tail='';const log=s?.stage==='building_ros'?'build.log':s?.stage==='mission'?'mission.log':s?.stage==='finished'?'mission.log':'start.log';
  try{tail=(await fs.readFile(path.join(cfg.job,log),'utf8')).slice(-3500);}catch{}
  let audit=null;try{const a=JSON.parse((await fs.readFile(path.join(cfg.job,'audit.json'),'utf8')).replace(/^\uFEFF/,''));audit={passed:a.passed,checks:a.checks};}catch{}
  return {state:s,progress,audit,log_tail:tail};
 }
 throw Error('Unknown tool');
}
let sequence=Promise.resolve();
async function handle(m){
 if(m.id===undefined)return;let result;
 if(m.method==='initialize')result={protocolVersion:m.params.protocolVersion,capabilities:{tools:{}},serverInfo:{name:'igvc-iteration',version:'1'}};
 else if(m.method==='ping')result={};
 else if(m.method==='tools/list')result={tools};
 else if(m.method==='tools/call'){
  try{const value=await call(m.params.name,m.params.arguments??{});result={content:[{type:'text',text:JSON.stringify(value)}]};}
  catch(e){result={isError:true,content:[{type:'text',text:String(e.message).slice(0,700)}]};}
  await fs.appendFile(path.join(cfg.job,'tools.jsonl'),JSON.stringify({time:new Date().toISOString(),tool:m.params.name,path:m.params.arguments?.path,error:!!result.isError})+'\n');
 }else{process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:m.id,error:{code:-32601,message:'Unavailable'}})+'\n');return;}
 process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:m.id,result})+'\n');
}
readline.createInterface({input:process.stdin}).on('line',line=>{sequence=sequence.then(async()=>{try{await handle(JSON.parse(line));}catch{process.stderr.write('Invalid iteration RPC\n');}});});
