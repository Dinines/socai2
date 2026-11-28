import test from 'node:test';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {executionFlow} from '../web/execution_flow.mjs';
import {DELIVERY_SCHEMA} from '../web/delivery_view.mjs';

test('the existing delivery panel renders persisted true, false and unknown dispatch facts',async()=>{
  const previousWindow=globalThis.window;
  globalThis.window={matchMedia:()=>({matches:false})};
  try {
    for(const [sent,label] of [[false,'未发送'],[true,'已发送'],[null,'未确认'],[undefined,'未确认']]) {
      const buttons=[],rendered=[];
      const node=(tag,text=null,className='')=>({tag,text,className,children:[],dataset:{},attributes:{},
        append(...children){this.children.push(...children);},
        replaceChildren(...children){this.children=children;},
        setAttribute(key,value){this.attributes[key]=value;}});
      const run={id:randomUUID(),state:'failed'};
      const step={id:randomUUID(),run_id:run.id,kind:'stage',stage_code:'I',state:'failed',seq:1};
      const artifact={id:randomUUID(),run_id:run.id,step_id:step.id,kind:'source_snapshot',
        schema_version:DELIVERY_SCHEMA,content_url:'/local-test-receipt'};
      const receipt={schema_version:DELIVERY_SCHEMA,type:'stage_delivery',run_id:run.id,step_id:step.id,
        execution:{call_state:'failed',local_state:'ended',request_dispatched:sent},
        parse:{state:'no_response'},delivery:{state:'none'},quality:{state:'not_checked'},
        retained_units:[],missing_units:[],invalid_units:[],use:{adoption_eligible:false,comparison_eligible:false}};
      executionFlow({run,steps:[step],artifacts:[artifact],result:null,current:()=>true,onInspect:()=>{},
        readBody:async()=>({data:{artifact,availability:'available',content_json:receipt}}),
        ui:{node,button:(text,click)=>{const value=node('button',text);value.click=click;buttons.push(value);return value;},
          facts:rows=>{rendered.push(...rows);return node('dl');},notice:text=>node('p',text),
          rawDetails:()=>node('details'),resultCard:()=>node('div'),contentCard:()=>node('div')}});
      const selected=buttons.find(button=>button.dataset.stepId===step.id);
      assert.ok(selected,'the actual stage button exists');
      await selected.click();
      assert.ok(rendered.some(([key,value])=>key==='请求发送' && value===label));
      assert.ok(rendered.some(([key,value])=>key==='本地执行' && value==='已结束'));
    }
  } finally {
    if(previousWindow===undefined)delete globalThis.window;
    else globalThis.window=previousWindow;
  }
});
