import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
const worktree=resolve(process.argv[2]);
const {NotteClient}=await import(pathToFileURL(resolve(worktree,'node_modules/notte-sdk/dist/index.mjs')));
const original=NotteClient.prototype.Session;
const sessions=[];let breakConnection=false;
NotteClient.prototype.Session=function(...args){
 const s=original.apply(this,args);sessions.push(s);
 if(breakConnection)s.cdpUrl=async()=> 'ws://127.0.0.1:9';
 return s;
};
const evidence={};
try{
 await import(pathToFileURL(resolve(worktree,'acceptance.mjs')));
 evidence.originalAcceptancePassed=true;
 const {run}=await import(pathToFileURL(resolve(worktree,'app.mjs')));
 breakConnection=true;
 let rejected=false;try{await run();}catch{rejected=true;}
 assert.ok(rejected,'connection failure must reject');evidence.connectionFailureRejected=true;
 evidence.createdSessionCount=sessions.length;
 assert.equal(sessions.length,process.argv[3]==='stagehand'?2:3,'each acceptance run and the connection-failure probe must create a Notte session');
 evidence.closedStatuses=[];
 for(const s of sessions){const status=(await s.status()).status;evidence.closedStatuses.push(status);assert.equal(status,'closed');}
 evidence.success=true;
}catch(e){evidence.success=false;evidence.failure={name:e.name,assertion:e.code==='ERR_ASSERTION'};process.exitCode=1;}
finally {NotteClient.prototype.Session=original;for(const s of sessions){try{await s.stop();}catch{}}}
console.log(JSON.stringify(evidence));
