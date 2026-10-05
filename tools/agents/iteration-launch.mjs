// Persistent Node supervisor: detach Node from the agent, not PowerShell.
// PowerShell exited before executing with DETACHED_PROCESS on this host.
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';

const configPath=path.resolve(process.argv[2]);
const cfg=JSON.parse((await fs.readFile(configPath,'utf8')).replace(/^\uFEFF/,''));
const powershell=path.join(process.env.SystemRoot??'C:/Windows','System32/WindowsPowerShell/v1.0/powershell.exe');
const child=spawn(powershell,['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
 path.join(cfg.coordinator,'tools/agents/iteration-live.ps1'),'-Config',configPath],
 {windowsHide:true,stdio:['ignore','inherit','inherit']});
const code=await new Promise(resolve=>{
 child.once('error',()=>resolve(-1));
 child.once('exit',resolve);
});
const statePath=path.join(cfg.job,'live.json');
let state;try{state=JSON.parse((await fs.readFile(statePath,'utf8')).replace(/^\uFEFF/,''));}catch{}
if(state?.stage==='launching'){
 await fs.writeFile(statePath,JSON.stringify({...state,status:'failed',stage:'finished',launcher_exit:code,
  error:'PowerShell exited before startup acknowledgement; inspect live-launcher.log. No automatic retry.'}));
}
process.exitCode=code===0?0:1;
