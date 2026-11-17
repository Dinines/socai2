"""Check the configured input guard locally or in the image, without I/O."""
import json
import os

from app.services.llm_safety import LLMInputContract, classify_message
from app.socai2.baseline_model_view import blocked, blocked_message
from app.socai2.runtime_policy import active_policy

policy = active_policy()
cap = int(os.environ['AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS'])
assert cap == policy.model.max_prepared_bytes
unit = 'A retained business statement with its original wording. '
large = unit * (cap // 8 // len(unit))
messages = [{'role': 'user', 'content': json.dumps({'statement': large})}]
assert len(large) > 60000 and len(json.dumps(messages).encode()) < cap
assert not blocked({'statement': large}) and not blocked_message(messages[0]['content'])
assert LLMInputContract.validate(messages) == messages
assert classify_message('x' * (cap + 1)).startswith('message exceeds size cap')
assert classify_message('{"class_uid":1007,"activity_id":1}') is not None
assert classify_message('password="synthetic_fixture_only_123456"') is not None
print(json.dumps({'status': 'passed', 'policy_sha256': policy.sha256,
                  'prepared_bytes': policy.model.max_prepared_bytes,
                  'guard_characters': cap, 'accepted_synthetic_characters': len(large),
                  'oversize_raw_and_secret_shape_rejected': True,
                  'model_calls': 0, 'network_calls': 0, 'business_writes': 0}))
