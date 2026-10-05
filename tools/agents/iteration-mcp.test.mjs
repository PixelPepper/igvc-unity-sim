import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline';
import {spawn,execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
test('implementation MCP rejects out-of-scope writes, untested commits and untested simulation',async()=>{
 const cfg=JSON.parse((await fs.readFile(path.join(root,'artifacts/iterations/2026-10-01/opus/config.json'),'utf8')).replace(/^\uFEFF/,''));
 cfg.branch=execFileSync('git',['-C',cfg.workspace,'branch','--show-current'],{encoding:'utf8',windowsHide:true}).trim();
 cfg.job=await fs.mkdtemp(path.join(root,'artifacts/iterations/2026-10-01/tool-test-'));
 const cfgFile=path.join(cfg.job,'config.json');await fs.writeFile(cfgFile,JSON.stringify(cfg));
 const child=spawn(process.execPath,[path.join(root,'tools/agents/iteration-mcp.mjs'),cfgFile],{stdio:['pipe','pipe','pipe']});
 const pending=new Map();let next=0;
 const lines=readline.createInterface({input:child.stdout});
 lines.on('line',line=>{const response=JSON.parse(line);pending.get(response.id)?.(response);});
 async function rpc(method,params){
  const id=++next;let timeout;
  const answer=new Promise((resolve,reject)=>{pending.set(id,resolve);timeout=setTimeout(()=>reject(Error('MCP timeout')),5000);});
  child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');
  try{return await answer;}finally{clearTimeout(timeout);}
 }
 try{
  const init=await rpc('initialize',{protocolVersion:'2024-11-05'});assert.ok(init.result);
  const listed=await rpc('tools/list',{});
  assert.equal(listed.result.tools.some(t=>['shell','exec','push','reset'].includes(t.name)),false);
  for(const [name,args] of [
   ['write_file',{path:'../../outside.txt',content:'denied'}],
   ['write_file',{path:'tools/sensor_course.py',content:'denied'}],
   ['read_file',{path:'.env'}],
   ['git_commit',{message:'must not commit without tests'}],
   ['run_simulation',{}]]){
   const response=await rpc('tools/call',{name,arguments:args});assert.equal(response.result.isError,true,name);
  }
  const stalled={status:'running',stage:'launching',launch_requested_utc:new Date(Date.now()-120000).toISOString()};
  await fs.writeFile(path.join(cfg.job,'live.json'),JSON.stringify(stalled));
  const response=await rpc('tools/call',{name:'simulation_status',arguments:{}});
  assert.equal(response.result.isError,true);
  assert.match(response.result.content[0].text,/Stop polling/);
  assert.deepEqual(JSON.parse(await fs.readFile(path.join(cfg.job,'live.json'),'utf8')),stalled);
 }finally{child.kill();lines.close();}
});

test('hidden PowerShell acknowledges startup and survives MCP exit without ROS or Unity',async()=>{
 const cfg=JSON.parse((await fs.readFile(path.join(root,'artifacts/iterations/2026-10-01/opus/config.json'),'utf8')).replace(/^\uFEFF/,''));
 cfg.branch=execFileSync('git',['-C',cfg.workspace,'branch','--show-current'],{encoding:'utf8',windowsHide:true}).trim();
 cfg.job=await fs.mkdtemp(path.join(root,'artifacts/iterations/2026-10-01/launch-test-'));
 cfg.coordinator=path.join(cfg.job,'fixture coordinator');
 const fixture=path.join(cfg.coordinator,'tools/agents');await fs.mkdir(fixture,{recursive:true});
 // Fake only the test/build workload. Exercise the real MCP spawning code and
 // actual Windows PowerShell process/argument handling, including spaced paths.
 await fs.writeFile(path.join(fixture,'iteration-check.sh'),'#!/bin/bash\nexit 0\n');
 await fs.writeFile(path.join(fixture,'iteration-live.ps1'),
  "param([string]$Config)\n$cfg=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json\n@{status='running';stage='fixture_started';fixture_only=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $cfg.job 'live.json')\nStart-Sleep -Seconds 2\n@{status='completed';stage='finished';fixture_only=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $cfg.job 'live.json')\n");
 const cfgFile=path.join(cfg.job,'config.json');await fs.writeFile(cfgFile,JSON.stringify(cfg));
 const child=spawn(process.execPath,[path.join(root,'tools/agents/iteration-mcp.mjs'),cfgFile],{stdio:['pipe','pipe','pipe']});
 const pending=new Map();let next=0;
 const lines=readline.createInterface({input:child.stdout});
 lines.on('line',line=>{const response=JSON.parse(line);pending.get(response.id)?.(response);});
 async function call(name){
  const id=++next;let timeout;
  const answer=new Promise((resolve,reject)=>{pending.set(id,resolve);timeout=setTimeout(()=>reject(Error('Fixture RPC timeout')),30000);});
  child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method:'tools/call',params:{name,arguments:{}}})+'\n');
  try{return await answer;}finally{clearTimeout(timeout);}
 }
 try{
  const tests=await call('run_tests');assert.notEqual(tests.result.isError,true);
  assert.equal(JSON.parse(tests.result.content[0].text).exit_code,0);
  const launch=await call('run_simulation');assert.notEqual(launch.result.isError,true);
  const deadline=Date.now()+15000;let state;
  do{
   state=JSON.parse((await fs.readFile(path.join(cfg.job,'live.json'),'utf8')).replace(/^\uFEFF/,''));
   if(state.stage==='fixture_started'){child.kill();}
   if(state.stage==='finished')break;
   await new Promise(resolve=>setTimeout(resolve,100));
  }while(Date.now()<deadline);
  assert.equal(state.fixture_only,true,JSON.stringify(state));
  assert.equal(state.stage,'finished');
 }finally{child.kill();lines.close();}
});
