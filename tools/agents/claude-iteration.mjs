import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const role=process.argv[2];
if(!['opus','sonnet'].includes(role))throw Error('Use opus|sonnet');
const configPath=path.join(root,`artifacts/iterations/2026-10-01/${role}/config.json`);
const cfg=JSON.parse((await fs.readFile(configPath,'utf8')).replace(/^\uFEFF/,''));
const statusPath=path.join(cfg.job,'usage.json');
try{await fs.access(statusPath);throw Error('Attempt already exists');}catch(e){if(e.code!=='ENOENT')throw e;}
const mcpFile=path.join(cfg.job,'mcp.json');
await fs.writeFile(mcpFile,JSON.stringify({mcpServers:{igvc_iteration:{command:process.execPath,args:[path.join(root,'tools/agents/iteration-mcp.mjs'),configPath]}}},null,2));
const assignment=role==='sonnet'?`Implement observed-surface projection correction in surface_projection.py and its two assigned test files. The coordinator reproduced a synthetic flat-ground query at6m, camera height1.4m/pitch20deg/f471, support offset7.9px: old projection error.38657m XY and+.09020m Z. These are test inputs, not physical calibration. Use only observed eligible local surface geometry, no fixed global ground plane or WORLD. Preserve exact-depth behavior where justified, foreground occlusion, nonfinite/range guards, real slope/ramp markings. Add meaningful grazing-ground, ramp, crease and occlusion regressions. Avoid fitting across discontinuities; unsupported geometry should reject conservatively without blocking all paint. Do not change point_memory or runtime lane configuration this round. Existing approximation-specific tests may need a justified behavioral expectation change; explain it. Run the perception suite; commit the correction; run your one live trial; report measured result.`:
`Implement a differential-drive-feasible path-entry contract in tools/path_entry.py and tests/test_path_entry.py. Current admission accepts pose(2.8,3.08,0) onto straight y3 path with a sideways -90deg positional connector at fixed zero yaw. Eliminate sideways/backward joins without shrinking footprint or bypassing observed sweeps. Prefer forward segment projection or a checked kinematic connector if feasible; blindly rejecting every small lateral tracking error may prevent useful runtime progress, so choose and test a workable forward-only method. Preserve rejection of stale large lateral/yaw error, unknown/blocked grid and consumed-path handling. Preserve path/yaw geometry in admitted output. Do not redesign recovery or change controller/profile this round. Run focused navigation tests; commit; run your one live trial and report observed effects. Do not use the prior review's chord-sagitta estimate as a pursuit-error bound; the integrator disproved that numerical argument.`;
const prompt=`You are the user-authorized implementation worker ${cfg.model} via Claude CLI, high effort, no fallback. You may edit/commit ONLY assigned files via igvc_iteration tools and initiate a real bounded Unity/ROS simulation via run_simulation. No recursive agents, arbitrary commands, networking, credential access, model switching, Git push/reset or unrelated edits. Workspace ${cfg.workspace}, branch ${cfg.branch}, baseline ${cfg.baseline}. Read README.md, AGENTS.md, docs/AGENT_ITERATION.md and relevant integrated findings first. These runtime instructions supersede older read-only review packets. The current Unity Editor is used by another project: never open, close or build any Unity Editor. Live tool uses the existing hidden player with rendering enabled and takes exclusive shared-simulator lease. Keep full footprint, .30m inflation, six sparse GPS destinations, sensor-only runtime, existing guards and speed ceiling. No source-map knowledge. At most3 test calls and1 live trial. Commit after tests pass, then run_simulation, then simulation_status until finished. While queued/running do not modify source. A partial/failed lap is not success. Do not stop at a plan: implement the bounded assignment. If live infrastructure fails, report exact failure without changing infrastructure. Return <=700words with commit, changed files, tests, live outcome, risks and next step.\n\nASSIGNMENT\n${assignment}`;
const args=['-p','--model',cfg.model,'--effort','high','--output-format','stream-json','--verbose',
 '--restricted','--tools','','--allowedTools','mcp__igvc_iteration','--permission-mode','dontAsk',
 '--permission-prompts','none','--strict-mcp-config','--mcp-config',mcpFile,
 '--disable-slash-commands','--setting-sources','','--settings','{"disableAllHooks":true,"autoMemoryEnabled":false}',
 '--no-chrome','--no-session-persistence','--max-budget-usd','10'];
const run=spawn(path.join(process.env.USERPROFILE,'.local/bin/claude.exe'),args,{cwd:cfg.workspace,windowsHide:true,stdio:['pipe','pipe','pipe']});
const status={role,provider:'Claude CLI',requested_model:cfg.model,effort:'high',branch:cfg.branch,
 baseline:cfg.baseline,started_utc:new Date().toISOString(),status:'running',requested_budget_usd:10,wall_limit_s:2100};
await fs.writeFile(statusPath,JSON.stringify(status,null,2));
let buffer='',stderr='',lastText='',result,chain=Promise.resolve();
const timer=setTimeout(()=>{status.status='time_limit';run.kill();},2100000);
run.stderr.on('data',b=>{stderr=(stderr+b.toString()).slice(-2000);});
run.stdout.on('data',b=>{
 buffer+=b.toString();let end;
 while((end=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,end);buffer=buffer.slice(end+1);let e;try{e=JSON.parse(line);}catch{continue;}
  if(e.type==='system'&&e.subtype==='init'){status.actual_model=e.model;status.tools=e.tools;if(e.model!==cfg.model){status.status='model_mismatch';run.kill();}}
  if(e.type==='assistant'){const text=(e.message?.content??[]).filter(c=>c.type==='text').map(c=>c.text).join('\n');if(text)lastText=text;}
  if(e.type==='result')result=e;
  if(e.type==='result'||(e.type==='system'&&e.subtype==='init'))chain=chain.then(()=>fs.appendFile(path.join(cfg.job,'events.jsonl'),JSON.stringify(e)+'\n'));
 }
});
run.stdin.end(prompt);
const code=await new Promise(resolve=>{run.on('error',()=>resolve(-1));run.on('close',resolve);});
clearTimeout(timer);await chain;
if(status.status==='running')status.status=result?.is_error?'error':code===0&&result?.subtype==='success'?'completed':'failed';
Object.assign(status,{exit_code:code,completed_utc:new Date().toISOString(),total_cost_usd:result?.total_cost_usd,usage:result?.usage,modelUsage:result?.modelUsage});
await fs.writeFile(statusPath,JSON.stringify(status,null,2));
await fs.writeFile(path.join(cfg.job,'report.md'),result?.result??lastText??'No final report returned');
if(!result&&stderr)await fs.writeFile(path.join(cfg.job,'launcher-error.txt'),stderr.replace(/(?:sk-ant-|crsr_)[A-Za-z0-9_-]+/g,'[REDACTED]'));
console.log(JSON.stringify({role,status:status.status,model:status.actual_model,cost_usd:status.total_cost_usd,job:cfg.job}));
if(status.status!=='completed')process.exitCode=1;
