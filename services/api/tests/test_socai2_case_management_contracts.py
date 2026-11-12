from uuid import uuid4

import pytest
from pydantic import ValidationError
from app.socai2.case_management_contracts import CaseManagementUpdate, CaseLifecycleRequest


@pytest.mark.parametrize('fields', [{}, {'title':None}, {'title':'  '}, {'tags':None},
    {'tags':['a','a']}, {'tags':[' ']}, {'handling_status':'resolved'}])
def test_invalid_management_inputs(fields):
    with pytest.raises(ValidationError):
        CaseManagementUpdate(operation_key=uuid4(),expected_row_version=1,**fields)


def test_patch_distinguishes_omitted_and_nullable_fields():
    patch=CaseManagementUpdate(operation_key=uuid4(),expected_row_version=1,description=None)
    assert patch.model_fields_set=={'operation_key','expected_row_version','description'}
    schema=CaseManagementUpdate.model_json_schema()
    for field in ['title','tags','handling_status']:
        assert 'anyOf' not in schema['properties'][field] and 'default' not in schema['properties'][field]
    assert CaseLifecycleRequest(operation_key=uuid4(),expected_row_version=1).reason is None
