import asyncio
import pytest
from app.banking_workflow import bind_request
from app.auth import DEMO_USERS
from app.database import Database
from app.gateway import PolicyGateway
from app.tools import ToolDispatcher


@pytest.mark.parametrize('text',[
    'Balance <ACCOUNT_1>', 'Số dư tài khoản <BANK_ACCOUNT>',
    'Balance account: unknown-person', 'Balance ACC-BROKEN',
    'Balance ACC-ALICE-001 and ACC-BOB-001',
    'Balance <ACCOUNT_UNKNOWN>', 'Balance account of Carol', 'Số dư tài khoản của Lan',
])
def test_unresolved_or_multiple_identifier_never_defaults(text):
    bound = bind_request([{'role':'user','content':text}])
    assert bound.tool is None
    assert bound.reply


def test_mapped_bob_placeholder_is_denied_not_replaced(tmp_path):
    bound = bind_request([{'role':'user','content':'Balance <ACCOUNT_1>'}],
                         account_mapping={'<ACCOUNT_1>':'ACC-BOB-001'})
    assert bound.arguments == {'account_id':'ACC-BOB-001'}
    db = Database(str(tmp_path/'binding.sqlite3'))
    db.initialize()
    cid = db.create_conversation('alice','Binding')['id']
    result = asyncio.run(ToolDispatcher(db,PolicyGateway(mode='local')).run(
        DEMO_USERS[0],cid,bound.tool,bound.arguments))
    assert result == {'error':'TOOL_DENIED','reason_code':'ACCOUNT_NOT_OWNED'}


def test_mapping_is_request_local_and_unresolved_history_does_not_default():
    messages = [{'role':'user','content':'Balance <ACCOUNT_1>'}]
    assert bind_request(messages,account_mapping={'<ACCOUNT_1>':'ACC-ALICE-001'}).arguments['account_id']=='ACC-ALICE-001'
    assert bind_request(messages).tool is None
    followup = messages + [{'role':'assistant','content':'Unknown'}, {'role':'user','content':'Do I have enough money?'}]
    assert bind_request(followup).tool is None


def test_self_balance_can_default():
    assert bind_request([{'role':'user','content':'Số dư của tôi?'}]).arguments == {}


def test_numeric_mapping_and_two_numeric_targets_do_not_default():
    assert bind_request([{'role':'user','content':'Balance <ACCOUNT_1>'}],
                        account_mapping={'<ACCOUNT_1>':'9876543210'}).arguments == {'account_id':'9876543210'}
    assert bind_request([{'role':'user','content':'Balance account 12345678 and account 98765432'}]).tool is None
