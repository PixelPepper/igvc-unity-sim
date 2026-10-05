import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import readline from 'node:readline';
import {fileURLToPath} from 'node:url';

test('review MCP exposes only bounded tools and rejects traversal/arbitrary checks', async()=>{
 const child=spawn(process.execPath,[fileURLToPath(new URL('./claude-review-mcp.mjs',import.meta.url)),'opus'],{stdio:['pipe','pipe','pipe']});
 const answers=new Map(),pending=new Map();let id=0;
 const lines=readline.createInterface({input:child.stdout});
 lines.on('line',line=>{const m=JSON.parse(line);answers.set(m.id,m);pending.get(m.id)?.(m);});
 const rpc=async(method,params)=>{
  const requestId=++id;
  const promise=new Promise(resolve=>pending.set(requestId,resolve));
  child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:requestId,method,params})+'\n');
  const timeout=AbortSignal.timeout(5000);
  return await Promise.race([promise,new Promise((_,reject)=>timeout.addEventListener('abort',()=>reject(Error('MCP timeout'))))]);
 };
 try{
  const init=await rpc('initialize',{protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'offline-test',version:'1'}});
  assert.equal(init.result.protocolVersion,'2024-11-05');
  const list=await rpc('tools/list',{});
  assert.deepEqual(list.result.tools.map(t=>t.name).sort(),['read_file','request_experiment','run_check']);
  for(const [name,args] of [['read_file',{path:'../../credentials'}],['run_check',{name:'shell'}],['shell',{command:'whoami'}]]){
   const response=await rpc('tools/call',{name,arguments:args});
   assert.equal(response.result.isError,true);
  }
 }finally{child.kill();lines.close();}
});
