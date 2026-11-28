import test from 'node:test';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {executionFlow} from '../web/execution_flow.mjs';

test('reply view distinguishes originals, local receipts and missing or unreadable artifacts',async()=>{
  const previousWindow=globalThis.window;
  globalThis.window={matchMedia:()=>({matches:false})};
  try {
    for(const mode of ['top_level_error','case_payload_error','top_level_no_response','case_payload_no_response',
      'ordinary_answer','read_error','missing_body','missing_artifact']) {
      const buttons=[],nodes=[];
      const node=(tag,text=null,className='')=>{
        const value={tag,textContent:text,className,children:[],dataset:{},attributes:{},
          append(...children){this.children.push(...children);},replaceChildren(...children){this.children=children;},
          setAttribute(key,item){this.attributes[key]=item;}};
        nodes.push(value);return value;
      };
      const run={id:randomUUID(),state:'failed'};
      const step={id:randomUUID(),run_id:run.id,kind:'model',stage_code:'I',state:'failed',seq:1};
      const artifact={id:randomUUID(),run_id:run.id,step_id:step.id,kind:'model_response',content_url:'/local-envelope-test'};
      step.output_artifact_id=artifact.id;
      if(mode==='missing_artifact')delete step.output_artifact_id;
      const local=mode.endsWith('no_response')?{raw:null,validation_error:'call_timeout'}:
        {raw:null,validation_error:'model_response_envelope_invalid',transport_error:{response_received:true}};
      const saved=mode.startsWith('case_payload')?{payload:local}:mode==='ordinary_answer'?
        {raw:{choices:[{finish_reason:'stop',message:{content:'{}'}}]}}:mode==='missing_body'?{}:local;
      executionFlow({run,steps:[step],artifacts:mode==='missing_artifact'?[]:[artifact],result:null,current:()=>true,onInspect:()=>{},
        readBody:async()=>{
          if(mode==='read_error')throw new Error('test-only-read-failure');
          return {data:{artifact,availability:'available',content_json:saved}};
        },ui:{node,button:(text,click)=>{const value=node('button',text);value.click=click;buttons.push(value);return value;},
          facts:()=>node('dl'),notice:text=>node('p',text),rawDetails:()=>node('details'),
          resultCard:()=>node('div'),contentCard:()=>node('div')}});
      await buttons.find(button=>button.dataset.stepId===step.id).click();
      await buttons.find(button=>button.textContent==='模型原答').click();
      const texts=nodes.map(value=>value.textContent).filter(value=>typeof value==='string');
      if(mode==='ordinary_answer') {
        assert.ok(texts.some(text=>text.includes('以下为实际收到的模型原答')));
        assert.ok(texts.includes('{}'));
      } else if(mode==='read_error') {
        assert.ok(texts.includes('原答读取失败，尚不能判定未收到正文。'));
        assert.ok(!texts.some(text=>text.startsWith('已收到 HTTP 响应')));
      } else if(mode.endsWith('no_response')) {
        assert.ok(texts.includes('本次调用未收到模型正文（no_response）；没有用解析输出替代原答。'));
        assert.ok(!texts.some(text=>text.startsWith('原件中未找到')));
        assert.ok(!texts.some(text=>text.startsWith('已收到 HTTP 响应')));
      } else if(mode.startsWith('missing_')) {
        assert.ok(texts.includes('原件中未找到该次模型的原始正文。'));
        assert.ok(!texts.some(text=>text.startsWith('本次调用未收到模型正文')));
      } else {
        assert.ok(texts.includes('已收到 HTTP 响应，但 JSON 信封无效；没有可用模型正文。'));
        assert.ok(!texts.some(text=>text.startsWith('本次调用未收到模型正文')));
        assert.ok(!texts.some(text=>text.startsWith('原件中未找到')));
      }
    }
  } finally {
    if(previousWindow===undefined)delete globalThis.window;
    else globalThis.window=previousWindow;
  }
});
