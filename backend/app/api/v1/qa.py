"""QA 智能问答路由。

接口：
- POST /qa/ask        同步答题（dev 模式方便 Swagger 调试）
- WS   /qa/stream/{task_id}  流式答题（生产用，小程序 wx.connectSocket）
- GET  /qa/history    历史问答查询
- GET  /qa/history/{msg_id}  单条问答详情
"""
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select, func, and_, or_

from app.core.config import settings
from app.core.deps import DB, ElderUser, AnyRole
from app.core.security import decode_token
from app.models.message import Message
from app.models.config import ApiConfig, PromptTemplate
from app.models.interaction import AlertEvent, BehaviorTrace
from app.models.user import User, ChildUser, UserChildRelation, WxAccount
from app.schemas.common import R, Page
from app.schemas.qa import QAAskIn, QAAskOut, QAHistoryQuery
from app.services import llm_client


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qa", tags=["qa"])


@router.post(
    "/ask",
    response_model=R,
    summary="提交问答（同步）",
    description="""
提交多模态问答，**同步返回完整答案**（dev 模式推荐用此接口，方便 Swagger 调试）。

**流程**：
1. 接收问题（text/image/voice）+ 可选 media_url（上传图片时已自动增强，传 enhanced_url 即可）
2. 组装 Prompt（系统提示词 + 用户问题 + 可选图片 URL）
3. 调大模型（dev 模式返回 mock 回答）
4. 合规拦截：涉医内容追加免责声明
5. 预警信号检测：识别跌倒/情绪低落等关键词 → 写 alert_event
6. 落库：message + behavior_trace
7. 返回完整答案 + msg_id + cat_action + alert_signal

**权限**：仅老人端可调。
""".strip(),
    response_description="问答成功，返回答案与元信息",
    responses={
        200: {
            "description": "问答成功",
            "content": {"application/json": {"examples": {
                "text_qa": {
                    "summary": "文本问答",
                    "value": {
                        "code": 0, "msg": "ok",
                        "data": {
                            "msg_id": 1,
                            "session_id": "sess_20260629_a1b2c3",
                            "answer": "喵~布洛芬是饭后吃的哦...",
                            "intercepted": True,
                            "risk_tags": ["药品", "布洛芬"],
                            "latency_ms": 1523,
                            "cat_action": "speak",
                            "alert_signal": None,
                        },
                    },
                },
                "image_qa": {
                    "summary": "图片+文本问答",
                    "value": {
                        "code": 0, "msg": "ok",
                        "data": {
                            "msg_id": 2,
                            "session_id": "sess_20260629_d4e5f6",
                            "answer": "这是一盒阿司匹林，用于...",
                            "intercepted": True,
                            "risk_tags": ["药品"],
                            "latency_ms": 2100,
                            "cat_action": "speak",
                            "alert_signal": None,
                        },
                    },
                },
            }}},
        },
        400: {"description": "参数错误（如 image 类型未传 media_url）"},
        401: {"description": "未认证"},
        403: {"description": "非老人端 token"},
        500: {"description": "大模型调用失败"},
    },
)
async def ask(
    payload: Annotated[
        QAAskIn,
        Body(
            openapi_examples={
                "text_qa": {
                    "summary": "文本问答",
                    "value": {"input_type": "text", "text": "布洛芬怎么吃？"},
                },
                "image_qa": {
                    "summary": "图片+文本问答",
                    "value": {
                        "input_type": "image",
                        "text": "这是什么药？",
                        "media_url": "/files/img_20260627_xxx_enhanced.jpg",
                    },
                },
            },
        ),
    ],
    cur: ElderUser,
    db: DB,
):
    # 参数校验
    if payload.input_type in ("image", "voice") and not payload.media_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"input_type={payload.input_type} 时必须传 media_url")
    if payload.input_type == "text" and not payload.text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "input_type=text 时必须传 text")

    # 生成 session_id
    session_id = payload.session_id or f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # media_url 直接用（上传时已自动增强）
    processed_media_url = payload.media_url

    # 拿默认 prompt 与 api_config
    prompt_tpl = (await db.execute(
        select(PromptTemplate).where(PromptTemplate.enabled == 1).order_by(PromptTemplate.prompt_id).limit(1)
    )).scalar_one_or_none()
    api_cfg = (await db.execute(
        select(ApiConfig).where(ApiConfig.is_default == 1, ApiConfig.enabled == 1).limit(1)
    )).scalar_one_or_none()

    system_prompt = prompt_tpl.content if prompt_tpl else "你是老人关爱助手，语气温暖简洁。"
    api_config_id = api_cfg.api_config_id if api_cfg else None
    prompt_id = prompt_tpl.prompt_id if prompt_tpl else None

    # 构造用户问题文本
    user_text = payload.text or ""
    if payload.input_type == "voice" and payload.media_url:
        user_text = f"[语音提问] {user_text}" if user_text else "[语音提问]"

    # 调大模型
    t0 = time.time()
    try:
        # 图片 URL：dev 用相对路径，prod 补全为绝对 URL
        image_url_for_llm = None
        if payload.input_type == "image" and processed_media_url:
            image_url_for_llm = processed_media_url
            if not settings.is_dev and not processed_media_url.startswith("http"):
                # prod 模式需要完整 URL，从 config 取 base
                # 实际部署时应在 .env 配 PUBLIC_URL
                pass

        answer = await llm_client.call_llm(
            prompt=user_text,
            image_url=image_url_for_llm,
            system_prompt=system_prompt,
            stream=False,
        )
    except Exception as e:
        logger.error("大模型调用失败: %s", e, exc_info=True)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"大模型调用失败：{e}")
    latency_ms = int((time.time() - t0) * 1000)

    # 合规拦截
    intercepted, risk_tags = llm_client.check_medical_intercept(user_text + answer)
    if intercepted:
        answer = llm_client.append_disclaimer(answer)

    # 预警信号检测
    alert_signal = llm_client.check_alert_signal(user_text)

    # 写 message
    msg = Message(
        user_id=cur.ref_id,
        session_id=session_id,
        role="user",
        input_type=payload.input_type,
        content_text=payload.text,
        content_media_url=payload.media_url,
        processed_media_url=processed_media_url if payload.input_type == "image" else None,
        asr_text=user_text if payload.input_type == "voice" else None,
        answer_text=answer,
        prompt_id=prompt_id,
        api_config_id=api_config_id,
        intercepted=1 if intercepted else 0,
        risk_tags={"tags": risk_tags} if risk_tags else None,
        latency_ms=latency_ms,
        status="success",
    )
    db.add(msg)
    await db.flush()

    # 写 behavior_trace
    trace = BehaviorTrace(
        user_id=cur.ref_id,
        trace_time=datetime.now(timezone.utc),
        trace_type="问答",
        content_summary=(user_text or payload.input_type)[:200],
        identified_object=risk_tags[0] if risk_tags else None,
        risk_level="低" if intercepted else "无",
    )
    db.add(trace)

    # 写 alert_event（如有预警信号）
    if alert_signal:
        alert = AlertEvent(
            user_id=cur.ref_id,
            alert_type=alert_signal["alert_type"],
            alert_level=alert_signal["alert_level"],
            trigger_source="llm",
            trigger_msg_id=msg.msg_id,
            alert_time=datetime.now(timezone.utc),
            detail=alert_signal["detail"],
            handling_status="待处理",
            notify_channels=[{"channel": "subscribe", "status": "pending"}],
        )
        db.add(alert)
        logger.warning("⚠️ 老人 %s 触发预警: %s", cur.ref_id, alert_signal)

    # 推送预警给子女端（异步，不阻塞响应）
    if alert_signal:
        await _notify_children_alert(db, cur.ref_id, alert_signal)

    out = QAAskOut(
        msg_id=msg.msg_id,
        session_id=session_id,
        answer=answer,
        intercepted=intercepted,
        risk_tags=risk_tags if risk_tags else None,
        latency_ms=latency_ms,
        cat_action="speak",
        alert_signal=alert_signal,
    )
    return R.ok(out.model_dump(mode="json"))


@router.websocket("/stream/{task_id}")
async def qa_stream(ws: WebSocket, task_id: str):
    """流式问答 WebSocket（生产用）。

    小程序 wx.connectSocket 连此接口。
    连接后先发 JSON 握手包，然后接收流式 chunk。

    协议：
    - 客户端连接后发 JSON：{token, input_type, text, media_url, session_id}
    - 服务端推送：
      - {type: action, state: listen/think/speak}
      - {type: chunk, content: "..."}  流式回答
      - {type: intercept, tags: [...]}
      - {type: alert_signal, ...}
      - {type: done, msg_id, latency_ms}
      - {type: error, message}
    """
    await ws.accept()
    try:
        # 1. 接收握手包并鉴权
        req = await ws.receive_json()
        token = req.get("token", "")
        data = decode_token(token)
        if not data or data.get("type") != "access":
            await ws.send_json({"type": "error", "message": "token 无效"})
            await ws.close()
            return
        user_type = data.get("user_type")
        ref_id = data.get("ref_id")
        if user_type != "user" or not ref_id:
            await ws.send_json({"type": "error", "message": "仅老人端可调用"})
            await ws.close()
            return

        # 验证老人存在
        from app.db.session import AsyncSessionLocal as ASL
        async with ASL() as vdb:
            elder = await vdb.get(User, ref_id)
            if elder is None:
                await ws.send_json({"type": "error", "message": "老人账号不存在"})
                await ws.close()
                return

        await ws.send_json({"type": "action", "state": "listen"})

        # 2. 提取提问参数
        input_type = req.get("input_type", "text")
        text = req.get("text", "")
        media_url = req.get("media_url")
        session_id = req.get("session_id") or f"sess_{uuid.uuid4().hex[:8]}"

        await ws.send_json({"type": "action", "state": "think"})

        # 3. 拿默认 prompt
        async with ASL() as pdb:
            prompt_tpl = (await pdb.execute(
                select(PromptTemplate).where(PromptTemplate.enabled == 1).limit(1)
            )).scalar_one_or_none()
        system_prompt = prompt_tpl.content if prompt_tpl else "你是老人关爱助手，语气温暖简洁。"

        # 4. 调大模型（流式）
        t0 = time.time()
        try:
            stream = await llm_client.call_llm(
                prompt=text, image_url=media_url,
                system_prompt=system_prompt, stream=True,
            )
            full_answer = ""
            async for chunk in stream:
                full_answer += chunk
                await ws.send_json({"type": "chunk", "content": chunk})
        except Exception as e:
            logger.error("QA 流式异常: %s", e, exc_info=True)
            await ws.send_json({"type": "error", "message": f"大模型调用失败：{e}"})
            await ws.close()
            return
        latency_ms = int((time.time() - t0) * 1000)

        # 5. 合规拦截
        intercepted, risk_tags = llm_client.check_medical_intercept(text + full_answer)
        if intercepted:
            disclaimer = llm_client.append_disclaimer("")
            full_answer += disclaimer
            await ws.send_json({"type": "intercept", "tags": risk_tags})
            await ws.send_json({"type": "chunk", "content": disclaimer})

        # 6. 预警信号
        alert_signal = llm_client.check_alert_signal(text)
        if alert_signal:
            await ws.send_json({"type": "alert_signal", **alert_signal})

        # 7. 落库
        async with ASL() as db:
            msg = Message(
                user_id=ref_id,
                session_id=session_id,
                role="user",
                input_type=input_type,
                content_text=text,
                content_media_url=media_url,
                answer_text=full_answer,
                intercepted=1 if intercepted else 0,
                risk_tags={"tags": risk_tags} if risk_tags else None,
                latency_ms=latency_ms,
                status="success",
            )
            db.add(msg)
            await db.flush()

            # behavior_trace
            trace = BehaviorTrace(
                user_id=ref_id,
                trace_time=datetime.now(timezone.utc),
                trace_type="问答",
                content_summary=(text or input_type)[:200],
                identified_object=risk_tags[0] if risk_tags else None,
                risk_level="低" if intercepted else "无",
            )
            db.add(trace)

            # alert_event
            if alert_signal:
                alert = AlertEvent(
                    user_id=ref_id,
                    alert_type=alert_signal["alert_type"],
                    alert_level=alert_signal["alert_level"],
                    trigger_source="llm",
                    trigger_msg_id=msg.msg_id,
                    alert_time=datetime.now(timezone.utc),
                    detail=alert_signal["detail"],
                    handling_status="待处理",
                    notify_channels=[{"channel": "subscribe", "status": "pending"}],
                )
                db.add(alert)
                await db.flush()

                # 通知子女
                relations = (await db.execute(
                    select(UserChildRelation).where(UserChildRelation.user_id == ref_id)
                )).scalars().all()
                from app.core.wx import send_subscribe_message
                for rel in relations:
                    child = await db.get(ChildUser, rel.child_id)
                    if child and child.wx_account_id:
                        acc = await db.get(WxAccount, child.wx_account_id)
                        if acc:
                            try:
                                await send_subscribe_message(
                                    openid=acc.openid,
                                    template_id="tpl_alert_urgent" if alert_signal["alert_level"] == "紧急" else "tpl_alert_warn",
                                    data={
                                        "thing1": {"value": str(ref_id)},
                                        "thing2": {"value": alert_signal["alert_type"]},
                                        "time3": {"value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")},
                                        "thing4": {"value": alert_signal["detail"][:20]},
                                    },
                                )
                            except Exception as e:
                                logger.warning("WS 模式通知子女预警失败: %s", e)

            await db.commit()
            msg_id = msg.msg_id

        await ws.send_json({"type": "action", "state": "speak"})
        await ws.send_json({"type": "done", "msg_id": msg_id, "latency_ms": latency_ms})

    except WebSocketDisconnect:
        logger.info("QA WebSocket 断开: task_id=%s", task_id)
    except Exception as e:
        logger.error("QA WebSocket 异常: %s", e, exc_info=True)
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@router.get(
    "/history",
    response_model=R,
    summary="历史问答查询",
    description="""
查询老人的历史问答记录，支持分页 + 多条件筛选。

**筛选条件**：
- input_type：按输入类型（text/image/voice）
- keyword：模糊匹配问题+回答
- start_date / end_date：按时间范围

**权限**：老人端查自己；子女端查绑定的老人（需传 user_id）；管理端查任意。
""".strip(),
    response_description="分页的历史问答列表",
    responses={
        200: {"description": "查询成功"},
        401: {"description": "未认证"},
        403: {"description": "无权访问该老人数据"},
    },
)
async def history(
    cur: AnyRole,
    db: DB,
    page: int = 1,
    page_size: int = 20,
    user_id: int | None = None,
    input_type: str | None = None,
    keyword: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    # 确定查询的 user_id
    target_user_id = _resolve_target_user(cur, user_id)

    # 子女端校验绑定关系
    if cur.is_child:
        bindings = (await db.execute(
            select(UserChildRelation).where(
                UserChildRelation.child_id == cur.ref_id,
                UserChildRelation.user_id == target_user_id,
            )
        )).scalars().all()
        if not bindings:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "您未绑定该老人，无权查看数据")

    # 构造查询
    conditions = [Message.user_id == target_user_id, Message.role == "user"]
    if input_type:
        conditions.append(Message.input_type == input_type)
    if keyword:
        conditions.append(or_(Message.content_text.like(f"%{keyword}%"), Message.answer_text.like(f"%{keyword}%")))
    if start_date:
        conditions.append(Message.created_at >= start_date)
    if end_date:
        conditions.append(Message.created_at <= end_date + " 23:59:59")

    # 总数
    total = (await db.execute(select(func.count()).select_from(Message).where(*conditions))).scalar() or 0

    # 分页数据
    stmt = (
        select(Message)
        .where(*conditions)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()

    return R.ok(Page(
        total=total, page=page, page_size=page_size,
        items=[_msg_to_dict(m) for m in items],
    ).model_dump(mode="json"))


@router.get(
    "/history/{msg_id}",
    response_model=R,
    summary="单条问答详情",
    description="根据 msg_id 查询单条问答详情（含原图/处理后图/回答）。",
    response_description="问答详情",
    responses={
        200: {"description": "查询成功"},
        401: {"description": "未认证"},
        404: {"description": "消息不存在"},
    },
)
async def history_detail(msg_id: int, cur: AnyRole, db: DB):
    msg = await db.get(Message, msg_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "消息不存在")
    return R.ok(_msg_to_dict(msg))


# ============ 辅助函数 ============

def _resolve_target_user(cur, user_id: int | None) -> int:
    """根据当前角色与传入 user_id 确定查询目标。

    老人端 -> 查自己
    子女端 -> 需传 user_id，且必须已绑定
    管理端 -> 需传 user_id
    """
    if cur.is_elder:
        return cur.ref_id
    if cur.is_child:
        if user_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "子女端查询需传 user_id")
        # 校验绑定关系：子女必须已绑定该老人
        # 使用同步方式从当前 DB session 校验（history 接口有 DB 注入）
        # 此处先做参数校验，绑定关系在接口中异步查
        return user_id
    if cur.is_admin:
        if user_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "管理端查询需传 user_id")
        return user_id
    raise HTTPException(status.HTTP_403_FORBIDDEN, "无权访问")


def _msg_to_dict(m: Message) -> dict:
    return {
        "msg_id": m.msg_id,
        "session_id": m.session_id,
        "input_type": m.input_type,
        "content_text": m.content_text,
        "content_media_url": m.content_media_url,
        "processed_media_url": m.processed_media_url,
        "asr_text": m.asr_text,
        "answer_text": m.answer_text,
        "intercepted": bool(m.intercepted),
        "risk_tags": m.risk_tags,
        "latency_ms": m.latency_ms,
        "status": m.status,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


async def _notify_children_alert(db, user_id: int, alert_signal: dict):
    """异步通知绑定子女预警（dev 模式仅打日志）。"""
    try:
        relations = (await db.execute(
            select(UserChildRelation).where(UserChildRelation.user_id == user_id)
        )).scalars().all()
        from app.core.wx import send_subscribe_message
        for rel in relations:
            child = await db.get(ChildUser, rel.child_id)
            if child and child.wx_account_id:
                acc = await db.get(WxAccount, child.wx_account_id)
                if acc:
                    await send_subscribe_message(
                        openid=acc.openid,
                        template_id="tpl_alert_urgent" if alert_signal["alert_level"] == "紧急" else "tpl_alert_warn",
                        data={
                            "thing1": {"value": f"老人{user_id}"},
                            "thing2": {"value": alert_signal["alert_type"]},
                            "time3": {"value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")},
                            "thing4": {"value": alert_signal["detail"][:20]},
                        },
                    )
    except Exception as e:
        logger.warning("通知子女预警失败: %s", e)
