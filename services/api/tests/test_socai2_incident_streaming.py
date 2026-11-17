"""Direct event-only selection/coverage invariants; no model calls."""
import pytest
from app.socai2.analysis_incident_executor import IncidentTaskPolicy
from app.socai2.incident_inputs import SELECTION_VERSION, coverage, selected_source_sql
from app.socai2.stage_inputs import SOURCE_SQL
from app.socai2.stage_read_contracts import IncidentStageEntry, StageEntry


def test_event_selection_does_not_load_omitted_members():
    sql = selected_source_sql(SOURCE_SQL, ':incident_limit')
    assert 'a.id IN (SELECT alert_id FROM picked)' in sql
    assert 'ORDER BY linked_at DESC,alert_id ASC LIMIT (:incident_limit)' in sql
    assert 'total_member_count' in sql and 'count(*) FROM socai2.incident_alerts' in sql


@pytest.mark.parametrize('omitted,analyzed,unresolved,state,counts', [
    (160, ['a','b'], ['b'], 'partial',(1,1,1)),
    (0, ['a','b','c'], ['b','c'], 'complete',(1,2,0)),
    (0, [], [], 'none',(0,0,3)),
])
def test_coverage_is_saved_analysis_not_input_presence(omitted,analyzed,unresolved,state,counts):
    source={'selection_version':SELECTION_VERSION,'input_selection':{'selected_alert_ids':['a','b','c'],'omitted_count':omitted}}
    diagnosis={'delivery_assessment':{'member_coverage':{'expected_ids':['a','b','c'],'analyzed_ids':analyzed},
                                    'review_items':{'unresolved_member_ids':unresolved},'reasons':[]}}
    result=coverage(source,diagnosis)
    assert result['state']==state
    assert (result['analyzed_count'],result['unresolved_count'],result['not_analyzed_count'])==counts
    assert result['covered_alert_ids']==sorted(analyzed)
    assert coverage(source,None)['analyzed_count'] is None
    assert coverage({},diagnosis) is None


def test_invalid_saved_member_scope_is_unknown():
    source={'selection_version':SELECTION_VERSION,'input_selection':{'selected_alert_ids':['a'],'omitted_count':0}}
    result=coverage(source,{'delivery_assessment':{'member_coverage':{'expected_ids':['a'],'analyzed_ids':['foreign']}}})
    assert result['state']=='unknown' and result['covered_alert_ids'] is None


def test_alert_public_entry_keeps_original_fields():
    assert {'input_selection','analysis_coverage'}.isdisjoint(StageEntry.model_fields)
    assert {'input_selection','analysis_coverage'} <= IncidentStageEntry.model_fields.keys()


@pytest.mark.parametrize('value',[0,-1,True,1.5])
def test_invalid_selection_configuration(value):
    with pytest.raises(ValueError): IncidentTaskPolicy(value,100)
