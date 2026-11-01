"""
Tests for UITarsBridge and VisionExecutor

WSP Reference: WSP 34 (Test Documentation)
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from pathlib import Path

# Import modules under test
from modules.infrastructure.foundups_vision.src.ui_tars_bridge import (
    UITarsBridge,
    ActionResult,
    Screenshot,
    UITarsConnectionError,
    _decode_ui_tars_point,
    _ui_tars_15_image_size,
)
from modules.infrastructure.foundups_vision.src.vision_executor import (
    VisionExecutor,
    ActionStep,
    WorkflowResult,
)


class TestUITarsCoordinates:
    """Offline protocol tests: no browser, provider request or model authority."""

    def test_legacy_tagged_point_and_box_keep_grid_contract(self):
        point = _decode_ui_tars_point("Thought: target\nAction: click(start_box='<|box_start|>(250,500)<|box_end|>')")
        box = _decode_ui_tars_point("Action: click(start_box='<|box_start|>(200,400)<|box_end|>(300,600)')")
        assert point['normalized'] == box['normalized'] == (.25, .5)

    def test_model_specific_absolute_point_is_not_legacy_grid(self):
        point = _decode_ui_tars_point("Action: click(start_box='(196,420)')",
            coordinate_profile='ui_tars_1_5_qwen25vl', image_size=(392,840))
        assert point['normalized'] == (.5,.5)
        assert point['model_image_size'] == (392,840)
        assert int(point['normalized'][0]*780/2) == 195
        assert int(point['normalized'][1]*1688/2) == 422
        with pytest.raises(ValueError):
            _decode_ui_tars_point("Action: click(start_box='(196,420)')")

    def test_absolute_bbox_center_uses_submitted_image(self):
        point = _decode_ui_tars_point('Action: click(start_box="(100,200),(292,640)")',
            coordinate_profile='ui_tars_1_5_qwen25vl', image_size=(392,840))
        assert point['normalized'] == (.5,.5)

    @pytest.mark.parametrize('width,height,expected',[(390,844,(392,840)),(1280,588,(1288,588)),(28,28,(280,280)),(10000,10000,(3584,3584))])
    def test_qwen_grid_is_explicit_before_inference(self,width,height,expected):
        assert _ui_tars_15_image_size(width,height) == expected

    @pytest.mark.parametrize('output',[
        "Action: click(start_box='(-1,20)')",
        "Action: click(start_box='(nan,20)')",
        "Action: click(start_box='(393,20)')",
        "Action: click(start_box='(392,20)')",
        "Action: click(start_box='(20,841)')",
        "Action: click(start_box='(200,300),(100,200)')",
        "Action: click(start_box='(20,20)'); __import__('os').system('bad')",
        "Action: click(start_box=__import__('os').system('bad'))",
        "Action: click(start_box='(20,20)')\nAction: click(start_box='(30,30)')",
        "Action: click(start_box='(20,20)')\n  Action: click(start_box='(30,30)')",
        "Action:\nclick(start_box='(20,20)')",
        "Action: finished()",
    ])
    def test_bad_or_ambiguous_actions_fail_closed(self,output):
        with pytest.raises(ValueError):
            _decode_ui_tars_point(output,coordinate_profile='ui_tars_1_5_qwen25vl',image_size=(392,840))

    @pytest.mark.parametrize('profile,size',[('guessed',None),('ui_tars_1_5_qwen25vl',None),('ui_tars_1_5_qwen25vl',(390,844)),('ui_tars_1_5_qwen25vl',(0,28))])
    def test_unknown_profile_or_unbound_grid_is_rejected(self,profile,size):
        with pytest.raises(ValueError):
            _decode_ui_tars_point("Action: click(start_box='(20,20)')",coordinate_profile=profile,image_size=size)

    @pytest.mark.parametrize('profile,output,model_size',[
        ('legacy_1000',"Action: click(start_box='<|box_start|>(500,500)<|box_end|>')",(780,1688)),
        ('ui_tars_1_5_qwen25vl',"Action: click(start_box='(392,840)')",(784,1680)),
    ])
    @pytest.mark.parametrize('action,reply,accepted',[
        ('verify',None,True),
        ('click',{'ok':True},True),
        ('click',{'ok':False,'error':'No element at point'},False),
        ('click',{'ok':False,'error':'SENTINEL: ABORTED'},False),
        ('click',None,False),
    ])
    def test_snapshot_action_result_maps_dpr_without_browser_effects(self,monkeypatch,tmp_path,profile,output,model_size,action,reply,accepted):
        import io
        from PIL import Image
        import requests
        import modules.infrastructure.foundups_vision.src.ui_tars_bridge as owner
        monkeypatch.setattr(owner,'UI_TARS_TELEMETRY',tmp_path/'telemetry')
        monkeypatch.setattr(owner,'SCREENSHOT_DIR',tmp_path/'screenshots')
        monkeypatch.setattr(owner,'UI_TARS_MODEL','ui-tars-1.5-7b')
        png=io.BytesIO();Image.new('RGB',(780,1688)).save(png,format='PNG')
        class Snapshot:
            def get_screenshot_as_png(self):return png.getvalue()
            def execute_script(self,script,*args):
                if 'window.innerWidth' in script:return {'w':390,'h':844,'dpr':2,'topLevel':True}
                if 'window.frameElement' in script:return {'x':0,'y':0}
                if 'elementFromPoint' in script:return reply
                raise AssertionError('Unexpected browser effect')
        response=MagicMock(status_code=200)
        response.json.return_value={'choices':[{'message':{'content':output}}]}
        monkeypatch.setattr(requests,'post',lambda *args,**kwargs:response)
        bridge=owner.UITarsBridge();bridge._connected=True
        result=asyncio.run(bridge.execute_action(action,'fixture',context={'coordinate_profile':profile},driver=Snapshot()))
        assert result.success is accepted,result.error
        assert result.metadata['viewport_css']=={'x':195,'y':422}
        assert result.metadata['model_image_size']==model_size
        assert result.metadata['executed']==({'ok':True} if action=='verify' else reply)
        assert result.metadata['proposal_only'] is (action=='verify')
        assert result.metadata['action_executed'] is (accepted and action=='click')
        if not accepted:assert result.error and result.confidence==0.0

    def test_unverified_model_profile_never_requests_inference(self,monkeypatch,tmp_path):
        import io
        from PIL import Image
        import requests
        import modules.infrastructure.foundups_vision.src.ui_tars_bridge as owner
        monkeypatch.setattr(owner,'UI_TARS_TELEMETRY',tmp_path/'telemetry')
        monkeypatch.setattr(owner,'SCREENSHOT_DIR',tmp_path/'screenshots')
        monkeypatch.setattr(owner,'UI_TARS_MODEL','unknown-model-alias')
        png=io.BytesIO();Image.new('RGB',(392,840)).save(png,format='PNG')
        snapshot=MagicMock();snapshot.get_screenshot_as_png.return_value=png.getvalue()
        request=MagicMock();monkeypatch.setattr(requests,'post',request)
        bridge=owner.UITarsBridge();bridge._connected=True
        result=asyncio.run(bridge.execute_action('verify','fixture',context={'coordinate_profile':'ui_tars_1_5_qwen25vl'},driver=snapshot))
        assert not result.success and 'verified model identifier' in result.error
        request.assert_not_called()

    @pytest.mark.parametrize('viewport',[
        None, {}, {'w':0,'h':0,'topLevel':True}, RuntimeError('query unavailable'),
        {'w':390,'h':1688,'topLevel':True},
        {'w':390,'h':844,'topLevel':False}, {'w':390,'h':844},
        {'w':390,'h':844,'topLevel':'true'},
        {'w':float('nan'),'h':844,'topLevel':True},
        {'w':390,'h':float('inf'),'topLevel':True},
        {'w':True,'h':844,'topLevel':True},
    ])
    def test_new_profile_unknown_geometry_blocks_before_inference_or_input(self,monkeypatch,tmp_path,viewport):
        import io
        from PIL import Image
        import requests
        import modules.infrastructure.foundups_vision.src.ui_tars_bridge as owner
        monkeypatch.setattr(owner,'UI_TARS_TELEMETRY',tmp_path/'telemetry')
        monkeypatch.setattr(owner,'SCREENSHOT_DIR',tmp_path/'screenshots')
        monkeypatch.setattr(owner,'UI_TARS_MODEL','ui-tars-1.5-7b')
        png=io.BytesIO();Image.new('RGB',(780,1688)).save(png,format='PNG')
        class Snapshot:
            def get_screenshot_as_png(self):return png.getvalue()
            def execute_script(self,script,*args):
                if 'window.innerWidth' in script:
                    if isinstance(viewport,Exception):raise viewport
                    return viewport
                raise AssertionError('No downstream geometry/input permitted')
        request=MagicMock();monkeypatch.setattr(requests,'post',request)
        bridge=owner.UITarsBridge();bridge._connected=True
        result=asyncio.run(bridge.execute_action('click','fixture',context={'coordinate_profile':'ui_tars_1_5_qwen25vl'},driver=Snapshot()))
        assert not result.success and 'viewport geometry' in result.error
        request.assert_not_called()

    @pytest.mark.parametrize('pixels,model_size,point',[
        ((390,843),(392,840),(196,420)),
        ((488,1055),(476,1064),(238,532)),
    ])
    def test_new_profile_capture_rounding_keeps_observed_top_level_css(self,monkeypatch,tmp_path,pixels,model_size,point):
        import io
        from PIL import Image
        import requests
        import modules.infrastructure.foundups_vision.src.ui_tars_bridge as owner
        monkeypatch.setattr(owner,'UI_TARS_TELEMETRY',tmp_path/'telemetry')
        monkeypatch.setattr(owner,'SCREENSHOT_DIR',tmp_path/'screenshots')
        monkeypatch.setattr(owner,'UI_TARS_MODEL','ui-tars-1.5-7b')
        png=io.BytesIO();Image.new('RGB',pixels).save(png,format='PNG')
        class Snapshot:
            def get_screenshot_as_png(self):return png.getvalue()
            def execute_script(self,script,*args):
                if 'window.innerWidth' in script:return {'w':390,'h':844,'topLevel':True}
                raise AssertionError('Top-level profile must not query legacy frame offsets or execute input')
        response=MagicMock(status_code=200)
        response.json.return_value={'choices':[{'message':{'content':f"Action: click(start_box='({point[0]},{point[1]})')"}}]}
        monkeypatch.setattr(requests,'post',lambda *args,**kwargs:response)
        bridge=owner.UITarsBridge();bridge._connected=True
        result=asyncio.run(bridge.execute_action('verify','fixture',context={'coordinate_profile':'ui_tars_1_5_qwen25vl'},driver=Snapshot()))
        assert result.success,result.error
        assert result.metadata['model_image_size']==model_size
        assert result.metadata['viewport_css']=={'x':195,'y':422}
        assert result.metadata['original_screenshot_size']==pixels
        assert result.metadata['observed_viewport']=={'width':390,'height':844}

    @pytest.mark.parametrize('viewport',[{},RuntimeError('legacy query unavailable')])
    def test_legacy_geometry_fallback_remains_explicitly_unchanged(self,monkeypatch,tmp_path,viewport):
        import io
        from PIL import Image
        import requests
        import modules.infrastructure.foundups_vision.src.ui_tars_bridge as owner
        monkeypatch.setattr(owner,'UI_TARS_TELEMETRY',tmp_path/'telemetry')
        monkeypatch.setattr(owner,'SCREENSHOT_DIR',tmp_path/'screenshots')
        png=io.BytesIO();Image.new('RGB',(780,1688)).save(png,format='PNG')
        class Snapshot:
            def get_screenshot_as_png(self):return png.getvalue()
            def execute_script(self,script,*args):
                if 'window.innerWidth' in script:
                    if isinstance(viewport,Exception):raise viewport
                    return viewport
                if 'window.frameElement' in script:return {'x':0,'y':0}
                raise AssertionError('No real browser effects')
        response=MagicMock(status_code=200)
        response.json.return_value={'choices':[{'message':{'content':"Action: click(start_box='<|box_start|>(500,500)<|box_end|>')"}}]}
        monkeypatch.setattr(requests,'post',lambda *args,**kwargs:response)
        bridge=owner.UITarsBridge();bridge._connected=True
        result=asyncio.run(bridge.execute_action('verify','fixture',driver=Snapshot()))
        assert result.success and result.metadata['viewport_css']=={'x':390,'y':844}
        assert result.metadata['proposal_only'] and not result.metadata['action_executed']


class TestUITarsBridge:
    """Test UITarsBridge functionality."""

    def test_bridge_init(self):
        """Test bridge initialization."""
        bridge = UITarsBridge()
        assert bridge.browser_port == 9222
        assert not bridge._connected
        assert bridge._session_id is None

    def test_bridge_init_custom_port(self):
        """Test bridge with custom port."""
        bridge = UITarsBridge(browser_port=9333)
        assert bridge.browser_port == 9333

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connection to UI-TARS."""
        bridge = UITarsBridge()
        
        # Should connect (creates directories)
        result = await bridge.connect()
        assert result is True
        assert bridge._connected is True
        assert bridge._session_id is not None
        
        bridge.close()
        assert bridge._connected is False

    @pytest.mark.asyncio
    async def test_execute_action(self):
        """Test action execution."""
        bridge = UITarsBridge()
        await bridge.connect()
        
        result = await bridge.execute_action(
            action="click",
            description="test button",
            context={"test": True},
        )
        
        assert isinstance(result, ActionResult)
        assert result.action == "click"
        assert result.description == "test button"
        assert result.duration_ms >= 0
        
        bridge.close()

    @pytest.mark.asyncio
    async def test_click_helper(self):
        """Test click convenience method."""
        bridge = UITarsBridge()
        await bridge.connect()
        
        result = await bridge.click("Like button")
        
        assert result.action == "click"
        assert result.description == "Like button"
        
        bridge.close()

    def test_observer_registration(self):
        """Test telemetry observer registration."""
        events = []
        
        def observer(event, payload):
            events.append((event, payload))
        
        bridge = UITarsBridge(observers=[observer])
        
        # Should have captured init event
        assert len(events) > 0
        assert events[0][0] == "bridge_init"

    def test_action_result_to_dict(self):
        """Test ActionResult serialization."""
        result = ActionResult(
            success=True,
            action="click",
            description="test",
            duration_ms=100,
            confidence=0.95,
        )
        
        d = result.to_dict()
        assert d["success"] is True
        assert d["action"] == "click"
        assert d["confidence"] == 0.95


class TestVisionExecutor:
    """Test VisionExecutor functionality."""

    @pytest.mark.asyncio
    async def test_executor_init(self):
        """Test executor initialization."""
        bridge = UITarsBridge()
        await bridge.connect()
        
        executor = VisionExecutor(bridge)
        assert executor.max_retries == 3
        assert executor.verify_each is True
        
        bridge.close()

    @pytest.mark.asyncio
    async def test_execute_step(self):
        """Test single step execution."""
        bridge = UITarsBridge()
        await bridge.connect()
        
        executor = VisionExecutor(bridge)
        
        step = ActionStep(
            action="click",
            description="test button",
            wait_after=0.1,
        )
        
        result = await executor.execute_step(step)
        
        assert isinstance(result, ActionResult)
        
        bridge.close()

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test multi-step workflow execution."""
        bridge = UITarsBridge()
        await bridge.connect()
        
        executor = VisionExecutor(bridge, verify_each=False)
        
        steps = [
            ActionStep(action="scroll", description="scroll down", wait_after=0.1),
            ActionStep(action="click", description="button", wait_after=0.1),
        ]
        
        result = await executor.execute_workflow(steps)
        
        assert isinstance(result, WorkflowResult)
        assert result.steps_total == 2
        assert len(result.step_results) == 2
        
        bridge.close()

    @pytest.mark.asyncio
    async def test_like_and_reply_workflow(self):
        """Test pre-built like and reply workflow."""
        bridge = UITarsBridge()
        await bridge.connect()
        
        executor = VisionExecutor(bridge, verify_each=False)
        
        result = await executor.like_and_reply_workflow(
            video_id="test123",
            comment_id="comment456",
            reply_text="Great video!",
        )
        
        assert isinstance(result, WorkflowResult)
        assert result.steps_total == 5  # scroll, like, reply btn, type, submit
        
        bridge.close()

    def test_action_step_defaults(self):
        """Test ActionStep default values."""
        step = ActionStep(action="click", description="button")
        
        assert step.text is None
        assert step.wait_after == 0.5
        assert step.required is True
        assert step.max_retries == 2

    def test_workflow_result_to_dict(self):
        """Test WorkflowResult serialization."""
        result = WorkflowResult(
            success=True,
            steps_completed=3,
            steps_total=3,
            total_duration_ms=1500,
        )
        
        d = result.to_dict()
        assert d["success"] is True
        assert d["steps_completed"] == 3
        assert d["total_duration_ms"] == 1500


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])



